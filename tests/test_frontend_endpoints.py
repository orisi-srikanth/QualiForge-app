import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "HEALTHY"]

def test_auth_login_quality_engineer():
    res = client.post("/api/auth/login", json={"username": "engineer@precisionaero.com", "password": "any"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "quality_engineer"
    assert "access_token" in data

def test_auth_login_operator():
    res = client.post("/api/auth/login", json={"username": "operator@precisionaero.com", "password": "any"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "operator"

def test_auth_me():
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert "name" in data

def test_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "acceptance_rate_percent" in data
    assert "rejection_rate_percent" in data
    assert "active_quality_incidents" in data
    assert "production_batches" in data
    assert "inspection_quantity" in data

def test_batches_endpoint():
    res = client.get("/api/batches")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_products_and_machines():
    res_p = client.get("/api/products")
    assert res_p.status_code == 200
    assert isinstance(res_p.json(), list)

    res_m = client.get("/api/machines")
    assert res_m.status_code == 200
    assert isinstance(res_m.json(), list)

def test_inspection_measurements():
    res = client.get("/api/inspection/measurements?batch_id=BATCH-0245")
    assert res.status_code == 200
    data = res.json()
    assert "measurements" in data or isinstance(data, list)

def test_vision_findings():
    res = client.get("/api/vision/findings")
    assert res.status_code == 200

def test_incidents_and_rca():
    res_inc = client.get("/api/incidents")
    assert res_inc.status_code == 200

    res_rca = client.get("/api/rca/analyze?incident_id=INC-2026-088&batch_id=BATCH-0245")
    assert res_rca.status_code == 200

def test_capa_and_human_decisions():
    res_capa = client.get("/api/capa/actions")
    assert res_capa.status_code == 200

    res_dec = client.get("/api/human-decisions")
    assert res_dec.status_code == 200

def test_reports_pdf():
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
