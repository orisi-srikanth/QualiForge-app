"""
Multi-Agent Orchestrator & Human-in-the-Loop Workflows
Coordinates execution through all 8 agents and enforces human decision gates.
"""
import os
import json
import html
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.schemas import HumanApprovalRequest, CertaintyLevel
from backend.app.orchestrator.engine import orchestrator
from backend.app.core.security import require_roles, UserRole, require_authenticated_role
from backend.app.database.session import SessionLocal
from backend.app.database.models import HumanDecision, AgentRun, WorkflowStateModel
from backend.app.services.safety_guardrails import safety_guardrail

router = APIRouter()


class ReanalyzeRequest(BaseModel):
    target_agent: str = Field("rca_agent", description="Target agent to re-execute", example="rca_agent")
    comment: str = Field(..., description="Engineering feedback instructions for re-analysis", example="Re-evaluate root cause including morning shift thermal drift readings.")


class WorkflowCommentRequest(BaseModel):
    entity_type: str = Field("batch", description="Entity type: batch, hypothesis, capa, finding", example="batch")
    entity_id: str = Field("BATCH-0245", description="Entity identifier", example="BATCH-0245")
    comment: str = Field(..., description="Engineering observation or investigation note", example="Thermal drift observed on machine CNC-04 spindle bearing.")


class SafetyActionTestRequest(BaseModel):
    action: str = Field(..., description="Autonomous action to test: RELEASE_PRODUCT, REJECT_BATCH, MODIFY_CNC, MODIFY_PLC, STOP_MACHINERY, OVERRIDE_ENGINEER", example="RELEASE_PRODUCT")
    target_id: str = Field("BATCH-0245", description="Target batch or machine", example="BATCH-0245")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Requested machine or PLC parameters")


@router.post("/orchestrator/run", tags=["Workflows (Agents)"], summary="Execute full 8-agent manufacturing quality pipeline", description="Runs end-to-end multi-agent orchestration for specified batch. Pauses execution at human approval gate and persists state to SQLite.")
def run_orchestrated_pipeline(batch_id: str = "BATCH-0245", sample_name: Optional[str] = None, image_name: Optional[str] = None):
    chosen = sample_name or image_name or "IMG-001.png"
    sample_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", chosen))
    state = orchestrator.run_full_pipeline(
        batch_meta={"batch_id": batch_id, "part_number": "PS-2026-101", "machine": "CNC-04", "quantity": 500, "nominal_mm": 50.00, "tolerance_mm": 0.05},
        image_path=sample_img if os.path.exists(sample_img) else None
    )
    return state


@router.post("/orchestrator/langgraph-run", tags=["Workflows (Agents)"], summary="Execute pipeline via compiled LangGraph StateGraph", description="Explicitly executes multi-agent pipeline using compiled LangGraph StateGraph with checkpointing and pauses at approval_gate.")
def run_langgraph_pipeline_endpoint(batch_id: str = "BATCH-0245", sample_name: Optional[str] = None, image_name: Optional[str] = None):
    chosen = sample_name or image_name or "IMG-001.png"
    sample_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", chosen))
    res = orchestrator.run_langgraph_pipeline(
        batch_meta={"batch_id": batch_id, "part_number": "PS-2026-101", "machine": "CNC-04", "quantity": 500, "nominal_mm": 50.00, "tolerance_mm": 0.05},
        image_path=sample_img if os.path.exists(sample_img) else None
    )
    return res


@router.post("/workflows", tags=["Workflows (Agents)"], summary="Initialize new quality inspection workflow", description="Initializes workflow for batch and returns initial checkpointed state.")
def start_workflow(batch_id: str = "BATCH-0245"):
    sample_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", "IMG-001.png"))
    state = orchestrator.run_full_pipeline(
        batch_meta={"batch_id": batch_id, "nominal_mm": 50.00, "tolerance_mm": 0.05},
        image_path=sample_img if os.path.exists(sample_img) else None
    )
    return state


@router.get("/workflows/batch/{batch_id}", tags=["Workflows (Agents)"], summary="Retrieve latest workflow state for a batch", description="Retrieves the most recent workflow execution state for a given batch from memory or persisted SQLite checkpoints.")
def get_batch_latest_workflow(batch_id: str):
    wf = orchestrator.get_latest_workflow_for_batch(batch_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No execution workflow found for batch {batch_id}")
    return wf


@router.get("/workflows/{workflow_id}", tags=["Workflows (Agents)"], summary="Retrieve workflow execution state", description="Retrieves state, agent outputs, and pause gate status for specified workflow.")
def get_workflow_state(workflow_id: str):
    wf = orchestrator.get_workflow(workflow_id)
    if not wf:
        sample_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", "IMG-001.png"))
        wf = orchestrator.run_full_pipeline(
            batch_meta={"batch_id": "BATCH-0245", "nominal_mm": 50.00, "tolerance_mm": 0.05},
            image_path=sample_img if os.path.exists(sample_img) else None,
            workflow_id=workflow_id
        )
    return wf



@router.get("/workflows/{workflow_id}/trace", tags=["Workflows (Agents)"], summary="Retrieve multi-agent execution trace", description="Returns detailed agent execution step logs, timestamps, and input/output summaries.")
def get_workflow_trace(workflow_id: str):
    wf = orchestrator.get_workflow(workflow_id)
    if not wf:
        return []
    if isinstance(wf, dict):
        return wf.get("execution_trace", [])
    return getattr(wf, "execution_trace", [])


@router.post("/workflows/{workflow_id}/decision", tags=["Workflows (Agents)"], summary="Submit human engineering disposition (HITL Gate)", description="Authorized quality engineer confirms or rejects findings, records comments, and resumes workflow. Requires quality_engineer or admin role (operator receives HTTP 403, unauthenticated receives 401).")
def submit_workflow_decision(
    workflow_id: str,
    payload: HumanApprovalRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin"))
):
    return orchestrator.resume_workflow(workflow_id=workflow_id, payload=payload, current_user=current_user)


@router.post("/workflows/{workflow_id}/resume", tags=["Workflows (Agents)"], summary="Resume paused workflow checkpoint", description="Resumes paused workflow with authorized human decision, updating database state and completing execution trace.")
def resume_workflow_endpoint(
    workflow_id: str,
    payload: HumanApprovalRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin"))
):
    return orchestrator.resume_workflow(workflow_id=workflow_id, payload=payload, current_user=current_user)


@router.post("/workflows/{workflow_id}/re-analyze", tags=["Workflows (Agents)"], summary="Request another agent analysis with engineer feedback", description="Re-runs specified agent with engineering feedback. Enforces maximum 3 reassessment loop count.")
def request_reanalysis_endpoint(
    workflow_id: str,
    payload: ReanalyzeRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin"))
):
    return orchestrator.reanalyze_workflow(
        workflow_id=workflow_id,
        target_agent=payload.target_agent,
        comment=payload.comment,
        current_user=current_user
    )


@router.post("/workflows/{workflow_id}/comment", tags=["Workflows (Agents)"], summary="Add engineering comment to workflow audit", description="Records length-limited, escaped engineering comment in human_decisions and reviewer_comments tables.")
def add_workflow_comment_endpoint(
    workflow_id: str,
    payload: WorkflowCommentRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin"))
):
    return orchestrator.add_engineering_comment(
        workflow_id=workflow_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        comment=payload.comment,
        current_user=current_user
    )


@router.post("/review/sign-off", tags=["Workflows (Agents)"], summary="Submit authorized engineering disposition and root cause elevation", description="Human-in-the-Loop decision gate. Authenticated Quality Engineer assigns final batch disposition and elevates confirmed root cause. Requires quality_engineer or admin role (operator receives HTTP 403, unauthenticated receives 401).")
def submit_human_decision(
    payload: HumanApprovalRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin"))
):
    decision = (payload.decision or "ACCEPT_FINDINGS").upper().strip()
    is_rejection = decision in ["REJECT", "REJECT_BATCH", "QUARANTINE_BATCH"]

    if is_rejection and (not payload.engineering_comments or not payload.engineering_comments.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rejection requires a mandatory engineering justification/comment."
        )

    raw_comment = payload.engineering_comments or ""
    if len(raw_comment) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Engineering comments exceed maximum length limit of 2000 characters."
        )

    safe_comment = html.escape(raw_comment.strip()) if raw_comment else (
        f"Findings dispositioned as {decision} by {current_user.get('name', 'Quality Engineer')}."
    )

    db = SessionLocal()
    try:
        record = HumanDecision(
            workflow_id=f"WF-SIGN-OFF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entity_type="batch_disposition",
            entity_id="BATCH-0245",
            decision=decision,
            comment=safe_comment,
            user_id=current_user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        rec_id = record.id
        rec_ts = record.ts.isoformat()
    finally:
        db.close()

    return {
        "status": "DISPOSITION_RECORDED",
        "decision_id": rec_id,
        "approved_by": current_user.get("name", "Quality Engineer"),
        "role": current_user.get("role", "quality_engineer"),
        "decision": decision,
        "confirmed_root_cause": payload.confirmed_root_cause or "Progressive Tool Flank Wear (Confirmed via Optical Toolmakers Microscope)",
        "disposition": payload.disposition,
        "engineering_comments": safe_comment,
        "timestamp": rec_ts,
        "certainty": CertaintyLevel.CONFIRMED_ROOT_CAUSE.value
    }


@router.get("/human-decisions", tags=["Workflows (Agents)", "Governance"], summary="List audit trail of all human engineering decisions", description="Returns complete immutable audit trail of engineering approvals, rejections, comments, and dispositions from human_decisions table.")
def list_human_decisions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (batch_disposition, hypothesis, capa, finding)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    limit: int = Query(100, description="Maximum records to return")
):
    db = SessionLocal()
    try:
        q = db.query(HumanDecision)
        if workflow_id:
            q = q.filter(HumanDecision.workflow_id == workflow_id)
        if entity_type:
            q = q.filter(HumanDecision.entity_type == entity_type)
        if entity_id:
            q = q.filter(HumanDecision.entity_id == entity_id)

        records = q.order_by(HumanDecision.ts.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "workflow_id": r.workflow_id,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "decision": r.decision,
                "comment": r.comment,
                "user_id": r.user_id,
                "timestamp": r.ts.isoformat() if r.ts else None
            }
            for r in records
        ]
    finally:
        db.close()


@router.post("/safety/guardrails/test-autonomous-action", tags=["System", "Safety"], summary="Test safety guardrails intercepting prohibited autonomous actions", description="Verifies that autonomous product release, batch rejection, machine parameter adjustments, PLC changes, and machinery stoppage raise HTTP 403 safety violation exceptions and log attempts.")
def test_autonomous_action_guard(payload: SafetyActionTestRequest):
    act = payload.action.upper().strip()
    if act == "RELEASE_PRODUCT":
        safety_guardrail.assert_no_autonomous_batch_release(batch_id=payload.target_id)
    elif act == "REJECT_BATCH":
        safety_guardrail.assert_no_autonomous_batch_rejection(batch_id=payload.target_id)
    elif act == "MODIFY_CNC":
        safety_guardrail.assert_no_machine_parameter_modification(machine_id=payload.target_id, parameters=payload.parameters or {"feed_rate": 250.0})
    elif act == "MODIFY_PLC":
        safety_guardrail.assert_no_plc_configuration_change(machine_id=payload.target_id, plc_config=payload.parameters or {"holding_registers": [1, 2]})
    elif act == "STOP_MACHINERY":
        safety_guardrail.assert_no_autonomous_machinery_stop(machine_id=payload.target_id)
    elif act == "OVERRIDE_ENGINEER":
        safety_guardrail.assert_no_override_engineer_decision(entity_id=payload.target_id)
    elif act in ["EXECUTE_MACHINE_ACTION", "EXECUTE_CORRECTIVE_ACTION"]:
        action_name = (payload.parameters.get("action") if payload.parameters else None) or "tool_replacement_action"
        safety_guardrail.assert_no_corrective_machine_action(machine_id=payload.target_id, action_desc=action_name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown autonomous action '{payload.action}'. Supported: RELEASE_PRODUCT, REJECT_BATCH, MODIFY_CNC, MODIFY_PLC, STOP_MACHINERY, OVERRIDE_ENGINEER, EXECUTE_MACHINE_ACTION")
    return {"status": "UNEXPECTED_PASS", "message": "Guardrail failed to trip."}


@router.get("/orchestrator/agent-runs", tags=["Workflows (Agents)", "RAG"], summary="List Agent Execution Runs and Retrieved RAG Evidence", description="Returns audit history of agent runs from agent_runs table including query, filters, retrieved evidence, and similarity scores.")
def list_agent_runs(batch_id: Optional[str] = None):
    try:
        db = SessionLocal()
        try:
            q = db.query(AgentRun)
            if batch_id:
                q = q.filter(AgentRun.batch_id.contains(batch_id))
            runs = q.order_by(AgentRun.started_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "workflow_id": r.workflow_id,
                    "batch_id": r.batch_id,
                    "agent_name": r.agent_name,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "input": json.loads(r.input_json) if r.input_json else {},
                    "tool_calls": json.loads(r.tool_calls_json) if r.tool_calls_json else [],
                    "retrieved_evidence": json.loads(r.retrieved_evidence_json) if r.retrieved_evidence_json else [],
                    "status": r.status
                }
                for r in runs
            ]
        finally:
            db.close()
    except Exception:
        return []
