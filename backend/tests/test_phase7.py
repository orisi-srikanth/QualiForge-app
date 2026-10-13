"""
Unit & Integration Tests for Phase 7: Backend REST API
Tests all domain endpoints, auth, pareto, effectiveness, and HITL workflow decision.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token, UserRole

client = TestClient(app)

def test_api_health_and_version():
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_ver = client.get("/api/version")
    assert res_ver.status_code == 200
    assert "QualityMind" in res_ver.json()["system"]

def test_api_auth_removed_and_open():
    """Verify that authentication is completely removed and endpoints are open without tokens."""
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/dashboard/summary")
    assert res.status_code == 200
    assert "overall_health_score" in res.json()

def test_api_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "overall_health_score" in data
    assert "top_defect_categories" in data
    assert len(data["top_defect_categories"]) > 0

def test_api_products_and_batches():
    res_p = client.get("/api/products")
    assert res_p.status_code == 200
    assert len(res_p.json()) >= 1

    res_b = client.get("/api/batches")
    assert res_b.status_code == 200
    assert len(res_b.json()) >= 1

def test_api_inspection_evaluation():
    payload = {
        "batch_id": "BATCH-0245",
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "measurements": [
            {"sample_id": "P001", "measured_value": 50.01},
            {"sample_id": "P002", "measured_value": 50.03},
            {"sample_id": "P003", "measured_value": 50.06},
            {"sample_id": "P004", "measured_value": 50.08},
            {"sample_id": "P005", "measured_value": 50.07},
        ]
    }
    res = client.post("/api/inspection/evaluate", json=payload)
    assert res.status_code == 200
    rep = res.json()["report"]
    assert rep["nonconforming"] == 3
    assert rep["rejection_rate_percent"] == 60.0

def test_api_pareto_endpoint():
    res = client.get("/api/pareto?dimension=defect_type")
    assert res.status_code == 200
    data = res.json()
    assert "vital_few_categories" in data
    assert "items" in data

def test_api_effectiveness_endpoint():
    res = client.get("/api/effectiveness/CAPA-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert data["is_statistically_significant"] is True
    assert "Observed association" in data["conclusion_label"]

def test_api_workflow_lifecycle_and_hitl_resume():
    # 1. Start workflow
    res_start = client.post("/api/workflows?batch_id=BATCH-0245")
    assert res_start.status_code == 200
    state = res_start.json()
    wf_id = state["workflow_id"]
    assert state["status"] == "PENDING_HUMAN_APPROVAL"

    # 2. Get trace
    res_trace = client.get(f"/api/workflows/{wf_id}/trace")
    assert res_trace.status_code == 200
    trace = res_trace.json()
    assert len(trace) >= 5

    # 3. Human Quality Engineer submits decision to resume
    decision_payload = {
        "batch_id": "BATCH-0245",
        "approved_by": "Sarah Chen, Lead Quality Engineer",
        "decision": "DISPOSITION_APPROVED",
        "confirmed_root_cause": "Progressive Carbide Insert Flank Wear (Confirmed under toolmakers microscope)",
        "disposition": "REWORK_AND_TOOL_REPLACE",
        "engineering_comments": "Tool inspected; VB measured 0.38 mm. Tool replaced and offset recalibrated."
    }
    res_dec = client.post(f"/api/workflows/{wf_id}/decision", json=decision_payload)
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "RESUMED_AND_COMPLETED"
    assert res_dec.json()["certainty"] == "Confirmed Root Cause"
