export type CertaintyLevel = 
  | "Observed Fact"
  | "Model Prediction"
  | "Statistical Finding"
  | "Hypothesis"
  | "Confirmed Root Cause";

export interface ProductSpec {
  product_id: string;
  name: string;
  part_number: string;
  machine_id: string;
  material: string;
  manufacturing_process: string;
  inspection_parameter: string;
  unit: string;
  nominal_mm: float;
  tolerance_mm: float;
  usl: float;
  lsl: float;
  inspection_frequency: string;
}

export type float = number;

export interface ProductionBatch {
  id?: string;
  batch_id: string;
  batch_number?: string;
  product_id?: string;
  product_name?: string;
  part_number?: string;
  machine?: string;
  machine_id?: string;
  material?: string;
  material_lot: string;
  shift: string;
  quantity: number;
  start_time: string;
  end_time?: string;
  status: string;
  operator?: string;
  operator_ref?: string;
  rejection_rate?: string;
  nonconforming_count?: number;
}

export type Batch = ProductionBatch;

export interface MeasurementItem {
  sample_id: string;
  measured_value: number;
  deviation_from_nominal: number;
  deviation_from_limit: number;
  is_conforming: boolean;
  status: string;
  certainty: CertaintyLevel;
}

export interface InspectionReport {
  batch_id: string;
  total_inspected: number;
  accepted: number;
  nonconforming: number;
  rejection_rate_percent: number;
  measurements: MeasurementItem[];
  nominal_mm: number;
  tolerance_mm: number;
  usl: number;
  lsl: number;
  certainty: CertaintyLevel;
  mean?: number;
  std_dev_sample?: number;
  min?: number;
  max?: number;
  max_deviation_from_limit?: number;
  histogram_bins?: Array<{
    bin: string;
    edge_low?: number;
    edge_high?: number;
    count: number;
    is_out_of_spec?: boolean;
    color?: string;
  }>;
  nonconforming_items?: Array<{
    sample_id: string;
    component_id?: string;
    measured_value: number;
    nominal_mm?: number;
    limit_breached: string;
    deviation_from_limit: number;
    deviation_from_nominal?: number;
    tolerance_band_usage_percent?: number;
  }>;
  distribution?: {
    mean?: number;
    std_dev_sample?: number;
    min?: number;
    max?: number;
    bin_edges?: number[];
    counts?: number[];
  };
  disposition_notice?: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DefectItem {
  defect_type: string;
  confidence: number;
  bounding_box: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
  };
  location_zone: string;
  segmentation_mask?: string;
}

export interface VisualDefectPrediction {
  image_id: string;
  batch_id: string;
  source?: string;
  data_source?: string;
  category?: string;
  product_category?: string;
  defect_detected: boolean;
  anomaly_score?: number;
  defect_type: string;
  raw_class?: string;
  confidence: number;
  location: string;
  location_zone?: string;
  bbox?: BoundingBox;
  bounding_box?: BoundingBox;
  defects?: DefectItem[];
  segmentation_mask?: string;
  review_status?: string;
  severity: string;
  certainty: CertaintyLevel;
  label?: string;
  model_version?: string;
  image_url?: string;
  annotated_image_url?: string;
}

export interface TelemetryDataPoint {
  timestamp: string;
  spindle_speed_rpm: number;
  feed_rate_mmrev: number;
  coolant_temperature_c: number;
  machine_vibration_mms: number;
  tool_usage_cycles: number;
  motor_current_a: number;
  cycle_time_s: number;
  is_anomaly: boolean;
  anomaly_score: number;
  flags: string[];
  certainty: CertaintyLevel;
}

export interface ProcessMonitoringReport {
  batch_id: string;
  machine: string;
  total_data_points: number;
  anomalies_detected: number;
  critical_parameters: string[];
  vibration_current: number;
  vibration_baseline: number;
  vibration_status: string;
  tool_cycles_current: number;
  tool_cycles_baseline: number;
  tool_status: string;
  temperature_current: number;
  temperature_baseline: number;
  drift_detected: boolean;
  certainty: CertaintyLevel;
}

export interface NelsonRuleViolation {
  rule_number: number;
  rule_name: string;
  description: string;
  sample_indices: number[];
  severity: string;
}

export interface SPCReport {
  batch_id: string;
  sample_size: number;
  mean: number;
  std_dev: number;
  ucl: number;
  lcl: number;
  cl: number;
  usl: number;
  lsl: number;
  cp: number | null;
  cpk: number | null;
  pp: number | null;
  ppk: number | null;
  status?: string;
  warnings?: string[];
  sigma_within?: number | null;
  sigma_within_method?: string;
  sigma_overall?: number | null;
  sigma_overall_method?: string;
  interpretation_band?: string;
  guidance_notice?: string;
  future_guarantee_disclaimer?: string;
  capability_assessment: string;
  chart_data: Array<{
    sample_index: number;
    sample_id: string;
    value: number;
    ucl: number;
    lcl: number;
    cl: number;
    usl: number;
    lsl: number;
    is_out_of_control: boolean;
    is_out_of_spec: boolean;
  }>;
  nelson_violations: NelsonRuleViolation[];
  distinction_warning: string;
  certainty: CertaintyLevel;
}

export interface HypothesisEvidence {
  hypothesis_id: string;
  rank?: number;
  title: string;
  description: string;
  category: string;
  confidence_score: number;
  evidence_score?: number;
  score_breakdown?: {
    base_weight: number;
    sum_supporting: number;
    sum_contradicting: number;
    net_difference: number;
    multiplier: number;
    formula: string;
  };
  supporting_evidence: string[];
  contradicting_evidence: string[];
  missing_evidence?: string[];
  required_confirmation: string;
  sources?: string[];
  confidence_text?: string;
  epistemic_label?: string;
  status: string;
  certainty: CertaintyLevel;
}

export interface FiveWhysItem {
  level: number;
  question: string;
  answer: string;
  evidence: string;
}

export interface FishboneCategory {
  category: string;
  factors: string[];
}

export interface HistoricalIncident {
  incident_id: string;
  date: string;
  title: string;
  defect_type: string;
  machine: string;
  material: string;
  confirmed_root_cause: string;
  similarity_score: number;
  action_taken: string;
  disclaimer?: string;
  certainty: CertaintyLevel;
}

export interface RCAReport {
  incident_id: string;
  batch_id: string;
  problem_statement: string;
  rca_inputs?: any;
  ranked_hypotheses: HypothesisEvidence[];
  five_whys: FiveWhysItem[];
  fishbone_diagram: FishboneCategory[];
  historical_matches: HistoricalIncident[];
  correlations?: Array<{
    parameter_x: string;
    parameter_y: string;
    pearson_r: number;
    pearson_p_value: number;
    spearman_rho: number;
    spearman_p_value: number;
    sample_size: number;
    disclaimer: string;
  }>;
  temporal_precedence?: any;
  pareto_causes?: any;
  correlation_vs_causation_note: string;
  certainty: CertaintyLevel;
}

export interface ActionItem {
  action_id: string;
  type: string;
  description: string;
  assigned_role: string;
  due_date: string;
  status: string;
  evidence_required: string;
  completion_date?: string;
  effectiveness_metric?: string;
}

export interface CAPAActionRecord {
  id: string;
  action_id: string;
  action_code: string;
  incident_id: string;
  hypothesis_id?: string | null;
  type: string; // containment, corrective, preventive
  description: string;
  suggested_role?: string | null;
  responsible_role?: string | null;
  assigned_role: string;
  due_date: string;
  status: string; // proposed, approved, in_progress, completed, verified, rejected
  evidence?: string;
  evidence_file_path?: string | null;
  completion_date?: string | null;
  effectiveness_result?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at?: string | null;
  created_by?: string | null;
  is_overdue: boolean;
}

export interface CAPAReport {
  capa_id: string;
  incident_id: string;
  batch_id: string;
  containment_actions: ActionItem[];
  corrective_actions: ActionItem[];
  preventive_actions: ActionItem[];
  requires_engineer_approval: boolean;
  approval_status: string;
  approver?: string;
  approved_at?: string;
  effectiveness_result?: string;
}

export interface CriticReview {
  verified_spec_references: boolean;
  validated_calculations: boolean;
  cv_predictions_verified: boolean;
  unsupported_causal_claims_detected: boolean;
  review_comments: string[];
  critic_verdict: string;
  certainty: CertaintyLevel;
}

export interface AgentStepLog {
  step_number: number;
  agent_name: string;
  status: string;
  input_summary: string;
  tool_calls: string[];
  output_summary: string;
  certainty_level: CertaintyLevel;
  duration_ms: number;
  timestamp: string;
}

export interface WorkflowState {
  workflow_id: string;
  batch_id: string;
  status: string;
  current_agent?: string;
  execution_trace: AgentStepLog[];
  batch_metadata?: any;
  dimensional_report?: InspectionReport;
  visual_prediction?: VisualDefectPrediction;
  process_report?: ProcessMonitoringReport;
  spc_report?: SPCReport;
  rca_report?: RCAReport;
  capa_report?: CAPAReport;
  critic_review?: CriticReview;
  human_approval?: any;
  has_defects: boolean;
  has_anomalies: boolean;
  has_spc_violations: boolean;
  completed_at?: string;
}

export interface TestScenarioResult {
  test_id: string;
  scenario: string;
  input: string;
  initial_state: string;
  expected_result: string;
  actual_result: string;
  agents_involved: string[];
  ml_model_output: string;
  evidence: string;
  status: "PASS" | "FAIL";
}

export interface ProcessInvestigationReport {
  batch_id: string;
  batch_db_id?: string;
  product: {
    id?: string;
    part_number: string;
    name: string;
    material: string;
    process: string;
  };
  machine: {
    id?: string;
    code: string;
    type: string;
    location: string;
  };
  shift: string;
  batch_status: string;
  batch_quantity: number;
  specification: {
    characteristic: string;
    unit: string;
    nominal: number;
    usl: number;
    lsl: number;
    tolerance_plus: number;
    tolerance_minus: number;
  };
  inspection_summary: {
    total_inspected: number;
    conforming_count: number;
    nonconforming_count: number;
    rejection_rate_percent: number;
    has_oversized: boolean;
    has_undersized: boolean;
    has_visual_defect: boolean;
    conformance_verdict: string;
  };
  nonconforming_samples: Array<{
    sample_id: string;
    measured_value: number;
    unit: string;
    status: string;
    deviation_from_limit: number;
    measured_at?: string;
    source?: string;
  }>;
  conforming_samples: Array<{
    sample_id: string;
    measured_value: number;
    unit: string;
    status: string;
    deviation_from_limit: number;
    measured_at?: string;
    source?: string;
  }>;
  visual_findings: Array<{
    id: string;
    defect_detected: boolean;
    defect_type: string;
    confidence: number;
    location: string;
    model_version?: string;
    human_status?: string;
  }>;
  strategy: {
    strategy: string;
    title: string;
    description: string;
  };
  investigation_status: string;
  hypotheses: Array<{
    hypothesis_id: string;
    title: string;
    category: string;
    description: string;
    confidence_score: number;
    evidence_score: number;
    status: string;
    epistemic_label: string;
    supporting_evidence: string[];
    contradicting_evidence: string[];
    missing_evidence: string[];
    required_confirmation: string;
  }>;
  missing_data_sources: string[];
  verification_steps: string[];
  recommended_actions: Array<{
    type: string;
    action: string;
    responsible: string;
    urgency: string;
  }>;
  capa_actions: Array<{
    id: string;
    action_code: string;
    type: string;
    description: string;
    status: string;
    due_date: string;
    responsible_role?: string;
  }>;
  incident_id?: string;
  investigation_timestamp: string;
  correlation_vs_causation_note: string;
  epistemic_label: string;
}
