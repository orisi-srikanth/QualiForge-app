from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.schemas import (
    ProductionBatch, InspectionReport, VisualDefectPrediction,
    ProcessMonitoringReport, SPCReport, RCAReport, CAPAReport,
    CriticReview, AgentStepLog, HumanApprovalRequest
)

class WorkflowState(BaseModel):
    workflow_id: str
    batch_id: str
    status: str = "INITIALIZED"
    current_agent: Optional[str] = None
    execution_trace: List[AgentStepLog] = []

    batch_metadata: Optional[Dict[str, Any]] = None
    dimensional_report: Optional[InspectionReport] = None
    visual_prediction: Optional[VisualDefectPrediction] = None
    visual_findings: Optional[List[Dict[str, Any]]] = None
    process_report: Optional[ProcessMonitoringReport] = None
    spc_report: Optional[SPCReport] = None
    rca_report: Optional[RCAReport] = None
    capa_report: Optional[CAPAReport] = None
    critic_review: Optional[CriticReview] = None
    human_approval: Optional[HumanApprovalRequest] = None

    has_defects: bool = False
    has_anomalies: bool = False
    has_spc_violations: bool = False
    product_mismatch: bool = False
    product_mismatch_warning: Optional[str] = None
    completed_at: Optional[str] = None

    stage_statuses: Dict[str, str] = Field(default_factory=dict)
    reassessment_loops: int = 0
    effectiveness_report: Optional[Dict[str, Any]] = None
    report_id: Optional[str] = None
