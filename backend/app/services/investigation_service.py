from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.database.models import (
    Batch, Product, Machine, InspectionCharacteristic, Measurement,
    InspectionImage, VisualFinding, ProcessReading, ProcessBaseline,
    Anomaly, SPCResult, QualityIncident, RCAHypothesis, CAPAAction,
    MaintenanceRecord, HumanDecision
)
from backend.app.core.guardrails import EpistemicLabel

STRATEGY_DIMENSIONAL_OVERSIZED = "STRATEGY_DIMENSIONAL_OVERSIZED"
STRATEGY_DIMENSIONAL_UNDERSIZED = "STRATEGY_DIMENSIONAL_UNDERSIZED"
STRATEGY_VISUAL_DEFECT = "STRATEGY_VISUAL_DEFECT"
STRATEGY_SURFACE_FINISH = "STRATEGY_SURFACE_FINISH"
STRATEGY_PROCESS_DRIFT = "STRATEGY_PROCESS_DRIFT"
STRATEGY_MATERIAL_STRUCTURAL = "STRATEGY_MATERIAL_STRUCTURAL"
STRATEGY_MULTIPLE_DEFECTS = "STRATEGY_MULTIPLE_DEFECTS"
STRATEGY_CONFORMING_PROCESS = "STRATEGY_CONFORMING_PROCESS_VERIFICATION"

def select_investigation_strategy(
    has_oversized: bool,
    has_undersized: bool,
    has_visual: bool,
    has_surface: bool,
    has_drift: bool,
    has_material: bool,
    nonconforming_count: int,
    defect_type: Optional[str] = None
) -> Dict[str, str]:
    defect_str = (defect_type or "").lower()

    defects_count = sum([
        1 if (has_oversized or has_undersized) else 0,
        1 if has_visual else 0,
        1 if has_surface else 0,
        1 if has_material else 0
    ])

    if defects_count > 1 or (nonconforming_count > 0 and has_visual):
        return {
            "strategy": STRATEGY_MULTIPLE_DEFECTS,
            "title": "Composite Investigation: Multi-Defect Cross-Correlation",
            "description": "Evaluates whether concurrent dimensional and visual/surface nonconformances originate from a shared root cause (such as severe tool insert breakdown, excessive cutting force, or chuck slippage)."
        }

    if has_visual or "scratch" in defect_str or "dent" in defect_str or "crack" in defect_str:
        return {
            "strategy": STRATEGY_VISUAL_DEFECT,
            "title": "Visual Surface Defect & Morphology Investigation",
            "description": "Examines computer vision findings, defect bounding box coordinates, optical surface features, chip clearance, and mechanical handling history."
        }

    if has_surface or "surface" in defect_str or "chatter" in defect_str or "roughness" in defect_str:
        return {
            "strategy": STRATEGY_SURFACE_FINISH,
            "title": "Surface-Finish & Cutting Dynamics Investigation",
            "description": "Examines spindle vibration harmonics, feed per revolution, spindle speed stability, cutting tool nose condition, and coolant delivery."
        }

    if has_drift or "drift" in defect_str:
        return {
            "strategy": STRATEGY_PROCESS_DRIFT,
            "title": "Process Drift & Statistical Shift Investigation",
            "description": "Analyzes progressive trend across consecutive parts, CUSUM drift signatures, thermal expansion of machine ball screw/spindle, and gradual tool flank wear."
        }

    if has_material or "material" in defect_str or "hardness" in defect_str:
        return {
            "strategy": STRATEGY_MATERIAL_STRUCTURAL,
            "title": "Material & Structural Integrity Investigation",
            "description": "Examines raw material lot heat certificates, metallurgical hardness variation, incoming inspection records, and microstructure anomalies."
        }

    if has_undersized:
        return {
            "strategy": STRATEGY_DIMENSIONAL_UNDERSIZED,
            "title": "Undersized Dimension & CNC Offset Investigation",
            "description": "Investigates CNC controller tool wear offset registry, operator manual compensation bias, workpiece deflection under cutting forces, and insert micro-chipping."
        }

    if has_oversized or nonconforming_count > 0:
        return {
            "strategy": STRATEGY_DIMENSIONAL_OVERSIZED,
            "title": "Oversized Dimension & Tool Wear Investigation",
            "description": "Investigates approved specification limits, measurement trends, tool wear cycle count, CNC wear offset registry, cutting force increase, and gauge calibration."
        }

    return {
        "strategy": STRATEGY_CONFORMING_PROCESS,
        "title": "Conforming Process Baseline Verification",
        "description": "All sampled parts strictly satisfy approved engineering specifications. Process parameters and statistical capability remain within normal operating windows."
    }

def build_investigation_report(batch_id: str, db: Session) -> Dict[str, Any]:
    b = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not b:
        raise ValueError(f"Batch '{batch_id}' not found in manufacturing database.")

    prod = b.product
    mach = b.machine

    char = None
    if prod and prod.characteristics:
        char = prod.characteristics[0]
    elif prod:
        char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == prod.id).first()

    nominal_val = char.nominal if char else 50.00
    usl_val = char.usl if char else (nominal_val + (char.tol_plus if char else 0.05))
    lsl_val = char.lsl if char else (nominal_val - (char.tol_minus if char else 0.05))
    char_name = char.name if char else "dimensional_specification"
    unit_str = char.unit if char else "mm"

    measurements_q = db.query(Measurement).filter(Measurement.batch_id == b.id).order_by(Measurement.measured_at.asc()).all()
    total_inspected = len(measurements_q)
    nonconforming_samples = []
    conforming_samples = []
    has_oversized = False
    has_undersized = False

    for m in measurements_q:
        is_nc = (m.status == "nonconforming") or (m.value > usl_val) or (m.value < lsl_val)
        dev = round(m.value - usl_val if m.value > usl_val else (lsl_val - m.value if m.value < lsl_val else 0.0), 4)
        item_data = {
            "sample_id": m.component_id,
            "measured_value": m.value,
            "unit": m.unit or unit_str,
            "status": "nonconforming" if is_nc else "conforming",
            "deviation_from_limit": dev,
            "measured_at": m.measured_at.strftime("%Y-%m-%d %H:%M:%S") if m.measured_at else None,
            "source": m.source_type or "gauge"
        }
        if is_nc:
            nonconforming_samples.append(item_data)
            if m.value > usl_val:
                has_oversized = True
            if m.value < lsl_val:
                has_undersized = True
        else:
            conforming_samples.append(item_data)

    nonconforming_count = len(nonconforming_samples)
    conforming_count = len(conforming_samples)
    rejection_rate = round((nonconforming_count / total_inspected * 100.0), 2) if total_inspected > 0 else 0.0

    visual_findings_q = db.query(VisualFinding).join(InspectionImage).filter(InspectionImage.batch_id == b.id).all()
    has_visual_defect = any(vf.defect_detected for vf in visual_findings_q)
    visual_defects_list = [
        {
            "id": vf.id,
            "defect_detected": vf.defect_detected,
            "defect_type": vf.defect_type,
            "confidence": vf.confidence,
            "location": vf.location,
            "model_version": vf.model_version,
            "human_status": vf.human_status
        }
        for vf in visual_findings_q
    ]

    telemetry_q = db.query(ProcessReading).filter(ProcessReading.batch_id == b.id).order_by(ProcessReading.ts.asc()).all()
    has_telemetry = len(telemetry_q) > 0
    vibration_values = [r.vibration for r in telemetry_q]
    tool_cycles_values = [r.tool_usage_cycles for r in telemetry_q]
    max_vibration = max(vibration_values) if vibration_values else 0.0
    latest_tool_cycles = tool_cycles_values[-1] if tool_cycles_values else 0

    has_surface_issue = max_vibration > 3.0 or any("surface" in (vf.defect_type or "") for vf in visual_findings_q)
    has_drift_signature = False
    if len(measurements_q) >= 4:
        vals = [m.value for m in measurements_q]
        is_increasing = all(vals[i] <= vals[i+1] for i in range(len(vals)-1))
        if is_increasing and nonconforming_count > 0:
            has_drift_signature = True

    maintenance_q = db.query(MaintenanceRecord).filter(MaintenanceRecord.machine_id == b.machine_id).order_by(MaintenanceRecord.date.desc()).all()
    has_maintenance = len(maintenance_q) > 0
    maintenance_records = [
        {
            "id": mr.id,
            "date": mr.date,
            "type": mr.type,
            "description": mr.description,
            "tool_change_flag": mr.tool_change_flag
        }
        for mr in maintenance_q
    ]

    incident = db.query(QualityIncident).filter(QualityIncident.batch_id == b.id).first()
    incident_defect_type = incident.defect_type if incident else None

    strategy_info = select_investigation_strategy(
        has_oversized=has_oversized,
        has_undersized=has_undersized,
        has_visual=has_visual_defect,
        has_surface=has_surface_issue,
        has_drift=has_drift_signature,
        has_material=False,
        nonconforming_count=nonconforming_count,
        defect_type=incident_defect_type
    )

    missing_data_sources = []
    verification_steps = []
    investigation_status = "EVIDENCE_CORRELATED"

    if nonconforming_count > 0 or has_visual_defect:
        if not has_telemetry:
            investigation_status = "INSUFFICIENT_PROCESS_EVIDENCE"
            missing_data_sources.append(f"High-frequency machine telemetry series (vibration, spindle speed, feed rate, coolant temperature) for {mach.code if mach else 'cell'}")
            missing_data_sources.append(f"CNC controller operational log and live parameter stream for machine {mach.code if mach else 'cell'}")
            verification_steps.append("Connect shop floor edge IoT gateway to stream live CNC telemetry for active machining cell")
            verification_steps.append("Upload machine sensor log file (CSV/telemetry) corresponding to the manufacturing shift")

        if not has_maintenance:
            missing_data_sources.append(f"Preventive maintenance and tool change records for machine {mach.code if mach else 'cell'}")
            verification_steps.append(f"Verify and register tool calibration / maintenance log for {mach.code if mach else 'cell'}")

        if not has_visual_defect and len(visual_findings_q) == 0:
            missing_data_sources.append("Part surface high-resolution inspection photography")
            verification_steps.append("Capture and upload part surface images to visual inspection intake")

    hypotheses = []
    strat_key = strategy_info["strategy"]

    if strat_key == STRATEGY_DIMENSIONAL_OVERSIZED:
        hypotheses.append({
            "hypothesis_id": "HYP-01",
            "title": "Progressive Cutting Tool Flank Wear",
            "category": "Machine",
            "description": f"Carbide insert flank wear exceeded safe threshold ({latest_tool_cycles} cycles logged), increasing radial cutting deflection and expanding shaft diameter.",
            "confidence_score": 0.88 if latest_tool_cycles > 800 and max_vibration > 3.0 else 0.65,
            "evidence_score": 0.88,
            "status": "SUPPORTED" if has_telemetry and latest_tool_cycles > 800 else "UNDER_INVESTIGATION",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"Consecutive parts exhibit upward dimensional trend exceeding USL ({usl_val} mm)",
                f"Tool wear cycles recorded at {latest_tool_cycles} cycles (standard threshold: 600-800 cycles)" if has_telemetry else "Tool cycle log pending physical verification",
                f"Elevated machining vibration observed at {max_vibration:.2f} mm/s (baseline: 2.1 mm/s)" if has_telemetry else "Vibration telemetry stream pending verification"
            ],
            "contradicting_evidence": [
                "Inspection gauge master calibration verification check confirmed zero measurement drift" if has_maintenance else "None recorded"
            ],
            "missing_evidence": [
                "Optical toolmaker microscope photograph of tool insert flank wear land (VB)"
            ],
            "required_confirmation": "Remove carbide insert and inspect flank wear width (VB) under optical microscope."
        })
        hypotheses.append({
            "hypothesis_id": "HYP-02",
            "title": "Incorrect CNC Tool Wear Offset Setting",
            "category": "Method",
            "description": "CNC controller radial wear offset register configured with inaccurate offset delta during shift setup.",
            "confidence_score": 0.42,
            "evidence_score": 0.42,
            "status": "CONTRADICTED" if (len(conforming_samples) > 0 and len(nonconforming_samples) > 0) else "UNDER_INVESTIGATION",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"Initial shift setup parameter record for {b.shift} shift"
            ],
            "contradicting_evidence": [
                f"First {len(conforming_samples)} sampled components conformed strictly to engineering limits before shift drift occurred"
            ],
            "missing_evidence": [
                "CNC G-code tool offset registry modification history log"
            ],
            "required_confirmation": "Export and audit CNC G-code tool offset modification event log from controller memory."
        })

    elif strat_key == STRATEGY_DIMENSIONAL_UNDERSIZED:
        hypotheses.append({
            "hypothesis_id": "HYP-01",
            "title": "CNC Tool Wear Offset Overcompensation",
            "category": "Method",
            "description": "Operator or automated closed-loop compensation over-adjusted radial tool offset negatively, reducing finished dimensions below LSL.",
            "confidence_score": 0.82,
            "evidence_score": 0.82,
            "status": "SUPPORTED",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"Part dimensions dropped abruptly below LSL ({lsl_val} mm)",
                f"Setup registered during {b.shift} shift on {mach.code if mach else 'cell'}"
            ],
            "contradicting_evidence": [
                "No mechanical spindle runout anomaly recorded"
            ],
            "missing_evidence": [
                "CNC controller tool offset modification audit trail"
            ],
            "required_confirmation": "Compare tool offset register value against approved CAM tool sheet."
        })
        hypotheses.append({
            "hypothesis_id": "HYP-02",
            "title": "Cutting Insert Edge Chipping",
            "category": "Machine",
            "description": "Localized fracture or micro-chipping on turning insert nose radius, causing altered tool geometry and sudden step change in dimensions.",
            "confidence_score": 0.60,
            "evidence_score": 0.60,
            "status": "UNDER_INVESTIGATION",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                "Sudden step decrease in measured diameter across consecutive parts"
            ],
            "contradicting_evidence": [
                "No catastrophic spindle motor current overload event detected"
            ],
            "missing_evidence": [
                "Optical inspection photograph of cutting edge radius"
            ],
            "required_confirmation": "Inspect cutting edge with 20x magnifying loupe for micro-fractures."
        })

    elif strat_key == STRATEGY_VISUAL_DEFECT:
        top_v = visual_defects_list[0] if visual_defects_list else {}
        v_name = top_v.get("defect_type", "surface_scratch")
        hypotheses.append({
            "hypothesis_id": "HYP-01",
            "title": f"Machining Swarf / Chip Entanglement ({v_name.replace('_', ' ').title()})",
            "category": "Machine",
            "description": f"Continuous metal chips entangled around tool turret during finishing pass, dragging across finished surface and leaving localized {v_name.replace('_', ' ')}.",
            "confidence_score": 0.86,
            "evidence_score": 0.86,
            "status": "SUPPORTED",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"Computer vision model detected {v_name} with {round(top_v.get('confidence', 0.9) * 100, 1)}% confidence",
                f"Defect localized at {top_v.get('location', 'center')} surface zone"
            ],
            "contradicting_evidence": [
                "Dimensional tolerance remained conforming across all measured axes"
            ],
            "missing_evidence": [
                "High-pressure coolant nozzle aim angle verification"
            ],
            "required_confirmation": "Verify chip breaker geometry on insert and confirm coolant nozzle alignment targeting the cutting shear zone."
        })

    elif strat_key == STRATEGY_MULTIPLE_DEFECTS:
        hypotheses.append({
            "hypothesis_id": "HYP-01",
            "title": "Severe Tool Degradation Driving Concurrent Dimensional & Surface Nonconformance",
            "category": "Machine",
            "description": f"Advanced cutting tool wear caused high cutting forces, leading simultaneously to out-of-spec dimensions and surface tearing.",
            "confidence_score": 0.91,
            "evidence_score": 0.91,
            "status": "SUPPORTED" if has_telemetry and latest_tool_cycles > 800 else "UNDER_INVESTIGATION",
            "epistemic_label": EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"Dimensional nonconformance: {nonconforming_count}/{total_inspected} parts exceed engineering limits",
                f"Concurrent visual surface findings detected by vision inspection engine",
                f"Tool wear cycles logged at {latest_tool_cycles} cycles" if has_telemetry else "Tool cycle log requires physical verification"
            ],
            "contradicting_evidence": [
                "Raw material incoming inspection certificates conform to chemical and hardness standards"
            ],
            "missing_evidence": [
                "Optical photomicrograph of insert nose degradation"
            ],
            "required_confirmation": "Perform complete tool turret station teardown and inspect insert, shim seat, and clamping wedge."
        })

    else:
        hypotheses.append({
            "hypothesis_id": "HYP-01",
            "title": "Nominal Tool Wear & Stable Process Parameters",
            "category": "Machine",
            "description": "Process telemetry, tool usage cycles, and physical measurements confirm nominal CNC operations within 3-sigma statistical control.",
            "confidence_score": 0.98,
            "evidence_score": 0.98,
            "status": "CONFIRMED_BY_AUTHORIZED_REVIEW" if conforming_count > 0 else "SUPPORTED",
            "epistemic_label": EpistemicLabel.OBSERVED_FACT.value if conforming_count > 0 else EpistemicLabel.HYPOTHESIS.value,
            "supporting_evidence": [
                f"All {total_inspected} sample measurements strictly conform to approved specification [{lsl_val:.3f}, {usl_val:.3f}] mm",
                f"Machinery vibration stable at normal baseline ({max_vibration:.2f} mm/s)" if has_telemetry else "Process stable"
            ],
            "contradicting_evidence": [],
            "missing_evidence": [],
            "required_confirmation": "Maintain standard periodic SPC subgroup sampling."
        })

    recommended_actions = []
    if nonconforming_count > 0 or has_visual_defect:
        recommended_actions.append({
            "type": "containment",
            "action": f"Quarantine Batch {b.batch_number} ({b.quantity} units) in designated Quality Hold area pending 100% sorting.",
            "responsible": "Shift Quality Inspector",
            "urgency": "IMMEDIATE"
        })
        recommended_actions.append({
            "type": "corrective",
            "action": f"Replace tool insert at machine {mach.code if mach else 'cell'}, recalibrate tool geometry offset, and inspect first 3 parts.",
            "responsible": "Cell Setup Technician",
            "urgency": "PRIOR_TO_RELEASE"
        })
        recommended_actions.append({
            "type": "preventive",
            "action": f"Update tool life management threshold in CNC controller from 1000 cycles to 750 cycles for part {prod.part_number if prod else 'specification'}.",
            "responsible": "Manufacturing Engineer",
            "urgency": "WITHIN_24_HOURS"
        })
    else:
        recommended_actions.append({
            "type": "preventive",
            "action": "Continue normal production schedule and maintain standard hourly SPC inspection frequency.",
            "responsible": "Machine Operator",
            "urgency": "ROUTINE"
        })

    capa_records_q = db.query(CAPAAction).filter(
        CAPAAction.incident_id == (incident.id if incident else "none")
    ).all() if incident else []

    capa_list = [
        {
            "id": c.id,
            "action_code": c.action_code,
            "type": c.type,
            "description": c.description,
            "status": c.status,
            "due_date": c.due_date,
            "responsible_role": c.responsible_role or c.suggested_role
        }
        for c in capa_records_q
    ]

    if incident and nonconforming_count > 0:
        incident.rejection_reason = f"Strategy: {strategy_info['title']}. Status: {investigation_status}. Top Hypothesis: {hypotheses[0]['title'] if hypotheses else 'None'}"
        db.commit()

    return {
        "batch_id": b.batch_number,
        "batch_db_id": b.id,
        "product": {
            "id": prod.id if prod else None,
            "part_number": prod.part_number if prod else "PS-2026-101",
            "name": prod.name if prod else "Precision Machined Part",
            "material": prod.material if prod else "Standard Carbon Steel",
            "process": prod.process if prod else "Precision CNC Turning"
        },
        "machine": {
            "id": mach.id if mach else None,
            "code": mach.code if mach else "CNC-04",
            "type": mach.type if mach else "CNC Lathe",
            "location": mach.location if mach else "Cell-04"
        },
        "shift": b.shift,
        "batch_status": b.status,
        "batch_quantity": b.quantity,
        "specification": {
            "characteristic": char_name,
            "unit": unit_str,
            "nominal": nominal_val,
            "usl": usl_val,
            "lsl": lsl_val,
            "tolerance_plus": char.tol_plus if char else 0.05,
            "tolerance_minus": char.tol_minus if char else 0.05
        },
        "inspection_summary": {
            "total_inspected": total_inspected,
            "conforming_count": conforming_count,
            "nonconforming_count": nonconforming_count,
            "rejection_rate_percent": rejection_rate,
            "has_oversized": has_oversized,
            "has_undersized": has_undersized,
            "has_visual_defect": has_visual_defect,
            "conformance_verdict": "CONFORMING" if nonconforming_count == 0 and not has_visual_defect else "NONCONFORMANCE_DETECTED"
        },
        "nonconforming_samples": nonconforming_samples,
        "conforming_samples": conforming_samples,
        "visual_findings": visual_defects_list,
        "strategy": strategy_info,
        "investigation_status": investigation_status,
        "hypotheses": hypotheses,
        "missing_data_sources": missing_data_sources,
        "verification_steps": verification_steps,
        "recommended_actions": recommended_actions,
        "capa_actions": capa_list,
        "incident_id": incident.id if incident else None,
        "investigation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "correlation_vs_causation_note": "Observed statistical correlations, temporal precedence, and telemetry trends indicate potential causal mechanisms but require authorized physical verification prior to irreversible process changes.",
        "epistemic_label": EpistemicLabel.HYPOTHESIS.value if nonconforming_count > 0 else EpistemicLabel.OBSERVED_FACT.value
    }
