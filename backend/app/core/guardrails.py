"""
Industrial Guardrail & Autonomous Action Prevention Layer
Enforces ISO 9001 / IATF 16949 Decision-Support Constraints.
Prevents any AI agent or autonomous routine from executing physical or disposition actions.
"""
from enum import Enum
from typing import Set, Dict, Any, Optional
from backend.app.core.logging import logger

class ForbiddenAutonomousAction(Exception):
    """Raised when an autonomous system attempts a safety-critical physical or disposition action."""
    pass

class EpistemicViolation(Exception):
    """Raised when an unauthorized agent emits a restricted epistemic certainty level."""
    pass

class EpistemicLabel(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    MODEL_PREDICTION = "MODEL_PREDICTION"
    STATISTICAL_FINDING = "STATISTICAL_FINDING"
    HYPOTHESIS = "HYPOTHESIS"
    CONFIRMED_ROOT_CAUSE = "CONFIRMED_ROOT_CAUSE"

# The hard allowlist of actions that software agents are permitted to execute
PERMITTED_AGENT_ACTIONS: Set[str] = {
    "parse_file",
    "validate_batch_schema",
    "normalize_units",
    "detect_missing_fields",
    "run_cv_model",
    "compute_gradcam_bbox",
    "format_visual_prediction",
    "compute_spec_limits",
    "check_dimensional_conformance",
    "calculate_deviations",
    "fetch_telemetry",
    "evaluate_operational_thresholds",
    "detect_sudden_step_change",
    "detect_ewma_drift",
    "run_isolation_forest",
    "select_control_chart",
    "compute_control_limits",
    "evaluate_nelson_rules",
    "calculate_capability_indices",
    "build_6m_fishbone",
    "construct_5_whys",
    "query_historical_rag",
    "compute_correlation_matrix",
    "score_hypotheses",
    "formulate_containment_actions",
    "formulate_corrective_actions",
    "formulate_preventive_actions",
    "check_recurrence_history",
    "verify_spec_citations",
    "recompute_numeric_metrics",
    "scan_unsupported_causal_claims",
    "validate_guardrail_compliance",
    "generate_report_draft",
    "request_reassessment",
    "recommend_disposition"  # Recommendation ONLY, not disposition execution
}

# Strictly forbidden autonomous actions
FORBIDDEN_ACTIONS: Set[str] = {
    "release_product",
    "release_batch",
    "reject_batch",
    "scrap_batch",
    "modify_cnc_parameter",
    "change_plc_config",
    "set_feed_rate",
    "set_spindle_speed",
    "stop_machine",
    "emergency_stop",
    "execute_machine_action",
    "override_engineer_decision",
    "confirm_root_cause_autonomous"
}

class GuardrailLayer:
    """Central policy enforcement interceptor for all agentic operations."""

    @staticmethod
    def validate_action(action_name: str, agent_name: str = "System", context: Optional[Dict[str, Any]] = None):
        """
        Validates that the requested action is on the strict allowlist and not in the forbidden set.
        Raises ForbiddenAutonomousAction on violation.
        """
        clean_action = action_name.strip().lower()

        if clean_action in FORBIDDEN_ACTIONS or clean_action not in PERMITTED_AGENT_ACTIONS:
            error_msg = (
                f"[GUARDRAIL VIOLATION] Agent '{agent_name}' attempted forbidden autonomous action '{action_name}'. "
                f"Autonomous machine modification and physical product disposition are strictly barred. "
                f"Action requires authenticated Quality Engineer authority."
            )
            logger.error(error_msg, extra={"agent_name": agent_name, "action": action_name, "context": context})
            raise ForbiddenAutonomousAction(error_msg)

    @staticmethod
    def validate_epistemic_label(label: str, source: str = "Agent", is_human_engineer: bool = False):
        """
        Validates epistemic certainty classification.
        Agents can only emit OBSERVED_FACT, MODEL_PREDICTION, STATISTICAL_FINDING, HYPOTHESIS.
        CONFIRMED_ROOT_CAUSE can ONLY be declared by an authenticated human Quality Engineer.
        """
        try:
            enum_label = EpistemicLabel(label)
        except ValueError:
            raise EpistemicViolation(f"Invalid epistemic label '{label}'. Must be one of {[e.value for e in EpistemicLabel]}")

        if enum_label == EpistemicLabel.CONFIRMED_ROOT_CAUSE and not is_human_engineer:
            raise EpistemicViolation(
                f"[EPISTEMIC VIOLATION] Source '{source}' attempted to declare CONFIRMED_ROOT_CAUSE. "
                f"Only an authenticated Quality Engineer can elevate a finding to CONFIRMED_ROOT_CAUSE."
            )
        return enum_label

guardrails = GuardrailLayer()
