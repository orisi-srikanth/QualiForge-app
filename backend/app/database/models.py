import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def gen_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    part_number = Column(String, unique=True, index=True, nullable=False)
    process = Column(String, nullable=False)
    material = Column(String, nullable=False)
    family = Column(String, default="Precision Shafts")
    machine_id = Column(String, ForeignKey("machines.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    machine = relationship("Machine")
    characteristics = relationship("InspectionCharacteristic", back_populates="product", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="product")

class Machine(Base):
    __tablename__ = "machines"
    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    batches = relationship("Batch", back_populates="machine")
    maintenance_records = relationship("MaintenanceRecord", back_populates="machine")

class InspectionCharacteristic(Base):
    __tablename__ = "inspection_characteristics"
    id = Column(String, primary_key=True, default=gen_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    unit = Column(String, default="mm")
    nominal = Column(Float, nullable=False)
    tol_plus = Column(Float, nullable=False)
    tol_minus = Column(Float, nullable=False)
    lsl = Column(Float, nullable=False)
    usl = Column(Float, nullable=False)
    inspection_frequency = Column(String, default="100%")
    sample_size = Column(Integer, default=5)

    product = relationship("Product", back_populates="characteristics")

class Batch(Base):
    __tablename__ = "batches"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_number = Column(String, unique=True, index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    shift = Column(String, nullable=False)
    quantity = Column(Integer, default=500)
    material_lot = Column(String, nullable=False)
    operator_ref = Column(String, default="OP-44")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="QUALITY_HOLD")
    scenario_label = Column(String, nullable=True)

    product = relationship("Product", back_populates="batches")
    machine = relationship("Machine", back_populates="batches")
    measurements = relationship("Measurement", back_populates="batch")
    images = relationship("InspectionImage", back_populates="batch")
    readings = relationship("ProcessReading", back_populates="batch")
    incidents = relationship("QualityIncident", back_populates="batch")

class Measurement(Base):
    __tablename__ = "measurements"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    characteristic_id = Column(String, ForeignKey("inspection_characteristics.id"), nullable=False, index=True)
    component_id = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, default="mm")
    measured_at = Column(DateTime, default=utc_now)
    subgroup = Column(Integer, default=1)
    status = Column(String, default="conforming")
    deviation_from_limit = Column(Float, default=0.0)
    source_type = Column(String, default="manual")
    file_name = Column(String, nullable=True)
    uploaded_by = Column(String, nullable=True)
    upload_time = Column(DateTime, default=utc_now)

    batch = relationship("Batch", back_populates="measurements")

class InspectionImage(Base):
    __tablename__ = "inspection_images"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    component_id = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    sha256_hash = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=utc_now)
    uploaded_by = Column(String, nullable=True)

    batch = relationship("Batch", back_populates="images")
    findings = relationship("VisualFinding", back_populates="image")

class VisualFinding(Base):
    __tablename__ = "visual_findings"
    id = Column(String, primary_key=True, default=gen_uuid)
    image_id = Column(String, ForeignKey("inspection_images.id"), nullable=False, index=True)
    defect_detected = Column(Boolean, default=False)
    defect_type = Column(String, default="no_defect")
    confidence = Column(Float, default=0.0)
    bbox = Column(Text, default="[]")
    location = Column(String, default="center")
    model_version = Column(String, default="cv-v1.0")
    human_status = Column(String, default="pending")
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)
    heatmap_url = Column(String, nullable=True)

    image = relationship("InspectionImage", back_populates="findings")

class ProcessReading(Base):
    __tablename__ = "process_readings"
    id = Column(String, primary_key=True, default=gen_uuid)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    ts = Column(DateTime, nullable=False, index=True)
    spindle_speed = Column(Float, nullable=False)
    feed_rate = Column(Float, nullable=False)
    coolant_temp = Column(Float, nullable=False)
    vibration = Column(Float, nullable=False)
    tool_usage_cycles = Column(Integer, nullable=False)
    motor_current = Column(Float, nullable=False)
    cycle_time = Column(Float, nullable=False)
    pressure = Column(Float, default=5.5)

    batch = relationship("Batch", back_populates="readings")

class ProcessBaseline(Base):
    __tablename__ = "process_baselines"
    id = Column(String, primary_key=True, default=gen_uuid)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    parameter = Column(String, nullable=False)
    mean = Column(Float, nullable=False)
    std = Column(Float, nullable=False)
    p01 = Column(Float, nullable=False)
    p99 = Column(Float, nullable=False)
    lower_threshold = Column(Float, nullable=False)
    upper_threshold = Column(Float, nullable=False)
    computed_from = Column(String, default="Baseline Run Batch B001-B010")

class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(String, primary_key=True, default=gen_uuid)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    parameter = Column(String, nullable=False)
    ts = Column(DateTime, nullable=False)
    type = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    details_json = Column(Text, default="{}")

class SPCResult(Base):
    __tablename__ = "spc_results"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    characteristic_id = Column(String, ForeignKey("inspection_characteristics.id"), nullable=False)
    chart_type = Column(String, nullable=False)
    center_line = Column(Float, nullable=False)
    ucl = Column(Float, nullable=False)
    lcl = Column(Float, nullable=False)
    violations_json = Column(Text, default="[]")
    cp = Column(Float, nullable=True)
    cpk = Column(Float, nullable=True)
    pp = Column(Float, nullable=True)
    ppk = Column(Float, nullable=True)
    n = Column(Integer, nullable=False)
    warnings_json = Column(Text, default="[]")

class QualityIncident(Base):
    __tablename__ = "quality_incidents"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    defect_type = Column(String, nullable=False)
    severity = Column(String, default="HIGH")
    status = Column(String, default="open")
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    batch = relationship("Batch", back_populates="incidents")
    hypotheses = relationship("RCAHypothesis", back_populates="incident")
    capas = relationship("CAPAAction", back_populates="incident")

class RCAHypothesis(Base):
    __tablename__ = "rca_hypotheses"
    id = Column(String, primary_key=True, default=gen_uuid)
    incident_id = Column(String, ForeignKey("quality_incidents.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    label = Column(String, default="HYPOTHESIS")
    supporting_evidence_json = Column(Text, default="[]")
    contradicting_evidence_json = Column(Text, default="[]")
    missing_evidence_json = Column(Text, default="[]")
    evidence_score = Column(Float, default=0.0)
    confidence_text = Column(String, default="Requires engineering verification")
    status = Column(String, default="proposed")
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=True)

    incident = relationship("QualityIncident", back_populates="hypotheses")

class HistoricalIncident(Base):
    __tablename__ = "historical_incidents"
    id = Column(String, primary_key=True, default=gen_uuid)
    ncr_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    defect_type = Column(String, nullable=False)
    part_number = Column(String, nullable=False)
    machine = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    confirmed_root_cause = Column(Text, nullable=False)
    resolution = Column(Text, nullable=False)
    date = Column(String, nullable=False)

class CAPAAction(Base):
    __tablename__ = "capa_actions"
    id = Column(String, primary_key=True, default=gen_uuid)
    incident_id = Column(String, ForeignKey("quality_incidents.id"), nullable=False, index=True)
    hypothesis_id = Column(String, ForeignKey("rca_hypotheses.id"), nullable=True, index=True)
    action_code = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    suggested_role = Column(String, nullable=True)
    responsible_role = Column(String, nullable=True)
    due_date = Column(String, nullable=False)
    status = Column(String, default="proposed")
    evidence = Column(Text, default="")
    evidence_file_path = Column(String, nullable=True)
    completion_date = Column(String, nullable=True)
    effectiveness_result = Column(Text, nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    incident = relationship("QualityIncident", back_populates="capas")
    hypothesis = relationship("RCAHypothesis")
    approver = relationship("User", foreign_keys=[approved_by])
    effectiveness_checks = relationship("EffectivenessCheck", back_populates="capa")

class CAPASequence(Base):
    __tablename__ = "capa_sequences"
    year = Column(Integer, primary_key=True)
    last_seq = Column(Integer, nullable=False, default=0)

class EffectivenessCheck(Base):
    __tablename__ = "effectiveness_checks"
    id = Column(String, primary_key=True, default=gen_uuid)
    capa_id = Column(String, ForeignKey("capa_actions.id"), nullable=False, index=True)
    window_before_json = Column(Text, default="{}")
    window_after_json = Column(Text, default="{}")
    rejection_rate_before = Column(Float, nullable=False)
    rejection_rate_after = Column(Float, nullable=False)
    test_used = Column(String, default="two_proportion_z_test")
    p_value = Column(Float, nullable=False)
    conclusion_label = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)

    capa = relationship("CAPAAction", back_populates="effectiveness_checks")

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True, default=gen_uuid)
    workflow_id = Column(String, nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    agent_name = Column(String, nullable=False)
    started_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, default=utc_now)
    input_json = Column(Text, default="{}")
    tool_calls_json = Column(Text, default="[]")
    model_outputs_json = Column(Text, default="{}")
    retrieved_evidence_json = Column(Text, default="[]")
    status = Column(String, default="COMPLETED")

class HumanDecision(Base):
    __tablename__ = "human_decisions"
    id = Column(String, primary_key=True, default=gen_uuid)
    workflow_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    decision = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ts = Column(DateTime, default=utc_now)

class ReviewerComment(Base):
    __tablename__ = "reviewer_comments"
    id = Column(String, primary_key=True, default=gen_uuid)
    workflow_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False)
    severity = Column(String, default="WARNING")
    comment = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    generated_at = Column(DateTime, default=utc_now)

class KBDocument(Base):
    __tablename__ = "kb_documents"
    id = Column(String, primary_key=True, default=gen_uuid)
    doc_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    source_file = Column(String, nullable=False)
    chunks_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    id = Column(String, primary_key=True, default=gen_uuid)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    date = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    tool_change_flag = Column(Boolean, default=False)

    machine = relationship("Machine", back_populates="maintenance_records")

class WorkflowStateModel(Base):
    __tablename__ = "workflow_state"
    workflow_id = Column(String, primary_key=True, index=True)
    state_json = Column(Text, nullable=False)
    current_node = Column(String, nullable=False)
    status = Column(String, default="running")
    updated_at = Column(DateTime, default=utc_now)
