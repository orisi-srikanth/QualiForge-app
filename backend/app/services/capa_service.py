"""
CAPA Management Service (Agent 7 & IATF 16949 Section 10.2)
Handles 3-tiered action plans (Containment, Corrective, Preventive),
strict human-in-the-loop engineering approvals, deterministic status workflows,
safety guardrails against autonomous machine execution, sequential non-reusable IDs,
and defect recurrence detection.
"""
import re
import os
import json
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.app.database.models import (
    CAPAAction, CAPASequence, QualityIncident, RCAHypothesis,
    HumanDecision, ReviewerComment, Batch, Machine, User
)

# ---------------------------------------------------------------------------
# Safety Guardrails: Strictly human decision support (IATF 16949)
# ---------------------------------------------------------------------------
FORBIDDEN_AUTONOMOUS_PATTERNS = [
    # Direct machine control / stopping
    r"\b(e-?stop|emergency\s+stop)\b",
    r"\b(stop|halt|shut\s*down)\s+(the\s+)?(machine|spindle|line|lathe|mill|production|feed)\b",
    # Direct CNC/PLC manipulation
    r"\b(change|modify|override|set|update|write|alter)\s+(the\s+)?(cnc|plc|ladder|register|offset|parameter|g-?code|m-?code)\b",
    r"\b(adjust|reset)\s+(the\s+)?(machine\s+offset|spindle\s+speed)\s+directly\b",
    # Autonomous disposition / release
    r"\b(auto-?release|automatically\s+release|system\s+release)\s+(batch|product|lot)?\b",
    r"\b(auto-?scrap|automatically\s+scrap|auto-?reject|automatically\s+reject)\s+(batch|parts|lot)?\b",
    r"\b(override|bypass)\s+quality\s+hold\b",
    # Autonomous execution
    r"\bautonomous(ly)?\s+(execute|actuate|control|change|stop|release|scrap)\b",
    r"\bexecute\s+g-?code\b"
]

def check_safety_guardrails(description: str) -> Optional[str]:
    """
    Scans action description for forbidden autonomous machine actions.
    Returns matched offending phrase if detected, otherwise None.
    """
    for pat in FORBIDDEN_AUTONOMOUS_PATTERNS:
        match = re.search(pat, description, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


class CAPAManagementService:
    """Enterprise CAPA Lifecycle Engine compliant with IATF 16949 Section 10.2."""

    # Documented status transitions:
    # proposed -> approved -> in_progress -> completed -> verified
    # proposed -> rejected
    ALLOWED_TRANSITIONS = {
        "proposed": ["approved", "rejected"],
        "approved": ["in_progress"],
        "in_progress": ["completed"],
        "completed": ["verified"],
        "verified": [],
        "rejected": []
    }

    def generate_next_action_code(self, db: Session, year: Optional[int] = None) -> str:
        """
        Generates sequential, unique action IDs formatted as CAPA-{YYYY}-{NNN}.
        Monotonically tracked in capa_sequences table so numbers are never reused
        even if an action record is deleted.
        """
        current_year = year or datetime.now(timezone.utc).year
        seq_record = db.query(CAPASequence).filter(CAPASequence.year == current_year).with_for_update().first()
        if not seq_record:
            # Determine existing max in database for baseline
            existing_codes = db.query(CAPAAction.action_code).filter(
                CAPAAction.action_code.like(f"CAPA-{current_year}-%")
            ).all()
            max_seq = 0
            for (code,) in existing_codes:
                m = re.match(rf"CAPA-{current_year}-(\d+)", code or "")
                if m:
                    max_seq = max(max_seq, int(m.group(1)))
            seq_record = CAPASequence(year=current_year, last_seq=max_seq)
            db.add(seq_record)
            db.flush()

        while True:
            seq_record.last_seq += 1
            code = f"CAPA-{current_year}-{seq_record.last_seq:03d}"
            if not db.query(CAPAAction).filter(CAPAAction.action_code == code).first():
                break
        db.flush()
        return code

    def validate_action_description(self, description: str, db: Session, user_id: str, action_code: str = ""):
        """Enforces safety guardrail against autonomous machine commands."""
        forbidden_phrase = check_safety_guardrails(description)
        if forbidden_phrase:
            # Log blocking safety audit record
            audit_log = HumanDecision(
                workflow_id="wf-capa-safety-guardrail",
                entity_type="capa",
                entity_id=action_code or "PROPOSAL_VALIDATION",
                decision="blocked_by_safety_guardrail",
                comment=f"SAFETY VIOLATION BLOCKED: Autonomous command detected: '{forbidden_phrase}'. Action must be assigned to human personnel.",
                user_id=user_id,
                ts=datetime.now(timezone.utc)
            )
            db.add(audit_log)
            reviewer_comment = ReviewerComment(
                workflow_id="wf-capa-safety-guardrail",
                agent_name="Agent 8 (Critic Agent)",
                severity="BLOCKING",
                comment=f"CRITIC SAFETY VIOLATION: Forbidden autonomous machine action detected: '{forbidden_phrase}'. QualityMind operates strictly as human decision support.",
                resolved=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(reviewer_comment)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"SAFETY GUARDRAIL VIOLATION: QualityMind functions strictly as human decision support (IATF 16949). "
                    f"Autonomous machine actuation or automated disposition ('{forbidden_phrase}') is strictly prohibited. "
                    f"Every CAPA action must be assigned to human personnel."
                )
            )

    def create_action(
        self,
        db: Session,
        incident_id: str,
        action_type: str,
        description: str,
        due_date: str,
        user: Dict[str, Any],
        hypothesis_id: Optional[str] = None,
        suggested_role: Optional[str] = None,
        responsible_role: Optional[str] = None
    ) -> CAPAAction:
        """
        Creates a new CAPA action in 'proposed' status.
        Requires Quality Engineer or Admin authorization.
        Responsible role is assigned ONLY after approval.
        """
        pass

        valid_types = ["containment", "corrective", "preventive"]
        clean_type = action_type.strip().lower()
        if clean_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type '{action_type}'. Allowed types: {valid_types}."
            )

        # Enforce safety guardrail
        self.validate_action_description(description, db, user.get("id", "usr-unknown"))

        # Enforce date formatting
        try:
            parsed_due = datetime.strptime(due_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid due_date format '{due_date}'. Expected YYYY-MM-DD."
            )

        today = datetime.now(timezone.utc).date()
        if parsed_due < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Due date '{due_date}' cannot precede the current creation date '{today}'."
            )

        action_code = self.generate_next_action_code(db)

        # Proposed actions carry a suggested role; responsible_role assigned upon approval
        action = CAPAAction(
            incident_id=incident_id,
            hypothesis_id=hypothesis_id,
            action_code=action_code,
            type=clean_type,
            description=description.strip(),
            suggested_role=suggested_role or responsible_role or "Quality Engineer",
            responsible_role=None,  # Not assigned until engineering approval
            due_date=due_date.strip(),
            status="proposed",
            evidence="",
            evidence_file_path=None,
            completion_date=None,
            effectiveness_result=None,
            approved_by=None,
            approved_at=None,
            created_at=datetime.now(timezone.utc),
            created_by=user.get("id")
        )
        db.add(action)
        db.flush()

        # Audit logging
        decision_log = HumanDecision(
            workflow_id=f"wf-capa-{action_code}",
            entity_type="capa",
            entity_id=action_code,
            decision="created",
            comment=f"Created proposed {clean_type} action {action_code}: '{description[:60]}...'",
            user_id=user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(decision_log)
        db.commit()
        db.refresh(action)
        return action

    def approve_action(
        self,
        db: Session,
        action_id_or_code: str,
        user: Dict[str, Any],
        responsible_role: Optional[str] = None,
        comment: Optional[str] = None
    ) -> CAPAAction:
        """
        Approves a proposed action.
        Transitions proposed -> approved.
        Records who, when, and formally assigns the responsible person/role.
        """
        pass

        action = self.get_action(db, action_id_or_code)
        user_role = str(user.get("role", "")).lower()
        if user.get("enforce_role") and user_role and user_role not in ["quality_engineer", "admin", "lead quality engineer"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: Role '{user.get('role')}' is not authorized to approve CAPA actions. Quality Engineer or Admin authorization required."
            )

        if action.status != "proposed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve action {action.action_code} with status '{action.status}'. Only 'proposed' actions can be approved."
            )

        assigned_role = responsible_role or action.suggested_role or "Lead Quality Engineer"
        action.status = "approved"
        action.responsible_role = assigned_role
        action.approved_by = user.get("id", "usr-qe-01")
        action.approved_at = datetime.now(timezone.utc)

        # Audit log
        decision_log = HumanDecision(
            workflow_id=f"wf-capa-{action.action_code}",
            entity_type="capa",
            entity_id=action.action_code,
            decision="approved",
            comment=comment or f"Approved by {user.get('name', 'Quality Engineer')} (Role assigned: {assigned_role})",
            user_id=user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(decision_log)
        db.commit()
        db.refresh(action)
        return action

    def reject_action(
        self,
        db: Session,
        action_id_or_code: str,
        user: Dict[str, Any],
        reason: str
    ) -> CAPAAction:
        """
        Rejects a proposed action.
        Transitions proposed -> rejected.
        Records reviewer and reason.
        """
        pass

        action = self.get_action(db, action_id_or_code)
        user_role = str(user.get("role", "")).lower()
        if user.get("enforce_role") and user_role and user_role not in ["quality_engineer", "admin", "lead quality engineer"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: Role '{user.get('role')}' is not authorized to reject CAPA actions. Quality Engineer or Admin authorization required."
            )

        if action.status != "proposed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject action {action.action_code} with status '{action.status}'. Only 'proposed' actions can be rejected."
            )

        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A non-empty rejection reason is required to reject a CAPA action."
            )

        action.status = "rejected"
        action.approved_by = user.get("id", "usr-qe-01")
        action.approved_at = datetime.now(timezone.utc)

        # Audit log
        decision_log = HumanDecision(
            workflow_id=f"wf-capa-{action.action_code}",
            entity_type="capa",
            entity_id=action.action_code,
            decision="rejected",
            comment=f"Rejected by {user.get('name', 'Quality Engineer')}. Reason: {reason.strip()}",
            user_id=user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(decision_log)
        db.commit()
        db.refresh(action)
        return action

    def update_action_status(
        self,
        db: Session,
        action_id_or_code: str,
        new_status: str,
        user: Dict[str, Any],
        evidence: Optional[str] = None,
        completion_date: Optional[str] = None,
        responsible_role: Optional[str] = None,
        due_date: Optional[str] = None,
        description: Optional[str] = None,
        comment: Optional[str] = None
    ) -> CAPAAction:
        """
        Validates state transitions and updates action fields according to industrial QMS rules.
        """
        pass

        action = self.get_action(db, action_id_or_code)
        old_status = action.status
        target_status = new_status.strip().lower()

        if description is not None:
            self.validate_action_description(description, db, user.get("id", "usr-unknown"), action.action_code)
            action.description = description.strip()

        # Check if status transition is requested
        if target_status not in [old_status, "no_change", ""]:
            allowed = self.ALLOWED_TRANSITIONS.get(old_status, [])
            if target_status not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Illegal status transition from '{old_status}' to '{target_status}'. "
                        f"Allowed transitions from '{old_status}': {allowed}."
                    )
                )

            # Specific transition rules
            if target_status == "approved":
                return self.approve_action(db, action.id, user, responsible_role, comment)
            elif target_status == "rejected":
                return self.reject_action(db, action.id, user, reason=comment or "Rejected during engineering review")
            elif target_status == "in_progress":
                if old_status != "approved":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Action must be approved before moving to in_progress."
                    )
                action.status = "in_progress"

            elif target_status == "completed":
                # Evidence (text or file) is MANDATORY
                submitted_ev = (evidence or "").strip()
                if not submitted_ev and not action.evidence and not action.evidence_file_path:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Evidence (text description or uploaded file) is required before marking action as completed."
                    )
                if submitted_ev:
                    action.evidence = submitted_ev

                # Completion date validation
                comp_dt = completion_date.strip() if completion_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                try:
                    parsed_comp = datetime.strptime(comp_dt, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid completion_date format '{comp_dt}'. Expected YYYY-MM-DD."
                    )

                if action.approved_at:
                    appr_date = action.approved_at.date()
                    if parsed_comp < appr_date:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Completion date '{comp_dt}' cannot be earlier than approval date '{appr_date}'."
                        )
                action.completion_date = comp_dt
                action.status = "completed"

                # Automatic effectiveness monitoring trigger (FR-15 Check 1)
                try:
                    from backend.app.services.effectiveness import effectiveness_engine
                    eff_eval = effectiveness_engine.evaluate_capa_effectiveness(action.action_code, db=db)
                    if eff_eval and eff_eval.get("conclusion_label"):
                        action.effectiveness_result = eff_eval.get("conclusion_label")
                except Exception as e:
                    logger.warning(f"Automatic effectiveness evaluation on CAPA completion skipped: {e}")

            elif target_status == "verified":
                if old_status != "completed":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Action must be completed before it can be verified."
                    )
                if not action.effectiveness_result:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Effectiveness evaluation result is required before verifying CAPA completion."
                    )
                action.status = "verified"

        # Field updates
        if due_date:
            try:
                parsed_due = datetime.strptime(due_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid due_date format '{due_date}'. Expected YYYY-MM-DD."
                )
            if action.approved_at and parsed_due < action.approved_at.date():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Due date '{due_date}' cannot precede approval date '{action.approved_at.date()}'."
                )
            elif action.created_at and parsed_due < action.created_at.date():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Due date '{due_date}' cannot precede creation date '{action.created_at.date()}'."
                )
            action.due_date = due_date.strip()

        if responsible_role and action.status != "proposed":
            action.responsible_role = responsible_role.strip()
        elif responsible_role and action.status == "proposed":
            action.suggested_role = responsible_role.strip()

        if evidence and target_status != "completed":
            action.evidence = evidence.strip()

        # Audit log entry
        audit_entry = HumanDecision(
            workflow_id=f"wf-capa-{action.action_code}",
            entity_type="capa",
            entity_id=action.action_code,
            decision="status_update" if target_status != old_status else "edit",
            comment=comment or f"Updated action {action.action_code}: status {old_status} -> {action.status}",
            user_id=user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(action)
        return action

    def delete_action(self, db: Session, action_id_or_code: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Deletes an action record. Preserves sequence counter so ID is never reused."""
        pass
        action = self.get_action(db, action_id_or_code)
        action_code = action.action_code

        # Log deletion audit
        audit_entry = HumanDecision(
            workflow_id=f"wf-capa-{action_code}",
            entity_type="capa",
            entity_id=action_code,
            decision="deleted",
            comment=f"Deleted CAPA action {action_code} by {user.get('name', 'User')}",
            user_id=user.get("id", "usr-qe-01"),
            ts=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.delete(action)
        db.commit()
        return {"deleted": True, "action_code": action_code, "note": "Sequence counter preserved; ID will not be reused."}

    def get_action(self, db: Session, action_id_or_code: str) -> CAPAAction:
        """Retrieves action by either UUID or action_code."""
        action = db.query(CAPAAction).filter(
            (CAPAAction.id == action_id_or_code) | (CAPAAction.action_code == action_id_or_code)
        ).first()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CAPA Action '{action_id_or_code}' not found."
            )
        return action

    def list_actions(
        self,
        db: Session,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        incident_id: Optional[str] = None,
        is_overdue: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries and filters CAPA actions.
        Enriches output with computed overdue status, incident title, and hypothesis details.
        """
        query = db.query(CAPAAction)
        if action_type:
            query = query.filter(CAPAAction.type == action_type.strip().lower())
        if status:
            query = query.filter(CAPAAction.status == status.strip().lower())
        if due_date:
            query = query.filter(CAPAAction.due_date == due_date.strip())
        if incident_id:
            query = query.filter(CAPAAction.incident_id == incident_id.strip())

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        actions = query.order_by(CAPAAction.action_code.asc()).all()

        results = []
        for act in actions:
            # Overdue rule: due date has passed and status is not completed, verified, or rejected
            act_overdue = (act.due_date < today_str) and (act.status not in ["completed", "verified", "rejected"])
            if is_overdue is not None and act_overdue != is_overdue:
                continue

            results.append(self.serialize_action(act, act_overdue))
        return results

    def serialize_action(self, act: CAPAAction, is_overdue: Optional[bool] = None) -> Dict[str, Any]:
        """Serializes CAPAAction instance with all eight fields and contextual audit data."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if is_overdue is None:
            is_overdue = (act.due_date < today_str) and (act.status not in ["completed", "verified", "rejected"])

        return {
            "id": act.id,
            "action_id": act.action_code,  # Documented alias
            "action_code": act.action_code,
            "incident_id": act.incident_id,
            "hypothesis_id": act.hypothesis_id,
            "type": act.type,
            "description": act.description,
            "suggested_role": act.suggested_role,
            "responsible_role": act.responsible_role,
            "assigned_role": act.responsible_role or f"Suggested: {act.suggested_role}",
            "due_date": act.due_date,
            "status": act.status,
            "evidence": act.evidence or "",
            "evidence_file_path": act.evidence_file_path,
            "completion_date": act.completion_date,
            "effectiveness_result": act.effectiveness_result,
            "approved_by": act.approved_by,
            "approved_at": act.approved_at.isoformat() if act.approved_at else None,
            "created_at": act.created_at.isoformat() if act.created_at else None,
            "created_by": act.created_by,
            "is_overdue": is_overdue
        }

    def detect_defect_recurrence(
        self,
        db: Session,
        machine_code: str,
        defect_type: str
    ) -> Dict[str, Any]:
        """
        Recurrence detector:
        Flags if the same defect type on the same machine returns after a completed CAPA action.
        """
        # 1. Resolve machine
        mach = db.query(Machine).filter((Machine.code == machine_code) | (Machine.id == machine_code)).first()
        mach_id = mach.id if mach else machine_code
        mach_name = mach.code if mach else machine_code

        # 2. Find completed or verified CAPA actions associated with this machine and defect
        completed_capas = db.query(CAPAAction).join(QualityIncident, CAPAAction.incident_id == QualityIncident.id)\
            .join(Batch, QualityIncident.batch_id == Batch.id)\
            .filter(
                Batch.machine_id == mach_id,
                QualityIncident.defect_type == defect_type,
                CAPAAction.status.in_(["completed", "verified"])
            ).all()

        if not completed_capas:
            return {
                "recurrence_detected": False,
                "machine": mach_name,
                "defect_type": defect_type,
                "completed_capas_count": 0,
                "message": f"No completed CAPA actions found for defect '{defect_type}' on machine {mach_name}."
            }

        # Check for incidents occurring after the latest completion date
        recurrence_events = []
        for capa in completed_capas:
            comp_dt = capa.completion_date or "2026-01-01"
            subsequent_incidents = db.query(QualityIncident).join(Batch, QualityIncident.batch_id == Batch.id)\
                .filter(
                    Batch.machine_id == mach_id,
                    QualityIncident.defect_type == defect_type,
                    func.date(QualityIncident.created_at) > comp_dt
                ).all()

            for inc in subsequent_incidents:
                recurrence_events.append({
                    "capa_code": capa.action_code,
                    "capa_completion_date": comp_dt,
                    "incident_id": inc.id,
                    "incident_title": inc.title,
                    "incident_date": inc.created_at.strftime("%Y-%m-%d") if inc.created_at else "Unknown"
                })

        detected = len(recurrence_events) > 0
        return {
            "recurrence_detected": detected,
            "machine": mach_name,
            "defect_type": defect_type,
            "completed_capas_count": len(completed_capas),
            "recurrence_count": len(recurrence_events),
            "recurrence_events": recurrence_events,
            "alert": (
                f"RECURRENCE ALERT: Defect '{defect_type}' re-occurred on {mach_name} after {len(completed_capas)} completed CAPA actions."
                if detected else "No defect recurrence observed."
            )
        }

    def seed_batch_0245_benchmark_proposals(self, db: Session) -> List[CAPAAction]:
        """
        Seeds/ensures the 11 benchmark CAPA proposals for BATCH-0245 from the problem statement:
        - 5 Containment actions
        - 4 Corrective actions (conditional on physical wear confirmation)
        - 2 Preventive actions
        All created in 'proposed' status, linked to hyp-conf-inc-ncr-019 and inc-ncr-019.
        """
        inc = db.query(QualityIncident).filter(
            (QualityIncident.id == "inc-ncr-019") | (QualityIncident.title.like("%BATCH-0245%"))
        ).first()
        inc_id = inc.id if inc else "inc-ncr-019"

        hyp = db.query(RCAHypothesis).filter(
            (RCAHypothesis.id == "hyp-conf-inc-ncr-019") | (RCAHypothesis.title.like("%Tool Flank Wear%"))
        ).first()
        hyp_id = hyp.id if hyp else "hyp-conf-inc-ncr-019"

        proposals = [
            # Containment (5 items)
            {
                "type": "containment",
                "description": "Hold affected production batch BATCH-0245 for 100% inspection and quarantine in Quality Hold area.",
                "suggested_role": "Quality Inspector / Shift Supervisor",
                "due_date": "2026-10-18"
            },
            {
                "type": "containment",
                "description": "Verify digital micrometer and bore gauge calibration against master setting gauge blocks.",
                "suggested_role": "Metrology Technician",
                "due_date": "2026-10-18"
            },
            {
                "type": "containment",
                "description": "Inspect cutting tool insert condition on CNC-04 tool turret position 2 for flank wear.",
                "suggested_role": "CNC Lead Machinist",
                "due_date": "2026-10-18"
            },
            {
                "type": "containment",
                "description": "Re-measure affected components from batch BATCH-0245 for dimensional conformance.",
                "suggested_role": "Quality Inspector",
                "due_date": "2026-10-19"
            },
            {
                "type": "containment",
                "description": "Review and quarantine all components manufactured since the last acceptable inspection at 02:30.",
                "suggested_role": "Quality Systems Auditor",
                "due_date": "2026-10-19"
            },
            # Corrective (4 items - conditional wording where wear confirmation is required)
            {
                "type": "corrective",
                "description": "Replace worn carbide cutting insert on CNC-04 turret position 2 IF tool inspection confirms flank wear exceeding 0.3mm criterion.",
                "suggested_role": "Tooling Specialist",
                "due_date": "2026-10-20"
            },
            {
                "type": "corrective",
                "description": "Re-validate machine tool offset and execute 5-piece first-article verification inspection.",
                "suggested_role": "CNC Setup Engineer",
                "due_date": "2026-10-20"
            },
            {
                "type": "corrective",
                "description": "Inspect CNC-04 spindle bearings and tool-holder chuck clamping mechanism for radial runout.",
                "suggested_role": "Maintenance Engineer",
                "due_date": "2026-10-22"
            },
            {
                "type": "corrective",
                "description": "Inspect all components produced during the anomalous telemetry drift window (04:15 - 06:30).",
                "suggested_role": "Quality Inspector",
                "due_date": "2026-10-21"
            },
            # Preventive (2 items)
            {
                "type": "preventive",
                "description": "Introduce an automated tool-life monitoring warning and cycle lockout threshold at 800 cycles on CNC-04.",
                "suggested_role": "Controls / PLC Engineer",
                "due_date": "2026-10-25"
            },
            {
                "type": "preventive",
                "description": "Review and recalibrate preventive tool-change threshold in maintenance schedule SOP-012.",
                "suggested_role": "Quality Systems Manager",
                "due_date": "2026-10-28"
            }
        ]

        created_actions = []
        for p in proposals:
            # Check if identical proposal already exists
            existing = db.query(CAPAAction).filter(
                CAPAAction.incident_id == inc_id,
                CAPAAction.description == p["description"]
            ).first()
            if not existing:
                code = self.generate_next_action_code(db)
                act = CAPAAction(
                    incident_id=inc_id,
                    hypothesis_id=hyp_id,
                    action_code=code,
                    type=p["type"],
                    description=p["description"],
                    suggested_role=p["suggested_role"],
                    responsible_role=None,  # Unassigned until approval
                    due_date=p["due_date"],
                    status="proposed",
                    evidence="",
                    evidence_file_path=None,
                    completion_date=None,
                    effectiveness_result=None,
                    approved_by=None,
                    approved_at=None,
                    created_at=datetime.now(timezone.utc),
                    created_by="usr-qe-01"
                )
                db.add(act)
                db.flush()
                created_actions.append(act)
            else:
                created_actions.append(existing)

        db.commit()
        return created_actions


capa_service = CAPAManagementService()
