import uuid
import time
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.app.agents.intake_agent import data_intake_agent
from backend.app.agents.visual_agent import vision_agent
from backend.app.agents.dimensional_agent import compliance_agent
from backend.app.agents.process_agent import anomaly_agent
from backend.app.agents.spc_agent import spc_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.agents.capa_agent import capa_agent
from backend.app.agents.reviewer_agent import critic_agent

class QualityWorkflowGraphState(TypedDict, total=False):
    workflow_id: str
    batch_id: str
    status: str
    current_agent: str
    batch_metadata: Dict[str, Any]
    measurements: List[Dict[str, Any]]
    image_path: Optional[str]
    telemetry_records: Optional[List[Dict[str, Any]]]
    visual_prediction: Optional[Dict[str, Any]]
    dimensional_report: Optional[Dict[str, Any]]
    process_report: Optional[Dict[str, Any]]
    spc_report: Optional[Dict[str, Any]]
    rca_report: Optional[Dict[str, Any]]
    capa_report: Optional[Dict[str, Any]]
    critic_review: Optional[Dict[str, Any]]
    human_approval: Optional[Dict[str, Any]]
    execution_trace: List[Dict[str, Any]]
    has_defects: bool
    has_anomalies: bool
    has_spc_violations: bool
    reassessment_loops: int
    product_mismatch: Optional[bool]
    product_mismatch_warning: Optional[str]
    error_message: Optional[str]

def node_intake(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_meta = state.get("batch_metadata", {})
    raw_m = state.get("measurements")
    res = data_intake_agent.process_batch_and_measurements(batch_meta=batch_meta, raw_measurements=raw_m)
    
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    return {
        "current_agent": data_intake_agent.name,
        "batch_metadata": res["batch_data"],
        "execution_trace": trace
    }

def node_visual(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    img_path = state.get("image_path")
    batch_id = state.get("batch_id", "BATCH-0245")
    trace = list(state.get("execution_trace", []))
    
    if img_path:
        res = vision_agent.inspect(image_path=img_path, batch_id=batch_id, image_id=f"IMG-{batch_id}")
        pred = res["prediction"].model_dump()
        trace.append(res["log"].model_dump())

        batch_meta = state.get("batch_metadata", {})
        batch_prod = (batch_meta.get("part_name") or batch_meta.get("product_name") or "Precision Ground Shaft").lower()
        img_cat = (pred.get("product_category") or pred.get("category") or "").lower()

        is_mismatch = False
        mismatch_msg = None
        if ("shaft" in batch_prod and "shaft" not in img_cat) or ("screw" in batch_prod and "screw" not in img_cat):
            is_mismatch = True
            mismatch_msg = (
                f"PRODUCT MISMATCH DETECTED: Uploaded inspection image represents category '{img_cat}' "
                f"({pred.get('defect_type')}), but selected batch {batch_id} is for product '{batch_meta.get('part_name', 'Precision Ground Shaft')}'. "
                f"Finding quarantined from batch dimensional disposition."
            )
            pred["product_mismatch"] = True
            pred["mismatch_warning"] = mismatch_msg

        has_def = bool(pred.get("defect_detected", False)) and not is_mismatch
        return {
            "current_agent": vision_agent.name,
            "visual_prediction": pred,
            "product_mismatch": is_mismatch,
            "product_mismatch_warning": mismatch_msg,
            "has_defects": has_def or state.get("has_defects", False),
            "execution_trace": trace
        }
    return {
        "current_agent": vision_agent.name,
        "execution_trace": trace
    }

def node_compliance(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_id = state.get("batch_id", "BATCH-0245")
    meta = state.get("batch_metadata", {})
    meas = meta.get("measurements", [])
    nom = meta.get("nominal_mm", 50.00)
    tol = meta.get("tolerance_mm", 0.05)
    
    res = compliance_agent.evaluate_compliance(batch_id=batch_id, measurements=meas, nominal_mm=nom, tolerance_mm=tol)
    rep = res["report"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    has_def = (rep.get("nonconforming", 0) > 0) or state.get("has_defects", False)
    return {
        "current_agent": compliance_agent.name,
        "dimensional_report": rep,
        "has_defects": has_def,
        "execution_trace": trace
    }

def node_anomaly(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_id = state.get("batch_id", "BATCH-0245")
    meta = state.get("batch_metadata", {})
    machine = meta.get("machine", "CNC-04")
    telemetry = state.get("telemetry_records")
    
    res = anomaly_agent.analyze_telemetry_series(batch_id=batch_id, machine=machine, telemetry_records=telemetry)
    rep = res["report"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    has_anom = (rep.get("anomalies_detected", 0) > 0)
    return {
        "current_agent": anomaly_agent.name,
        "process_report": rep,
        "has_anomalies": has_anom,
        "execution_trace": trace
    }

def node_spc(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_id = state.get("batch_id", "BATCH-0245")
    meta = state.get("batch_metadata", {})
    meas = meta.get("measurements", [])
    raw_vals = [m["measured_value"] for m in meas] if meas else [50.01, 50.03, 50.06, 50.08, 50.07]
    usl = meta.get("usl", 50.05)
    lsl = meta.get("lsl", 49.95)
    nom = meta.get("nominal_mm", 50.00)
    
    res = spc_agent.analyze_process_capability_and_control(batch_id=batch_id, values=raw_vals, usl=usl, lsl=lsl, nominal=nom)
    rep = res["report"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    has_spc = bool(len(rep.get("nelson_violations", [])) > 0 or (rep.get("cpk") is not None and rep.get("cpk") < 1.0))
    return {
        "current_agent": spc_agent.name,
        "spc_report": rep,
        "has_spc_violations": has_spc,
        "execution_trace": trace
    }

def node_rca(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_id = state.get("batch_id", "BATCH-0245")
    proc = state.get("process_report", {})
    vib = proc.get("vibration_current", 3.8)
    cyc = proc.get("tool_cycles_current", 1150)
    v_pred = state.get("visual_prediction")
    d_rep = state.get("dimensional_report")
    
    dt = "Oversized shaft diameter"
    cat = "precision_shaft"
    is_mismatch = state.get("product_mismatch", False) or (v_pred and v_pred.get("product_mismatch", False))
    if v_pred and v_pred.get("defect_detected") and not is_mismatch:
        dt = v_pred.get("defect_type", dt)
        cat = v_pred.get("category", cat)
    elif d_rep and d_rep.get("nonconforming", 0) > 0:
        dt = "Oversized shaft diameter"
    
    try:
        from backend.app.database.session import SessionLocal
        from backend.app.database.models import QualityIncident, Batch
        db = SessionLocal()
        b = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
        b_id = b.id if b else batch_id
        existing_inc = db.query(QualityIncident).filter(QualityIncident.batch_id == b_id).first()
        if not existing_inc:
            new_inc = QualityIncident(
                id=f"INC-{batch_id}",
                batch_id=b_id,
                title=f"Dimensional Non-Conformance: {dt}",
                defect_type=dt,
                severity="HIGH",
                status="OPEN"
            )
            db.add(new_inc)
            db.commit()
        db.close()
    except Exception:
        pass
    
    meas_items = (d_rep.get("measurements") if d_rep else None) or state.get("batch_metadata", {}).get("measurements", [])
    actual_usl = (d_rep.get("usl") if d_rep else None) or state.get("batch_metadata", {}).get("usl", 50.05) or 50.05
    if meas_items:
        max_val = max(float(m.get("measured_value", 0.0)) for m in meas_items)
    else:
        max_val = actual_usl + 0.03

    res = rca_agent.analyze_incident(
        incident_id=f"INC-{batch_id}",
        batch_id=batch_id,
        defect_type=dt,
        max_measured_val=max_val,
        usl=actual_usl,
        vibration_val=vib,
        tool_cycles=cyc,
        visual_prediction=v_pred,
        dimensional_findings=d_rep,
        category=cat
    )

    rep = res["report"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    return {
        "current_agent": rca_agent.name,
        "rca_report": rep,
        "execution_trace": trace
    }

def node_capa(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    batch_id = state.get("batch_id", "BATCH-0245")
    meta = state.get("batch_metadata", {})
    machine = meta.get("machine", "CNC-04")
    rca_report = state.get("rca_report")
    
    res = capa_agent.generate_capa_plan(
        incident_id=f"INC-{batch_id}",
        batch_id=batch_id,
        machine=machine,
        rca_report=rca_report
    )
    rep = res["capa"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    return {
        "status": "DISPOSITION_READY",
        "current_agent": capa_agent.name,
        "capa_report": rep,
        "execution_trace": trace
    }

def node_critic(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    meta = state.get("batch_metadata", {})
    dim = state.get("dimensional_report", {})
    vis = state.get("visual_prediction")
    proc = state.get("process_report", {})
    spc = state.get("spc_report", {})
    rca = state.get("rca_report", {})
    capa = state.get("capa_report", {})
    
    res = critic_agent.review_workflow(
        intake_data={"batch": meta},
        compliance_data={"report": dim},
        vision_data={"prediction": vis} if vis else None,
        anomaly_data={"report": proc},
        spc_data={"report": spc},
        rca_data={"report": rca},
        capa_data={"capa": capa}
    )
    rev = res["review"].model_dump()
    trace = list(state.get("execution_trace", []))
    trace.append(res["log"].model_dump())
    
    return {
        "current_agent": critic_agent.name,
        "critic_review": rev,
        "execution_trace": trace
    }

def node_approval_gate(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    return {
        "status": "AWAITING_HUMAN_APPROVAL",
        "current_agent": "Human Gatekeeper"
    }

def node_report(state: QualityWorkflowGraphState) -> Dict[str, Any]:
    is_conforming = not state.get("has_defects", False) and not state.get("has_anomalies", False)
    final_status = "CONFORMING_AUDITED" if is_conforming else "DISPOSITION_READY"
    return {
        "status": final_status,
        "current_agent": "Report Compiler"
    }

def route_after_intake(state: QualityWorkflowGraphState) -> str:
    meta = state.get("batch_metadata", {})
    if meta.get("needs_info", False):
        return END
    return "visual_inspection"

def route_after_spc(state: QualityWorkflowGraphState) -> str:
    if not state.get("has_defects", False) and not state.get("has_anomalies", False) and not state.get("has_spc_violations", False):
        return "final_report"
    return "root_cause_analysis"

def route_after_critic(state: QualityWorkflowGraphState) -> str:
    rev = state.get("critic_review", {})
    loops = state.get("reassessment_loops", 0)
    if rev.get("critic_verdict") in ("REASSESS", "REASSESSMENT_REQUIRED") and loops < 2:
        state["reassessment_loops"] = loops + 1
        return "root_cause_analysis"
    return "capa_management"

def create_qualitymind_graph():
    builder = StateGraph(QualityWorkflowGraphState)

    builder.add_node("intake", node_intake)
    builder.add_node("visual_inspection", node_visual)
    builder.add_node("compliance", node_compliance)
    builder.add_node("anomaly_detection", node_anomaly)
    builder.add_node("spc", node_spc)
    builder.add_node("root_cause_analysis", node_rca)
    builder.add_node("critic", node_critic)
    builder.add_node("capa_management", node_capa)
    builder.add_node("approval_gate", node_approval_gate)
    builder.add_node("final_report", node_report)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", route_after_intake, {
        "visual_inspection": "visual_inspection",
        END: END
    })
    builder.add_edge("visual_inspection", "compliance")
    builder.add_edge("compliance", "anomaly_detection")
    builder.add_edge("anomaly_detection", "spc")
    
    builder.add_conditional_edges("spc", route_after_spc, {
        "root_cause_analysis": "root_cause_analysis",
        "final_report": "final_report"
    })

    builder.add_edge("root_cause_analysis", "critic")
    
    builder.add_conditional_edges("critic", route_after_critic, {
        "root_cause_analysis": "root_cause_analysis",
        "capa_management": "capa_management"
    })

    builder.add_edge("capa_management", "approval_gate")
    builder.add_edge("approval_gate", "final_report")
    builder.add_edge("final_report", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer, interrupt_before=["approval_gate"])
    return graph

qualitymind_langgraph = create_qualitymind_graph()

