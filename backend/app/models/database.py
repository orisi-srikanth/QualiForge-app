"""
SQLAlchemy Database Setup & Seed Repository for Agentic Quality System
Persists all batches, measurements, telemetry, RCA, CAPA, and audit traces in SQLite.
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from backend.app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if "///" in db_url:
        db_file = db_url.split("///")[-1]
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)

engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBProductSpec(Base):
    __tablename__ = "products"
    product_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    part_number = Column(String, nullable=False, unique=True)
    machine_id = Column(String, nullable=False)
    material = Column(String, nullable=False)
    manufacturing_process = Column(String, nullable=False)
    inspection_parameter = Column(String, nullable=False)
    unit = Column(String, default="mm")
    nominal_mm = Column(Float, nullable=False)
    tolerance_mm = Column(Float, nullable=False)
    usl = Column(Float, nullable=False)
    lsl = Column(Float, nullable=False)
    inspection_frequency = Column(String, default="100%")

class DBProductionBatch(Base):
    __tablename__ = "batches"
    batch_id = Column(String, primary_key=True)
    product_id = Column(String, ForeignKey("products.product_id"))
    part_number = Column(String, nullable=False)
    machine = Column(String, nullable=False)
    shift = Column(String, nullable=False)
    material = Column(String, nullable=False)
    material_lot = Column(String, nullable=False)
    quantity = Column(Integer, default=500)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=True)
    status = Column(String, default="QUALITY_HOLD")
    operator = Column(String, default="J. Smith (OP-44)")

class DBMeasurement(Base):
    __tablename__ = "measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("batches.batch_id"))
    sample_id = Column(String, nullable=False)
    measured_value = Column(Float, nullable=False)
    deviation_from_nominal = Column(Float, nullable=False)
    deviation_from_limit = Column(Float, nullable=False)
    is_conforming = Column(Boolean, default=True)
    status = Column(String, default="PASS")
    timestamp = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

class DBVisualInspection(Base):
    __tablename__ = "visual_inspections"
    image_id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    annotated_image_url = Column(String, nullable=True)
    defect_detected = Column(Boolean, default=False)
    defect_type = Column(String, default="none")
    confidence = Column(Float, default=0.0)
    location = Column(String, default="surface")
    bounding_box_json = Column(Text, default="{}")
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

class DBTelemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, nullable=True)
    timestamp = Column(String, nullable=False)
    spindle_speed_rpm = Column(Float, default=1200.0)
    feed_rate_mmrev = Column(Float, default=0.20)
    coolant_temperature_c = Column(Float, default=24.0)
    machine_vibration_mms = Column(Float, default=2.1)
    tool_usage_cycles = Column(Integer, default=600)
    motor_current_a = Column(Float, default=14.5)
    cycle_time_s = Column(Float, default=45.0)
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)
    flags_json = Column(Text, default="[]")

class DBQualityIncident(Base):
    __tablename__ = "incidents"
    incident_id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    defect_type = Column(String, nullable=False)
    severity = Column(String, default="High")
    status = Column(String, default="OPEN")
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    confirmed_root_cause = Column(String, nullable=True)
    rca_json = Column(Text, default="{}")
    critic_json = Column(Text, default="{}")
    human_approval_json = Column(Text, default="{}")

class DBCAPA(Base):
    __tablename__ = "capa_actions"
    action_id = Column(String, primary_key=True)
    incident_id = Column(String, ForeignKey("incidents.incident_id"))
    batch_id = Column(String, nullable=False)
    type = Column(String, nullable=False)  # Containment, Corrective, Preventive
    description = Column(String, nullable=False)
    assigned_role = Column(String, nullable=False)
    due_date = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    evidence_required = Column(String, nullable=False)
    completion_date = Column(String, nullable=True)
    effectiveness_result = Column(String, nullable=True)

class DBAgentAuditLog(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, nullable=False)
    step_number = Column(Integer, nullable=False)
    agent_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    input_summary = Column(Text, nullable=False)
    tool_calls_json = Column(Text, default="[]")
    output_summary = Column(Text, nullable=False)
    certainty_level = Column(String, nullable=False)
    duration_ms = Column(Integer, default=0)
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

def init_db():
    from backend.app.database.session import Base as RealBase, engine as RealEngine
    import backend.app.database.models
    RealBase.metadata.create_all(bind=RealEngine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
