import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    Batch, Measurement, QualityIncident, CAPAAction,
    ProcessReading, Anomaly, WorkflowStateModel, User, Machine, Product
)

client = TestClient(app)

def test_database_is_clean_of_demo_records():
    db = SessionLocal()
    try:
        assert db.query(Batch).count() == 0, "No demo batches should exist in clean state"
        assert db.query(Measurement).count() == 0, "No demo measurements should exist"
        assert db.query(QualityIncident).count() == 0, "No demo incidents should exist"
        assert db.query(CAPAAction).count() == 0, "No demo CAPA actions should exist"
        assert db.query(ProcessReading).count() == 0, "No demo telemetry readings should exist"
        assert db.query(Anomaly).count() == 0, "No demo anomaly records should exist"
        assert db.query(WorkflowStateModel).count() == 0, "No demo workflow checkpoints should exist"
    finally:
        db.close()

def test_essential_configuration_and_users_preserved():
    db = SessionLocal()
    try:
        assert db.query(User).count() >= 3, "Essential user accounts must be preserved"
        assert db.query(Machine).count() >= 4, "Machinery configuration must be preserved"
        assert db.query(Product).count() >= 3, "Product engineering specs must be preserved"
    finally:
        db.close()

def test_dashboard_summary_returns_genuine_zeroes():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["active_batches_count"] == 0
    assert data["total_batches"] == 0
    assert data["total_inspected_parts"] == 0
    assert data["active_quality_incidents"] == 0
    assert data["open_capas"] == 0
    assert data["rejection_rate_percent"] == 0.0
    assert data["top_defect_categories"] == []
    assert data["spc_status"]["process_capability_cpk"] is None
    assert data["spc_status"]["nelson_rules_active"] == []

def test_batches_endpoint_is_empty():
    res = client.get("/api/batches")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_incidents_endpoint_is_empty():
    res = client.get("/api/incidents")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_capa_actions_endpoint_is_empty():
    res = client.get("/api/capa/actions")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["actions"]) == 0

def test_telemetry_endpoint_does_not_synthesize_fake_data():
    res = client.get("/api/process/telemetry?batch_id=NON_EXISTENT_BATCH&machine=CNC-04")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data_points"]) == 0
    assert len(data["anomalies"]) == 0
    assert data["report"]["total_data_points"] == 0
    assert data["report"]["anomalies_detected"] == 0

def test_startup_does_not_recreate_demo_data():
    health_res = client.get("/api/health")
    assert health_res.status_code == 200

    db = SessionLocal()
    try:
        assert db.query(Batch).count() == 0
        assert db.query(Measurement).count() == 0
    finally:
        db.close()
