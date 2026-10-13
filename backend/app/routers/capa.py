"""
Corrective & Preventive Action (CAPA) API Endpoints (Agent 7)
Fully compliant with IATF 16949 Section 10.2:
- 3-tiered action management (Containment, Corrective, Preventive)
- Strict RBAC: Quality Engineer / Admin sign-off required
- Monotonically sequential non-reusable IDs (CAPA-YYYY-NNN)
- Deterministic state machine & field validations
- Safety guardrails blocking autonomous machine control
- Defect recurrence detection
"""
import os
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.database.models import CAPAAction, HumanDecision, QualityIncident, RCAHypothesis
from backend.app.services.capa_service import capa_service
from backend.app.core.security import require_authenticated_role, get_current_user_optional

router = APIRouter(prefix="", tags=["CAPA"])

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class CAPACreateRequest(BaseModel):
    incident_id: str = Field(..., description="ID of the associated quality incident (e.g. inc-ncr-019)")
    type: str = Field(..., description="Action tier: containment, corrective, preventive")
    description: str = Field(..., description="Human action task description")
    due_date: str = Field(..., description="Target completion date in YYYY-MM-DD format")
    hypothesis_id: Optional[str] = Field(None, description="Linked RCA hypothesis ID (e.g. hyp-conf-inc-ncr-019)")
    suggested_role: Optional[str] = Field(None, description="Suggested role prior to engineering sign-off")
    responsible_role: Optional[str] = Field(None, description="Assigned role upon engineering approval")

    model_config = {
        "json_schema_extra": {
            "example": {
                "incident_id": "inc-ncr-019",
                "type": "containment",
                "description": "Quarantine production batch BATCH-0245 in Quality Hold area.",
                "due_date": "2026-10-25",
                "hypothesis_id": "hyp-conf-inc-ncr-019",
                "suggested_role": "Quality Inspector"
            }
        }
    }

class CAPAApproveRequest(BaseModel):
    responsible_role: Optional[str] = Field(None, description="Role assigned to execute the approved action")
    comment: Optional[str] = Field(None, description="Quality engineer approval remarks")

    model_config = {
        "json_schema_extra": {
            "example": {
                "responsible_role": "Tooling Specialist",
                "comment": "Approved following physical inspection sign-off."
            }
        }
    }

class CAPARejectRequest(BaseModel):
    reason: str = Field(..., description="Mandatory rationale for rejecting the action proposal")

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "Redundant action; tool insert was already replaced on previous shift."
            }
        }
    }

class CAPAUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="Target status (approved, in_progress, completed, verified, rejected)")
    description: Optional[str] = Field(None, description="Updated action description")
    due_date: Optional[str] = Field(None, description="Updated target date (YYYY-MM-DD)")
    responsible_role: Optional[str] = Field(None, description="Assigned role")
    evidence: Optional[str] = Field(None, description="Evidence text or documentation sign-off")
    completion_date: Optional[str] = Field(None, description="Date completed (YYYY-MM-DD)")
    effectiveness_result: Optional[str] = Field(None, description="Post-intervention verification outcome")
    comment: Optional[str] = Field(None, description="Audit log note")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@router.get(
    "/capa/actions",
    summary="List and filter CAPA actions",
    description="Retrieves CAPA actions with optional filtering by type, status, due date, incident, and overdue state."
)
def list_capa_actions(
    type: Optional[str] = Query(None, description="Filter by tier: containment, corrective, preventive"),
    status: Optional[str] = Query(None, description="Filter by status: proposed, approved, in_progress, completed, verified, rejected"),
    due_date: Optional[str] = Query(None, description="Filter by due date (YYYY-MM-DD)"),
    incident_id: Optional[str] = Query(None, description="Filter by incident ID"),
    is_overdue: Optional[bool] = Query(None, description="Filter by overdue status"),
    db: Session = Depends(get_db)
):
    actions = capa_service.list_actions(
        db=db,
        action_type=type,
        status=status,
        due_date=due_date,
        incident_id=incident_id,
        is_overdue=is_overdue
    )
    return {
        "total": len(actions),
        "actions": actions
    }


@router.get(
    "/capa/actions/{action_id_or_code}",
    summary="Get single CAPA action by ID or Code",
    description="Fetches complete details for a specific action, including links to incident, RCA hypothesis, and approval state."
)
def get_capa_action(
    action_id_or_code: str,
    db: Session = Depends(get_db)
):
    act = capa_service.get_action(db, action_id_or_code)
    return capa_service.serialize_action(act)


@router.post(
    "/capa/actions",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new CAPA action",
    description="Creates a new action in 'proposed' status with an auto-generated sequential ID (CAPA-YYYY-NNN). Requires Quality Engineer or Admin role."
)
def create_capa_action(
    payload: CAPACreateRequest,
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    act = capa_service.create_action(
        db=db,
        incident_id=payload.incident_id,
        action_type=payload.type,
        description=payload.description,
        due_date=payload.due_date,
        user=user,
        hypothesis_id=payload.hypothesis_id,
        suggested_role=payload.suggested_role,
        responsible_role=payload.responsible_role
    )
    return capa_service.serialize_action(act)


@router.post(
    "/capa/actions/{action_id_or_code}/approve",
    summary="Approve a proposed CAPA action",
    description="Transitions an action from 'proposed' to 'approved', assigns responsible role, and records approver timestamp. Requires Quality Engineer or Admin role."
)
def approve_capa_action(
    action_id_or_code: str,
    payload: Optional[CAPAApproveRequest] = Body(None),
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    responsible_role = payload.responsible_role if payload else None
    comment = payload.comment if payload else None
    act = capa_service.approve_action(
        db=db,
        action_id_or_code=action_id_or_code,
        user=user,
        responsible_role=responsible_role,
        comment=comment
    )
    return {
        "message": f"Action {act.action_code} successfully approved.",
        "action": capa_service.serialize_action(act)
    }


@router.post(
    "/capa/actions/{action_id_or_code}/reject",
    summary="Reject a proposed CAPA action",
    description="Transitions an action from 'proposed' to 'rejected' with mandatory rejection rationale. Requires Quality Engineer or Admin role."
)
def reject_capa_action(
    action_id_or_code: str,
    payload: CAPARejectRequest,
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    act = capa_service.reject_action(
        db=db,
        action_id_or_code=action_id_or_code,
        user=user,
        reason=payload.reason
    )
    return {
        "message": f"Action {act.action_code} rejected.",
        "action": capa_service.serialize_action(act)
    }


@router.patch(
    "/capa/actions/{action_id_or_code}",
    summary="Update CAPA action or status",
    description="Updates status, due date, description, or evidence with state machine transition checks. Requires Quality Engineer or Admin role."
)
def update_capa_action(
    action_id_or_code: str,
    payload: CAPAUpdateRequest,
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    act = capa_service.update_action_status(
        db=db,
        action_id_or_code=action_id_or_code,
        new_status=payload.status or "no_change",
        user=user,
        evidence=payload.evidence,
        completion_date=payload.completion_date,
        responsible_role=payload.responsible_role,
        due_date=payload.due_date,
        description=payload.description,
        comment=payload.comment
    )
    return {
        "message": f"Action {act.action_code} updated.",
        "action": capa_service.serialize_action(act)
    }


@router.delete(
    "/capa/actions/{action_id_or_code}",
    summary="Delete a CAPA action",
    description="Deletes an action while preserving the monotonic sequence counter so action codes are never reused. Requires Quality Engineer or Admin role."
)
def delete_capa_action(
    action_id_or_code: str,
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    return capa_service.delete_action(db, action_id_or_code, user)


@router.post(
    "/capa/actions/{action_id_or_code}/evidence",
    summary="Upload completion evidence file",
    description="Uploads an inspection report, photo, or calibration certificate (.pdf, .png, .jpg, .xlsx, .csv, .txt; max 10MB) attached to the CAPA action."
)
def upload_capa_evidence(
    action_id_or_code: str,
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    action = capa_service.get_action(db, action_id_or_code)

    # Validate file extension
    filename = file.filename or "evidence.dat"
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".csv", ".txt", ".docx"]
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Disallowed evidence file type '{ext}'. Allowed types: {allowed_extensions}."
        )

    # Validate file size (max 10MB)
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "evidence"))
    os.makedirs(upload_dir, exist_ok=True)

    safe_filename = f"{action.action_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename.replace(' ', '_')}"
    target_path = os.path.join(upload_dir, safe_filename)

    file_size = 0
    with open(target_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 64):
            file_size += len(chunk)
            if file_size > 10 * 1024 * 1024:
                os.remove(target_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Evidence file exceeds 10MB maximum size limit."
                )
            buffer.write(chunk)

    rel_path = f"/uploads/evidence/{safe_filename}"
    action.evidence_file_path = rel_path
    if not action.evidence:
        action.evidence = f"Evidence file uploaded: {filename}"
    else:
        action.evidence += f" | File: {filename}"

    # Audit log
    audit_log = HumanDecision(
        workflow_id=f"wf-capa-{action.action_code}",
        entity_type="capa",
        entity_id=action.action_code,
        decision="evidence_uploaded",
        comment=f"Uploaded evidence file: {filename} ({file_size} bytes)",
        user_id=user.get("id", "usr-qe-01"),
        ts=datetime.now(timezone.utc)
    )
    db.add(audit_log)
    db.commit()
    db.refresh(action)

    return {
        "message": "Evidence file uploaded successfully.",
        "file_path": rel_path,
        "action": capa_service.serialize_action(action)
    }


@router.get(
    "/capa/actions/{action_id_or_code}/audit",
    summary="Get audit trail history for an action",
    description="Returns human decisions, approvals, and status modification audit logs for the specified action."
)
def get_capa_audit_trail(
    action_id_or_code: str,
    db: Session = Depends(get_db)
):
    action = capa_service.get_action(db, action_id_or_code)
    logs = db.query(HumanDecision).filter(
        HumanDecision.entity_type == "capa",
        HumanDecision.entity_id == action.action_code
    ).order_by(HumanDecision.ts.asc()).all()

    return {
        "action_code": action.action_code,
        "audit_logs": [
            {
                "id": l.id,
                "decision": l.decision,
                "comment": l.comment,
                "user_id": l.user_id,
                "timestamp": l.ts.isoformat() if l.ts else None
            }
            for l in logs
        ]
    }


@router.get(
    "/capa/actions/{action_id_or_code}/effectiveness",
    tags=["Effectiveness", "CAPA"],
    summary="Get CAPA action effectiveness monitoring results",
    description="Statistical before-and-after effectiveness monitoring results including window partitioning, rates, two-proportion z-test / Fisher's exact test, and recurrence detection."
)
def get_action_effectiveness(
    action_id_or_code: str,
    db: Session = Depends(get_db)
):
    from backend.app.services.effectiveness import effectiveness_engine
    return effectiveness_engine.evaluate_capa_effectiveness(capa_id=action_id_or_code, db=db)


@router.get(
    "/capa/recurrence-check",
    summary="Defect Recurrence Detector",
    description="Analyzes whether the same defect type on the specified machine returned after completed CAPA actions."
)
def check_defect_recurrence(
    machine: str = Query("CNC-04", description="Machine code or ID to check"),
    defect_type: str = Query("Oversized shaft diameter", description="Defect type to investigate"),
    db: Session = Depends(get_db)
):
    return capa_service.detect_defect_recurrence(db=db, machine_code=machine, defect_type=defect_type)


@router.post(
    "/capa/generate-proposals/{batch_id}",
    summary="Agent 7: Generate CAPA proposals for batch",
    description="Generates containment, corrective, and preventive proposals for quality engineering sign-off."
)
def generate_proposals_for_batch(
    batch_id: str,
    db: Session = Depends(get_db)
):
    from backend.app.agents.capa_agent import capa_agent
    res = capa_agent.generate_capa_plan(incident_id=f"INC-{batch_id}", batch_id=batch_id, machine="CNC-04", db=db)
    capa = res.get("capa")
    if hasattr(capa, "containment_actions"):
        containment = [a.model_dump() for a in capa.containment_actions]
        corrective = [a.model_dump() for a in capa.corrective_actions]
        preventive = [a.model_dump() for a in capa.preventive_actions]
        all_actions = containment + corrective + preventive
    else:
        all_actions = []
        containment = []
        corrective = []
        preventive = []

    return {
        "batch_id": batch_id,
        "proposals_count": len(all_actions),
        "actions": all_actions,
        "containment_actions": containment,
        "corrective_actions": corrective,
        "preventive_actions": preventive
    }


@router.get(
    "/capa/stats",
    summary="Get aggregated CAPA counts",
    description="Returns total, open, overdue, and completed action counts calculated directly from the database."
)
def get_capa_statistics(db: Session = Depends(get_db)):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = db.query(CAPAAction).count()
    open_count = db.query(CAPAAction).filter(CAPAAction.status.in_(["proposed", "approved", "in_progress"])).count()
    overdue_count = db.query(CAPAAction).filter(
        CAPAAction.due_date < today_str,
        CAPAAction.status.in_(["proposed", "approved", "in_progress"])
    ).count()
    completed_count = db.query(CAPAAction).filter(CAPAAction.status.in_(["completed", "verified"])).count()

    return {
        "total_actions": total,
        "open_actions": open_count,
        "overdue_actions": overdue_count,
        "completed_actions": completed_count,
        "as_of_date": today_str
    }


@router.get(
    "/capa/plan",
    summary="Generate 3-tiered CAPA action plan",
    description="Returns the 3-tiered CAPA structure (Immediate Containment, Corrective Action, Preventive Action) for quality engineering sign-off."
)
def get_capa_plan(
    incident_id: str = "INC-2026-088",
    batch_id: str = "BATCH-0245",
    db: Session = Depends(get_db)
):
    from backend.app.agents.capa_agent import capa_agent
    res = capa_agent.generate_capa_plan(incident_id=incident_id, batch_id=batch_id, machine="CNC-04")
    return {"capa": res["capa"], "log": res["log"]}
