from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class CertaintyLevel(str, Enum):
    OBSERVED_FACT = "Observed Fact"
    MODEL_PREDICTION = "Model Prediction"
    STATISTICAL_FINDING = "Statistical Finding"
    HYPOTHESIS = "Hypothesis"
    CONFIRMED_ROOT_CAUSE = "Confirmed Root Cause"

class BatchStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    CONFORMING = "CONFORMING"
    QUALITY_HOLD = "QUALITY_HOLD"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ActionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"

class ProductSpec(BaseModel):
    product_id: str = "PROD-PS-101"
    name: str = "Precision Shaft"
    part_number: str = "PS-2026-101"
    machine_id: str = "CNC-04"
    material: str = "Carbon Steel"
    manufacturing_process: str = "CNC Lathe Turning & Grinding"
    inspection_parameter: str = "shaft_diameter"
    unit: str = "mm"
    nominal_mm: float = 50.00
    tolerance_mm: float = 0.05
    usl: float = 50.05
    lsl: float = 49.95
    inspection_frequency: str = "100% or 5-sample continuous sub-group"

class ProductionBatch(BaseModel):
    batch_id: str = "BATCH-0245"
    product_id: str = "PROD-PS-101"
    part_number: str = "PS-2026-101"
    machine: str = "CNC-04"
    shift: str = "Night Shift"
    material: str = "Carbon Steel"
    material_lot: str = "LOT-CS-9842"
    quantity: int = 500
    start_time: str = "2026-10-10 02:00:00"
    end_time: Optional[str] = "2026-10-10 06:30:00"
    status: BatchStatus = BatchStatus.QUALITY_HOLD
    operator: str = "J. Smith (OP-44)"

class UnitConversionRecord(BaseModel):
    sample_id: str
    original_value: float
    original_unit: str
    converted_value_mm: float

class DataIntakeOutput(BaseModel):
    batch_id: str = "BATCH-0245"
    part_number: str = "PS-2026-101"
    machine: str = "CNC-04"
    quantity: int = 500
    material: str = "Carbon Steel"
    shift: str = "Night"
    inspection_parameter: str = "shaft_diameter"
    nominal_mm: float = 50.00
    tolerance_mm: float = 0.05
    usl: float = 50.05
    lsl: float = 49.95
    missing_fields: List[str] = Field(default_factory=list)
    unit_conversions: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    needs_info: bool = False
    measurements: List[Dict[str, Any]] = Field(default_factory=list)
    certainty: CertaintyLevel = CertaintyLevel.OBSERVED_FACT
    production_notes: Optional[str] = None
    llm_interpretation: Optional[Dict[str, Any]] = None
    candidate_metadata: Optional[Dict[str, Any]] = None

class MeasurementItem(BaseModel):
    sample_id: str
    measured_value: float
    deviation_from_nominal: float
    deviation_from_limit: float
    is_conforming: bool
    status: str
    certainty: CertaintyLevel = CertaintyLevel.OBSERVED_FACT

class InspectionReport(BaseModel):
    batch_id: str
    total_inspected: int
    accepted: int
    nonconforming: int
    rejection_rate_percent: float
    measurements: List[MeasurementItem]
    nominal_mm: float
    tolerance_mm: float
    usl: float
    lsl: float
    trend_analysis: Optional[Dict[str, Any]] = None
    trend_direction: Optional[str] = None
    trend_slope: Optional[float] = None
    trend_detected: Optional[bool] = None
    max_deviation_from_limit: Optional[float] = None
    mean: Optional[float] = None
    std_dev_sample: Optional[float] = None
    distribution: Optional[Dict[str, Any]] = None
    certainty: CertaintyLevel = CertaintyLevel.OBSERVED_FACT

from pydantic import BaseModel, Field, model_validator

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class DefectBoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

class DefectItem(BaseModel):
    defect_type: str
    confidence: float
    bounding_box: DefectBoundingBox
    location_zone: str = "mid_region"
    segmentation_mask: Optional[str] = None

class VisualDefectPrediction(BaseModel):
    image_id: str
    batch_id: str
    source: str = "synthetic"
    data_source: str = "synthetic"
    category: str = "precision_shaft"
    product_category: Optional[str] = None
    defect_detected: bool
    anomaly_score: float = 0.0
    defect_type: str
    raw_class: str = "no_defect"
    confidence: float
    location: str
    location_zone: Optional[str] = None
    bbox: Optional[Dict[str, int]] = None
    bounding_box: Optional[BoundingBox] = None
    defects: List[DefectItem] = []
    segmentation_mask: Optional[str] = None
    review_status: str = "HUMAN_REVIEW_REQUIRED"
    severity: str = "High"
    certainty: CertaintyLevel = CertaintyLevel.MODEL_PREDICTION
    label: str = "MODEL_PREDICTION"
    model_version: str = "synthetic-shaft-v1.0"
    image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None
    product_mismatch: bool = False
    mismatch_warning: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("product_category"):
                data["product_category"] = data.get("category", "precision_shaft")
            if not data.get("defects") and data.get("defect_detected"):
                bb = data.get("bounding_box") or data.get("bbox")
                if bb:
                    if isinstance(bb, dict):
                        bx = bb.get("x", 0)
                        by = bb.get("y", 0)
                        bw = bb.get("width", 0)
                        bh = bb.get("height", 0)
                        x1 = bb.get("x1", bx)
                        y1 = bb.get("y1", by)
                        x2 = bb.get("x2", bx + bw)
                        y2 = bb.get("y2", by + bh)
                    else:
                        bx, by, bw, bh = bb.x, bb.y, bb.width, bb.height
                        x1, y1, x2, y2 = bx, by, bx + bw, by + bh
                    loc_zone = data.get("location_zone") or data.get("location", "mid_region")
                    seg = data.get("segmentation_mask") or (data.get("annotated_image_url", "").split("/")[-1] if data.get("annotated_image_url") else None)
                    data["defects"] = [{
                        "defect_type": data.get("defect_type", "surface_defect"),
                        "confidence": data.get("confidence", 0.9),
                        "bounding_box": {
                            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                            "x": bx, "y": by, "width": bw, "height": bh
                        },
                        "location_zone": loc_zone,
                        "segmentation_mask": seg
                    }]
            if not data.get("review_status"):
                data["review_status"] = "HUMAN_REVIEW_REQUIRED" if data.get("defect_detected") else "CONFORMING_VERIFIED"
        return data

class TelemetryDataPoint(BaseModel):
    timestamp: str
    spindle_speed_rpm: float
    feed_rate_mmrev: float
    coolant_temperature_c: float
    machine_vibration_mms: float
    tool_usage_cycles: int
    motor_current_a: float
    cycle_time_s: float
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    flags: List[str] = []
    certainty: CertaintyLevel = CertaintyLevel.STATISTICAL_FINDING

class ProcessMonitoringReport(BaseModel):
    batch_id: str
    machine: str
    total_data_points: int
    anomalies_detected: int
    critical_parameters: List[str]
    vibration_current: float
    vibration_baseline: float
    vibration_status: str
    tool_cycles_current: int
    tool_cycles_baseline: int
    tool_status: str
    temperature_current: float
    temperature_baseline: float
    drift_detected: bool
    certainty: CertaintyLevel = CertaintyLevel.STATISTICAL_FINDING

class NelsonRuleViolation(BaseModel):
    rule_number: int
    rule_name: str
    description: str
    sample_indices: List[int]
    severity: str

class SPCReport(BaseModel):
    batch_id: str
    sample_size: int
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    ucl: Optional[float] = None
    lcl: Optional[float] = None
    cl: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    range_value: Optional[float] = None
    chart_type: str = "I-MR"
    review_status: str = "HUMAN_REVIEW_REQUIRED"
    autonomous_actions_prohibited: bool = True
    usl: Optional[float] = None
    lsl: Optional[float] = None
    cp: Optional[float] = None
    cpk: Optional[float] = None
    pp: Optional[float] = None
    ppk: Optional[float] = None
    capability_assessment: str
    chart_data: List[Dict[str, Any]]
    nelson_violations: List[NelsonRuleViolation]
    distinction_warning: str = (
        "SPECIFICATION LIMITS (USL/LSL = 50.05/49.95) are engineering tolerance boundaries. "
        "STATISTICAL CONTROL LIMITS (UCL/LCL) represent natural 3-sigma process variation. "
        "They are mathematically and operationally distinct concepts."
    )
    certainty: CertaintyLevel = CertaintyLevel.STATISTICAL_FINDING
    status: str = "sufficient"
    warnings: List[str] = []
    sigma_within: Optional[float] = None
    sigma_within_method: Optional[str] = None
    sigma_overall: Optional[float] = None
    sigma_overall_method: Optional[str] = None
    cpk_ci_95: Optional[Dict[str, Any]] = None
    interpretation_band: Optional[str] = None
    guidance_notice: Optional[str] = None
    future_guarantee_disclaimer: Optional[str] = None

class CapabilityRequest(BaseModel):
    batch_id: Optional[str] = "BATCH-0245"
    values: List[float]
    usl: Optional[float] = 50.05
    lsl: Optional[float] = 49.95
    nominal: Optional[float] = 50.00
    subgroup_size: int = 1
    machine_ids: Optional[List[str]] = None
    batch_ids: Optional[List[str]] = None

class CapabilityResponse(BaseModel):
    batch_id: Optional[str] = None
    status: str
    sample_size: int
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    sigma_within: Optional[float] = None
    sigma_within_method: Optional[str] = None
    sigma_overall: Optional[float] = None
    sigma_overall_method: Optional[str] = None
    usl: Optional[float] = None
    lsl: Optional[float] = None
    target: Optional[float] = None
    tolerance_band: Optional[float] = None
    cp: Optional[float] = None
    cpk: Optional[float] = None
    cpu: Optional[float] = None
    cpl: Optional[float] = None
    pp: Optional[float] = None
    ppk: Optional[float] = None
    ppu: Optional[float] = None
    ppl: Optional[float] = None
    cpk_ci_95: Optional[Dict[str, Any]] = None
    normality_test: Optional[Dict[str, Any]] = None
    stability_test: Optional[Dict[str, Any]] = None
    trend_test: Optional[Dict[str, Any]] = None
    outliers: List[int] = []
    assessment: Optional[str] = None
    interpretation_band: Optional[str] = None
    benchmark_source: Optional[str] = None
    warnings: List[str] = []
    guidance_notice: str
    future_guarantee_disclaimer: str
    label: str = "[STATISTICAL_FINDING]"

class HypothesisEvidence(BaseModel):
    hypothesis_id: str
    rank: int = 1
    title: str
    description: str
    category: str
    confidence_score: float
    evidence_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    missing_evidence: List[str] = []
    alternative_explanations: List[str] = []
    required_confirmation: str
    required_approval_role: str = "Quality Engineer"
    sources: Optional[List[str]] = []
    confidence_text: str = "Requires engineering verification"
    epistemic_label: str = "HYPOTHESIS"
    status: str = "UNDER_INVESTIGATION"
    certainty: CertaintyLevel = CertaintyLevel.HYPOTHESIS

class FiveWhysItem(BaseModel):
    level: int
    question: str
    answer: str
    evidence: str
    reasoning_type: str = "Hypothetical Reasoning"
    epistemic_label: str = "HYPOTHESIS"

class FishboneCategory(BaseModel):
    category: str
    factors: List[str]

class HistoricalIncident(BaseModel):
    incident_id: str
    date: str
    title: str
    defect_type: str
    machine: str
    material: str
    confirmed_root_cause: str
    similarity_score: float
    action_taken: str
    certainty: CertaintyLevel = CertaintyLevel.CONFIRMED_ROOT_CAUSE
    disclaimer: str = "Historical context only. Previous incident similarity does not establish current root cause."

class HypothesisActionRequest(BaseModel):
    decision: str
    comment: Optional[str] = None

class RCARequest(BaseModel):
    batch_id: str = "BATCH-0245"
    incident_id: Optional[str] = None
    defect_type: Optional[str] = "Oversized shaft diameter"
    max_measured_val: Optional[float] = None
    usl: Optional[float] = None
    vibration_val: Optional[float] = None
    tool_cycles: Optional[int] = None
    visual_prediction: Optional[Dict[str, Any]] = None
    dimensional_findings: Optional[Dict[str, Any]] = None
    process_report: Optional[Dict[str, Any]] = None
    spc_report: Optional[Dict[str, Any]] = None
    category: Optional[str] = None

class RCAReport(BaseModel):
    incident_id: str
    batch_id: str
    problem_statement: str
    rca_inputs: Optional[Dict[str, Any]] = None
    ranked_hypotheses: List[HypothesisEvidence]
    five_whys: List[FiveWhysItem]
    fishbone_diagram: List[FishboneCategory]
    historical_matches: List[HistoricalIncident]
    correlations: Optional[List[Dict[str, Any]]] = None
    temporal_precedence: Optional[Dict[str, Any]] = None
    pareto_causes: Optional[Dict[str, Any]] = None
    fault_tree: Optional[Dict[str, Any]] = None
    review_status: str = "HUMAN_REVIEW_REQUIRED"
    autonomous_actions_prohibited: bool = True
    causality_disclaimer: str = (
        "IMPORTANT: Statistical correlation, temporal association, LLM narrative, and "
        "historical similarity do not establish proven causation without physical engineering verification and authorized sign-off."
    )
    correlation_vs_causation_note: str = (
        "IMPORTANT: Statistical correlation does not establish proven causation. "
        "Hypotheses require physical engineering verification before confirmation."
    )
    certainty: CertaintyLevel = CertaintyLevel.HYPOTHESIS
    llm_metadata: Optional[Dict[str, Any]] = None

class ActionItem(BaseModel):
    action_id: str
    type: str
    description: str
    assigned_role: str
    due_date: str
    status: ActionStatus = ActionStatus.PENDING
    evidence_required: str
    completion_date: Optional[str] = None
    effectiveness_metric: Optional[str] = None
    hypothesis_id: Optional[str] = None
    preconditions: Optional[str] = None
    affected_population: Optional[str] = None
    rationale: Optional[str] = None
    intended_outcome: Optional[str] = None

class CAPAReport(BaseModel):
    capa_id: str
    incident_id: str
    batch_id: str
    containment_actions: List[ActionItem]
    corrective_actions: List[ActionItem]
    preventive_actions: List[ActionItem]
    requires_engineer_approval: bool = True
    approval_status: str = "PENDING_ENGINEER_APPROVAL"
    approver: Optional[str] = None
    approved_at: Optional[str] = None
    effectiveness_result: Optional[str] = None
    llm_metadata: Optional[Dict[str, Any]] = None

class CriticReview(BaseModel):
    verified_spec_references: bool
    validated_calculations: bool
    cv_predictions_verified: bool
    unsupported_causal_claims_detected: bool
    review_comments: List[str]
    critic_verdict: str
    certainty: CertaintyLevel = CertaintyLevel.STATISTICAL_FINDING

class HumanApprovalRequest(BaseModel):
    approved_by: str
    decision: str
    engineering_comments: str
    confirmed_root_cause: Optional[str] = None
    approved_capa_ids: List[str] = []
    disposition: str

class AgentStepLog(BaseModel):
    step_number: int
    agent_name: str
    status: str
    input_summary: str
    tool_calls: List[str]
    output_summary: str
    certainty_level: CertaintyLevel
    duration_ms: int
    timestamp: str

class KnowledgeStatusResponse(BaseModel):
    status: str
    collection_name: str
    persist_directory: str
    document_count: int
    embedding_model: str
    embedding_type: str
    llm_mode: str
    llm_enabled: bool
    available_source_files: List[str] = []
    last_ingestion: Optional[Dict[str, Any]] = None
    warnings: List[str] = []

class KnowledgeIngestRequest(BaseModel):
    source_paths: Optional[List[str]] = None
    force_reindex: bool = False

class KnowledgeIngestResponse(BaseModel):
    status: str
    files_discovered: int
    files_processed: int
    files_updated: int
    files_skipped: int
    chunks_added: int
    chunks_updated: int
    chunks_deleted: int
    per_file_status: Dict[str, Any] = {}
    warnings: List[str] = []
    errors: List[str] = []

class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None
    source_file: Optional[str] = None
    batch_id: Optional[str] = None
    machine_id: Optional[str] = None
    part_number: Optional[str] = None
    record_id: Optional[str] = None

class KnowledgeMatchItem(BaseModel):
    id: str
    text: str
    source_file: str
    record_id: Optional[str] = None
    category: str
    metadata: Dict[str, Any] = {}
    chunk_index: int = 0
    distance: float = 0.0
    similarity_score: float = 0.0
    distance_metric: str = "cosine_distance"
    rank: int = 1

class KnowledgeQueryResponse(BaseModel):
    query: str
    answer: str
    answer_mode: str
    llm_enabled: bool
    results_count: int
    matches: List[KnowledgeMatchItem] = []
    sources: List[str] = []
    distance_metric: str = "cosine_distance"
    warnings: List[str] = []
