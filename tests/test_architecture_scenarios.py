import os
import io
import math
import pytest
from datetime import datetime, timezone
from pypdf import PdfReader
from scipy import stats

from backend.app.orchestrator.engine import orchestrator
from backend.app.agents.visual_agent import vision_agent
from backend.app.agents.dimensional_agent import compliance_agent
from backend.app.agents.process_agent import anomaly_agent
from backend.app.agents.spc_agent import spc_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.agents.reviewer_agent import critic_agent
from backend.app.agents.capa_agent import capa_agent
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.services.effectiveness import effectiveness_engine
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    Batch, Product, Measurement, ProcessReading, HumanDecision,
    CAPAAction, RCAHypothesis, QualityIncident
)
from backend.app.schemas.schemas import HumanApprovalRequest, CertaintyLevel

def test_scenario_a_conforming_batch():
    batch_meta = {
        "batch_id": "BATCH-CONF-001",
        "part_number": "PS-2026-101",
        "part_name": "Precision Ground Shaft",
        "machine": "CNC-04",
        "quantity": 100,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "usl": 50.05,
        "lsl": 49.95
    }
    meas = [
        {"sample_id": f"P00{i}", "measured_value": 50.00 + (i - 3) * 0.01, "unit": "mm"}
        for i in range(1, 6)
    ]
    tele = [
        {
            "timestamp": "2026-10-12T01:00:00",
            "vibration_mm_s": 2.1,
            "tool_wear_cycles": 300,
            "spindle_speed_rpm": 1200,
            "feed_rate_mm_rev": 0.20,
            "temperature_c": 24.0
        }
    ]

    state = orchestrator.run_full_pipeline(
        batch_meta=batch_meta,
        measurements=meas,
        telemetry_records=tele,
        image_path=None
    )

    assert state.status == "CONFORMING_AUDITED"
    assert state.has_defects is False
    assert state.has_anomalies is False
    assert state.has_spc_violations is False

    assert state.stage_statuses["intake"] == "COMPLETED"
    assert state.stage_statuses["compliance"] == "COMPLETED"
    assert state.stage_statuses["anomaly"] == "COMPLETED"
    assert state.stage_statuses["spc"] == "COMPLETED"
    assert state.stage_statuses["rca"] == "SKIPPED"
    assert state.stage_statuses["critic"] == "SKIPPED"
    assert state.stage_statuses["capa"] == "SKIPPED"
    assert state.stage_statuses["approval"] == "SKIPPED"
    assert state.stage_statuses["report"] == "COMPLETED"

    assert state.rca_report is None
    assert state.capa_report is None

def test_scenario_b_dimensional_nonconformance_boundary_math():
    nom = 50.00
    tol = 0.05
    usl = nom + tol
    lsl = nom - tol

    test_samples = [
        {"sample_id": "P-BELOW-LSL", "measured_value": 49.90, "unit": "mm"},
        {"sample_id": "P-EXACT-LSL", "measured_value": 49.95, "unit": "mm"},
        {"sample_id": "P-NOMINAL",   "measured_value": 50.00, "unit": "mm"},
        {"sample_id": "P-EXACT-USL", "measured_value": 50.05, "unit": "mm"},
        {"sample_id": "P-ABOVE-USL", "measured_value": 50.08, "unit": "mm"},
    ]

    res = compliance_agent.evaluate_compliance(
        batch_id="TC-SCENARIO-B",
        measurements=test_samples,
        nominal_mm=nom,
        tolerance_mm=tol
    )
    rep = res["report"]

    nonconforming_expected = [s for s in test_samples if s["measured_value"] < lsl or s["measured_value"] > usl]
    conforming_expected = [s for s in test_samples if lsl <= s["measured_value"] <= usl]

    assert rep.total_inspected == len(test_samples)
    assert rep.nonconforming == len(nonconforming_expected) == 2
    assert rep.accepted == len(conforming_expected) == 3
    assert math.isclose(rep.rejection_rate_percent, (2 / 5) * 100.0, rel_tol=1e-3)

    details_map = {d.sample_id: d for d in rep.measurements}
    assert details_map["P-BELOW-LSL"].is_conforming is False
    assert math.isclose(details_map["P-BELOW-LSL"].deviation_from_nominal, -0.10, rel_tol=1e-3)
    assert details_map["P-EXACT-LSL"].is_conforming is True
    assert details_map["P-EXACT-USL"].is_conforming is True
    assert details_map["P-ABOVE-USL"].is_conforming is False
    assert math.isclose(details_map["P-ABOVE-USL"].deviation_from_nominal, 0.08, rel_tol=1e-3)

def test_scenario_c_visual_defect_execution():
    img_path = os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    assert os.path.exists(img_path)

    res = vision_agent.inspect(image_path=img_path, batch_id="TC-SCENARIO-C", image_id="IMG-001")
    pred = res["prediction"]

    assert pred.defect_detected is True
    assert pred.defect_type == "thread_damage"
    assert pred.confidence >= 0.70
    assert pred.location_zone == "mid_region"
    assert pred.certainty.value == "Model Prediction"

def test_scenario_d_product_image_mismatch_quarantine():
    screw_img = os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "part_name": "Precision Ground Shaft",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        },
        image_path=screw_img
    )

    assert state.product_mismatch is True
    assert "PRODUCT MISMATCH DETECTED" in state.product_mismatch_warning
    assert "screw" in state.product_mismatch_warning.lower()
    assert state.visual_prediction.product_mismatch is True

    top_hypo = state.rca_report.ranked_hypotheses[0]
    assert "thread" not in top_hypo.title.lower()

def test_scenario_e_telemetry_anomaly_detection():
    telemetry = [
        {"timestamp": f"2026-10-12T0{i}:00:00", "vibration_mm_s": 2.0, "tool_wear_cycles": 500, "spindle_speed_rpm": 1200, "feed_rate_mm_rev": 0.20, "temperature_c": 24.0}
        for i in range(1, 5)
    ]
    telemetry.append({
        "timestamp": "2026-10-12T05:00:00",
        "vibration_mm_s": 3.8,
        "tool_wear_cycles": 1150,
        "spindle_speed_rpm": 1200,
        "feed_rate_mm_rev": 0.20,
        "temperature_c": 25.0
    })

    res = anomaly_agent.analyze_telemetry_series(
        batch_id="TC-SCENARIO-E",
        machine="CNC-04",
        telemetry_records=telemetry
    )
    rep = res["report"]

    assert rep.anomalies_detected > 0
    assert rep.vibration_current >= 3.5
    assert rep.vibration_status in ["ELEVATED_WARNING", "ABNORMAL_CRITICAL"]
    assert rep.tool_cycles_current >= 1000

def test_scenario_f_spc_and_distinct_limits():
    values = [50.01, 50.03, 50.06, 50.08, 50.07]
    usl = 50.05
    lsl = 49.95
    nom = 50.00

    res = spc_agent.analyze_process_capability_and_control(
        batch_id="TC-SCENARIO-F",
        values=values,
        usl=usl,
        lsl=lsl,
        nominal=nom
    )
    rep = res["report"]

    assert rep.ucl != usl
    assert rep.lcl != lsl
    assert rep.capability_assessment is not None
    assert "statistical control limits" in rep.distinction_warning.lower()

def test_scenario_g_historical_evidence_and_rca():
    res = rca_agent.analyze_incident(
        incident_id="INC-SCENARIO-G",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.8,
        tool_cycles=1150,
        category="precision_shaft"
    )
    rep = res["report"]

    assert len(rep.ranked_hypotheses) > 0
    top_hypo = rep.ranked_hypotheses[0]
    assert "Tool" in top_hypo.title or "Wear" in top_hypo.title
    assert top_hypo.epistemic_label == "HYPOTHESIS"
    assert len(top_hypo.supporting_evidence) > 0

    assert len(rep.historical_matches) > 0
    ncr_ids = [m.incident_id for m in rep.historical_matches]
    assert any("019" in nid or "NCR" in nid for nid in ncr_ids)

def test_scenario_h_reviewer_correction_loop():
    intake = {"batch_data": {"nominal_mm": 50.0, "tolerance_mm": 0.05}}
    comp = {"report": {"usl": 50.05, "lsl": 49.95}}
    rca = {
        "report": {
            "ranked_hypotheses": [
                {
                    "title": "Unverified Tool Breakage",
                    "description": "Tool definitely broke causing defect",
                    "status": "Confirmed",
                    "supporting_evidence": ["Statistical correlation"],
                    "required_confirmation": "Microscope check"
                }
            ]
        }
    }

    res = critic_agent.review_workflow(
        intake_data=intake,
        compliance_data=comp,
        vision_data=None,
        anomaly_data={"report": {}},
        spc_data={"report": {}},
        rca_data=rca,
        capa_data=None
    )
    rev = res["review"]

    assert rev.critic_verdict in ["REASSESS", "REASSESSMENT_REQUIRED", "NEEDS_REVISION"]
    assert any("Confirmed prior to physical" in c or "Unsupported" in c or "CRITIC" in c for c in rev.review_comments)

def test_scenario_i_human_approval_gate_and_reassessment():
    state = orchestrator.run_full_pipeline(
        batch_meta={"batch_id": "BATCH-HITL-TEST", "nominal_mm": 50.00, "tolerance_mm": 0.05},
        measurements=[{"sample_id": "P01", "measured_value": 50.08, "unit": "mm"}]
    )
    w_id = state.workflow_id

    assert state.status == "PENDING_HUMAN_APPROVAL"
    assert state.stage_statuses["approval"] == "PENDING"

    with pytest.raises(Exception):
        orchestrator.resume_workflow(
            workflow_id=w_id,
            payload=HumanApprovalRequest(approved_by="Sarah Chen", decision="REJECT_BATCH", engineering_comments="", disposition="REJECT_BATCH"),
            current_user={"id": "usr-qe", "name": "QE", "role": "quality_engineer"}
        )

    signoff = orchestrator.resume_workflow(
        workflow_id=w_id,
        payload=HumanApprovalRequest(
            approved_by="Sarah Chen",
            decision="QUARANTINE_BATCH",
            engineering_comments="Confirmed flank wear VB=0.38mm under microscope. Quarantining batch for 100% sort.",
            disposition="QUARANTINE_BATCH",
            confirmed_root_cause="Progressive Tool Flank Wear (Confirmed via Optical Toolmakers Microscope)"
        ),
        current_user={"id": "usr-qe", "name": "Sarah Chen", "role": "quality_engineer"}
    )

    assert signoff["status"] == "RESUMED_AND_COMPLETED"
    assert signoff["decision"] == "QUARANTINE_BATCH"
    assert signoff["certainty"] == "Confirmed Root Cause"

    final_wf = orchestrator.get_workflow(w_id)
    assert final_wf.stage_statuses["approval"] == "COMPLETED"
    assert final_wf.stage_statuses["effectiveness"] == "COMPLETED"
    assert final_wf.stage_statuses["report"] == "COMPLETED"

def test_scenario_j_effectiveness_monitoring_two_proportion_z_test():
    db = SessionLocal()
    eff = effectiveness_engine.evaluate_capa_effectiveness(capa_id="CAPA-2026-001", db=db)
    db.close()

    assert eff["sample_before_count"] == 1000
    assert eff["defects_before_count"] == 82
    assert math.isclose(eff["rejection_rate_before_percent"], 8.2, rel_tol=1e-3)

    assert eff["sample_after_count"] == 1000
    assert eff["defects_after_count"] == 11
    assert math.isclose(eff["rejection_rate_after_percent"], 1.1, rel_tol=1e-3)

    n1, x1 = 1000, 82
    n2, x2 = 1000, 11
    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    expected_z = (p1 - p2) / se_pool

    assert math.isclose(eff["z_statistic"], expected_z, rel_tol=1e-2)
    assert eff["p_value"] < 0.0001
    assert "causation not established" in eff["conclusion_label"].lower()

def test_scenario_k_api_checkpoint_retrieval():
    state = orchestrator.run_full_pipeline(
        batch_meta={"batch_id": "BATCH-REOPEN-TEST", "nominal_mm": 50.00, "tolerance_mm": 0.05},
        measurements=[{"sample_id": "P01", "measured_value": 50.07, "unit": "mm"}]
    )
    w_id = state.workflow_id

    loaded_wf = orchestrator.get_workflow(w_id)
    assert loaded_wf is not None
    assert getattr(loaded_wf, "workflow_id", None) == w_id or loaded_wf.get("workflow_id") == w_id

    latest_wf = orchestrator.get_latest_workflow_for_batch("BATCH-REOPEN-TEST")
    assert latest_wf is not None
    assert getattr(latest_wf, "workflow_id", None) == w_id or latest_wf.get("workflow_id") == w_id

def test_scenario_l_pdf_all_13_sections_and_reconciliation():
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "part_name": "Precision Ground Shaft",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        },
        image_path=os.path.abspath("backend/app/static/uploads/samples/screw_thread.png")
    )

    pdf_bytes = generate_quality_pdf_report(state.model_dump())
    reader = PdfReader(io.BytesIO(pdf_bytes))

    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    required_sections = [
        "1. Product Details",
        "2. Batch Information",
        "3. Inspection Summary",
        "4. Visual Inspection",
        "5. Dimensional Analysis",
        "6. SPC",
        "7. Process Anomalies",
        "8. Root Cause Analysis",
        "9. Historical Quality Precedents",
        "10. Containment Actions",
        "11. Corrective & Preventive Actions",
        "12. Human Quality Engineer Disposition",
        "13. Corrective Action Effectiveness"
    ]

    for sec in required_sections:
        assert any(term.lower() in full_text.lower() for term in sec.split()), f"Missing section: {sec}"

    assert "hypothesis" in full_text.lower()
    assert "decision-support only" in full_text.lower()
