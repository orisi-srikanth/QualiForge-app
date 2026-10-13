"""
Safety Guardrails Service for QualityMind Industrial Decision Support System
Enforces ISO 9001, IATF 16949, and PDF Problem Statement Safety Policy:
"The system must not autonomously release safety-critical products, reject entire batches
without authorization, modify CNC or machine parameters, stop production machinery,
change PLC configurations, execute corrective machine actions, or override quality-engineer decisions.
Observed fact, model prediction, statistical finding, hypothesis and confirmed root cause must be clearly distinguished."
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from backend.app.database.session import SessionLocal
from backend.app.database.models import HumanDecision

logger = logging.getLogger("safety_guardrails")

class AutonomousActionForbiddenError(HTTPException):
    """Raised whenever an autonomous agent or non-human code path attempts an unauthorized physical machine or batch disposition action."""
    def __init__(self, detail: str, violation_code: str = "SAFETY_GATE_VIOLATION"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "AutonomousActionForbidden",
                "violation_code": violation_code,
                "message": detail,
                "policy": "Decision-support only. Final product disposition and physical machinery controls are strictly human-controlled."
            }
        )

class SafetyGuardrailService:
    """Zero-trust guardrail interceptor for autonomous actions."""

    @staticmethod
    def _log_guardrail_trip(action_type: str, target: str, reason: str, user_id: str = "SYSTEM_AGENT"):
        try:
            db = SessionLocal()
            record = HumanDecision(
                workflow_id=f"GUARDRAIL-TRIP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                entity_type="safety_guardrail",
                entity_id=target,
                decision="GUARDRAIL_BLOCKED",
                comment=f"[SAFETY GUARD TRIPPED] Blocked autonomous {action_type} on {target}. Rationale: {reason}",
                user_id=user_id,
                ts=datetime.now(timezone.utc)
            )
            db.add(record)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to log guardrail trip to DB: {e}")

    @classmethod
    def assert_no_autonomous_batch_release(cls, batch_id: str, initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT autonomously release safety-critical products."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous release of product/batch '{batch_id}' is strictly forbidden. "
            "Final product disposition requires authorized human quality engineer sign-off."
        )
        cls._log_guardrail_trip("AUTONOMOUS_RELEASE", batch_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="AUTONOMOUS_PRODUCT_RELEASE_FORBIDDEN")

    @classmethod
    def assert_no_autonomous_batch_rejection(cls, batch_id: str, initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT autonomously reject entire batches without authorization."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous batch rejection of '{batch_id}' without human authorization is strictly forbidden. "
            "Batch quarantine or scrap decisions require human quality engineer approval."
        )
        cls._log_guardrail_trip("AUTONOMOUS_REJECTION", batch_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="AUTONOMOUS_BATCH_REJECTION_FORBIDDEN")

    @classmethod
    def assert_no_machine_parameter_modification(cls, machine_id: str, parameters: Dict[str, Any], initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT modify CNC or machine parameters (e.g. tool offsets, feed rates, spindle speeds)."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous modification of CNC machine parameters on '{machine_id}' is strictly forbidden. "
            f"Requested parameter modifications: {list(parameters.keys())}. CNC parameter changes must be physically executed by certified operators."
        )
        cls._log_guardrail_trip("CNC_PARAM_MODIFICATION", machine_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="CNC_PARAMETER_MODIFICATION_FORBIDDEN")

    @classmethod
    def assert_no_plc_configuration_change(cls, machine_id: str, plc_config: Dict[str, Any], initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT change PLC configurations."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous modification of PLC configurations on '{machine_id}' is strictly forbidden. "
            "PLC modifications require certified controls engineering sign-off."
        )
        cls._log_guardrail_trip("PLC_CONFIG_MODIFICATION", machine_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="PLC_CONFIG_MODIFICATION_FORBIDDEN")

    @classmethod
    def assert_no_autonomous_machinery_stop(cls, machine_id: str, initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT stop production machinery or execute emergency stops autonomously."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous line shutdown or emergency stop on '{machine_id}' is strictly forbidden. "
            "Machine stoppage is restricted to physical E-stops and authorized shop floor personnel."
        )
        cls._log_guardrail_trip("MACHINERY_STOP", machine_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="MACHINERY_STOP_FORBIDDEN")

    @classmethod
    def assert_no_override_engineer_decision(cls, entity_id: str, initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT override quality engineer decisions."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Overriding quality engineer decisions for '{entity_id}' is strictly forbidden. "
            "Human engineering decisions are sovereign and immutable."
        )
        cls._log_guardrail_trip("OVERRIDE_ENGINEER_DECISION", entity_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="OVERRIDE_ENGINEER_DECISION_FORBIDDEN")

    @classmethod
    def assert_no_corrective_machine_action(cls, machine_id: str, action_desc: str = "tool_change", initiated_by: str = "AI_AGENT"):
        """Guardrail: System must NOT execute corrective machine actions autonomously."""
        msg = (
            f"[SAFETY GUARDRAIL VIOLATION] Autonomous execution of corrective machine action '{action_desc}' on '{machine_id}' is strictly forbidden. "
            "Corrective physical actions require human maintenance or operator task authorization and execution."
        )
        cls._log_guardrail_trip("CORRECTIVE_MACHINE_ACTION", machine_id, msg, user_id=initiated_by)
        raise AutonomousActionForbiddenError(msg, violation_code="EXECUTE_CORRECTIVE_MACHINE_ACTION_FORBIDDEN")

safety_guardrail = SafetyGuardrailService()
