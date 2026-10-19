from enum import Enum
from typing import Set, Dict, Any, Optional
from backend.app.core.logging import logger

class ForbiddenAutonomousAction(Exception):
    pass

class EpistemicViolation(Exception):
    pass

class EpistemicLabel(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    MODEL_PREDICTION = "MODEL_PREDICTION"
    STATISTICAL_FINDING = "STATISTICAL_FINDING"
    HYPOTHESIS = "HYPOTHESIS"
    CONFIRMED_ROOT_CAUSE = "CONFIRMED_ROOT_CAUSE"

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
    "recommend_disposition"
}

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

    @staticmethod
    def validate_action(action_name: str, agent_name: str = "System", context: Optional[Dict[str, Any]] = None):
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
