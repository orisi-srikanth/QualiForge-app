"""
Clean Startup Verification Test Suite
Verifies that QualiForge starts in a genuinely clean state:
- Zero demo batches, measurements, incidents, CAPAs, or telemetry in development database
- Endpoints return empty arrays / zero aggregates
- Fresh startup does NOT recreate demo records or synthesize mock data
"""
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
    """Verify that all transactional business tables have 0 demo rows."""
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
    """Verify that genuine user accounts, machines, and product catalogs are preserved."""
    db = SessionLocal()
    try:
        assert db.query(User).count() >= 3, "Essential user accounts must be preserved"
        assert db.query(Machine).count() >= 4, "Machinery configuration must be preserved"
        assert db.query(Product).count() >= 3, "Product engineering specs must be preserved"
    finally:
        db.close()

def test_dashboard_summary_returns_genuine_zeroes():
    """Verify that /api/dashboard/summary returns clean zero counters, not fake KPIs."""
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
    """Verify that /api/batches endpoint returns empty list without fallback fake batches."""
    res = client.get("/api/batches")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_incidents_endpoint_is_empty():
    """Verify that /api/incidents endpoint returns empty list."""
    res = client.get("/api/incidents")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_capa_actions_endpoint_is_empty():
    """Verify that /api/capa/actions returns zero actions and does NOT auto-seed BATCH-0245 proposals."""
    res = client.get("/api/capa/actions")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["actions"]) == 0

def test_telemetry_endpoint_does_not_synthesize_fake_data():
    """Verify that /api/process/telemetry does not generate fake sensor readings."""
    res = client.get("/api/process/telemetry?batch_id=NON_EXISTENT_BATCH&machine=CNC-04")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data_points"]) == 0
    assert len(data["anomalies"]) == 0
    assert data["report"]["total_data_points"] == 0
    assert data["report"]["anomalies_detected"] == 0

def test_startup_does_not_recreate_demo_data():
    """Simulate fresh app access and confirm clean zero state persists."""
    # Ping key health and root endpoints
    health_res = client.get("/api/health")
    assert health_res.status_code == 200

    # Ensure no rows were secretly inserted during startup or health check
    db = SessionLocal()
    try:
        assert db.query(Batch).count() == 0
        assert db.query(Measurement).count() == 0
    finally:
        db.close()
