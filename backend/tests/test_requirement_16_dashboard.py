import pytest
import sqlite3
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

import os
from backend.app.main import app
from backend.app.core.security import create_access_token, UserRole

DB_PATH = os.path.abspath("backend/data/quality_system.db")

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def qe_token():
    return create_access_token({"sub": "engineer@precisionaero.com", "role": UserRole.QUALITY_ENGINEER.value})

@pytest.fixture
def operator_token():
    return create_access_token({"sub": "operator@precisionaero.com", "role": UserRole.OPERATOR.value})

@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin@precisionaero.com", "role": UserRole.ADMIN.value})

@pytest.fixture
def qe_headers(qe_token):
    return {"Authorization": f"Bearer {qe_token}"}

@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

def test_ten_dashboard_items_present_and_defined(client, qe_headers):
    res = client.get("/api/dashboard/summary", headers=qe_headers)
    assert res.status_code == 200
    data = res.json()

    assert "production_batches" in data
    assert "total_count" in data["production_batches"]
    assert "status_split" in data["production_batches"]
    assert isinstance(data["production_batches"]["status_split"], dict)

    assert "inspection_quantity" in data
    assert "total_inspected_parts" in data["inspection_quantity"]
    assert "accepted_parts" in data["inspection_quantity"]
    assert "nonconforming_parts" in data["inspection_quantity"]

    assert "acceptance_rate_percent" in data
    assert isinstance(data["acceptance_rate_percent"], (int, float))

    assert "rejection_rate_percent" in data
    assert isinstance(data["rejection_rate_percent"], (int, float))

    assert "active_quality_incidents" in data
    assert isinstance(data["active_quality_incidents"], int)

    assert "top_defect_categories" in data
    assert isinstance(data["top_defect_categories"], list)

    assert "machine_anomalies_detected" in data
    assert isinstance(data["machine_anomalies_detected"], int)

    assert "open_capas" in data
    assert isinstance(data["open_capas"], int)

    assert "overdue_capas" in data
    assert isinstance(data["overdue_capas"], int)

    assert "process_control_status" in data
    assert "status" in data["process_control_status"]
    assert "reason" in data["process_control_status"]
    assert "notice" in data["process_control_status"]

def test_independent_sql_recomputation_full_and_filtered(client, qe_headers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    res_full = client.get("/api/dashboard/summary", headers=qe_headers)
    assert res_full.status_code == 200
    app_full = res_full.json()

    c.execute("SELECT count(*) FROM batches")
    sql_batches_count = c.fetchone()[0]
    c.execute("SELECT status, count(*) FROM batches GROUP BY status")
    sql_batches_split = dict(c.fetchall())
    assert app_full["production_batches"]["total_count"] == sql_batches_count
    assert app_full["production_batches"]["status_split"] == sql_batches_split

    c.execute("SELECT count(*) FROM measurements")
    sql_inspected = c.fetchone()[0]
    c.execute("SELECT count(*) FROM measurements WHERE status IN ('conforming', 'rejected_conforming')")
    sql_accepted = c.fetchone()[0]
    c.execute("SELECT count(*) FROM measurements WHERE status IN ('nonconforming', 'confirmed_nonconforming')")
    sql_nonconforming = c.fetchone()[0]

    assert app_full["inspection_quantity"]["total_inspected_parts"] == sql_inspected
    assert app_full["inspection_quantity"]["accepted_parts"] == sql_accepted
    assert app_full["inspection_quantity"]["nonconforming_parts"] == sql_nonconforming
    assert sql_accepted + sql_nonconforming == sql_inspected

    sql_acc_rate = round(sql_accepted / sql_inspected * 100.0, 2)
    sql_rej_rate = round(sql_nonconforming / sql_inspected * 100.0, 2)
    assert abs(app_full["acceptance_rate_percent"] - sql_acc_rate) <= 0.02
    assert abs(app_full["rejection_rate_percent"] - sql_rej_rate) <= 0.02
    assert round(app_full["acceptance_rate_percent"] + app_full["rejection_rate_percent"], 1) == 100.0

    c.execute("SELECT count(*) FROM quality_incidents WHERE lower(status) != 'closed'")
    sql_active_incidents = c.fetchone()[0]
    assert app_full["active_quality_incidents"] == sql_active_incidents

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    c.execute("SELECT count(*) FROM capa_actions WHERE status IN ('proposed', 'approved', 'in_progress', 'pending')")
    sql_open_capas = c.fetchone()[0]
    c.execute(f"SELECT count(*) FROM capa_actions WHERE status IN ('proposed', 'approved', 'in_progress', 'pending') AND due_date < '{today_str}'")
    sql_overdue_capas = c.fetchone()[0]
    assert app_full["open_capas"] == sql_open_capas
    assert app_full["overdue_capas"] == sql_overdue_capas

    s_date = "2026-10-01"
    e_date = "2026-10-11"
    res_filt = client.get(f"/api/dashboard/summary?start_date={s_date}&end_date={e_date}", headers=qe_headers)
    assert res_filt.status_code == 200
    app_filt = res_filt.json()

    c.execute(f"SELECT count(*) FROM batches WHERE start_time >= '{s_date}' AND start_time <= '{e_date} 23:59:59'")
    sql_filt_batches = c.fetchone()[0]
    assert app_filt["production_batches"]["total_count"] == sql_filt_batches

    c.execute(f"SELECT count(*) FROM measurements WHERE measured_at >= '{s_date}' AND measured_at <= '{e_date} 23:59:59'")
    sql_filt_inspected = c.fetchone()[0]
    assert app_filt["inspection_quantity"]["total_inspected_parts"] == sql_filt_inspected

    conn.close()

def test_filters_and_boundary_conditions(client, qe_headers):
    res_day = client.get("/api/dashboard/summary?start_date=2026-10-10&end_date=2026-10-10", headers=qe_headers)
    assert res_day.status_code == 200
    data_day = res_day.json()
    assert data_day["filter_applied"]["is_filtered"] is True

    res_empty = client.get("/api/dashboard/summary?start_date=2020-01-01&end_date=2020-01-02", headers=qe_headers)
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["production_batches"]["total_count"] == 0
    assert data_empty["inspection_quantity"]["total_inspected_parts"] == 0
    assert data_empty["acceptance_rate_percent"] == 0.0
    assert data_empty["rejection_rate_percent"] == 0.0
    assert data_empty["process_control_status"]["status"] == "NO_DATA"

    res_rev = client.get("/api/dashboard/summary?start_date=2026-10-15&end_date=2026-10-01", headers=qe_headers)
    assert res_rev.status_code == 400
    assert "Reversed date range" in res_rev.json()["detail"]

    res_inv = client.get("/api/dashboard/summary?start_date=invalid-date", headers=qe_headers)
    assert res_inv.status_code == 422
    assert "Invalid start_date format" in res_inv.json()["detail"]

def test_live_behavior_mutations(client, qe_headers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    res1 = client.get("/api/dashboard/summary", headers=qe_headers)
    d1 = res1.json()
    base_inspected = d1["inspection_quantity"]["total_inspected_parts"]
    base_overdue = d1["overdue_capas"]

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO measurements (id, batch_id, characteristic_id, component_id, value, measured_at, status)
        VALUES ('TEST-MEAS-001', 'BATCH-0245', 'char-01', 'P999', 50.01, ?, 'conforming')
    """, (now_str,))
    
    c.execute("""
        INSERT INTO capa_actions (id, incident_id, action_code, type, description, due_date, status, created_at)
        VALUES ('TEST-CAPA-OVERDUE-01', 'inc-ncr-019', 'CAPA-OVERDUE-999', 'corrective', 'Test overdue', '2026-01-01', 'in_progress', ?)
    """, (now_str,))
    conn.commit()

    try:
        res2 = client.get("/api/dashboard/summary", headers=qe_headers)
        d2 = res2.json()
        assert d2["inspection_quantity"]["total_inspected_parts"] == base_inspected + 1
        assert d2["overdue_capas"] == base_overdue + 1
    finally:
        c.execute("DELETE FROM measurements WHERE id = 'TEST-MEAS-001'")
        c.execute("DELETE FROM capa_actions WHERE id = 'TEST-CAPA-OVERDUE-01'")
        conn.commit()
        conn.close()

def test_cross_page_consistency(client, qe_headers):
    dash_res = client.get("/api/dashboard/summary", headers=qe_headers).json()

    pareto_res = client.get("/api/pareto?dimension=defect_type").json()
    assert len(dash_res["top_defect_categories"]) > 0
    assert dash_res["top_defect_categories"][0]["defect"] == pareto_res["items"][0]["category"]
    assert dash_res["top_defect_categories"][0]["count"] == pareto_res["items"][0]["count"]

    capa_res = client.get("/api/capa/actions").json()
    capa_list = capa_res.get("actions", capa_res) if isinstance(capa_res, dict) else capa_res
    if isinstance(capa_list, dict):
        capa_list = list(capa_list.values())
    open_capas_api = sum(1 for c in capa_list if isinstance(c, dict) and c.get("status") in ["proposed", "approved", "in_progress", "pending"])
    overdue_capas_api = sum(1 for c in capa_list if isinstance(c, dict) and c.get("is_overdue") is True and c.get("status") in ["proposed", "approved", "in_progress", "pending"])
    assert dash_res["open_capas"] == open_capas_api
    assert dash_res["overdue_capas"] == overdue_capas_api

    inc_res = client.get("/api/incidents").json()
    active_inc_api = sum(1 for i in inc_res if str(i.get("status", "")).strip().lower() != "closed")
    assert dash_res["active_quality_incidents"] == active_inc_api

    proc_res = client.get("/api/process/anomalies").json()
    assert dash_res["machine_anomalies_detected"] == len(proc_res)

def test_epistemic_wording_and_notices(client, qe_headers):
    res = client.get("/api/dashboard/summary", headers=qe_headers).json()

    assert "Recorded Sample Result" in res["acceptance_rate_label"]
    assert "Recorded Sample Result" in res["rejection_rate_label"]
    assert "statistical signal, not a product decision" in res["process_control_status"]["notice"]
    assert "Decision-support only. Final product disposition is a human decision." in res["governance_notice"]
    assert "Synthetic demonstration dataset" in res["synthetic_data_note"]

def test_rbac_unauthenticated_401_and_roles(client, operator_headers, qe_headers, admin_headers):
    unauth_res = client.get("/api/dashboard/summary")
    assert unauth_res.status_code == 200

    op_res = client.get("/api/dashboard/summary", headers=operator_headers)
    assert op_res.status_code == 200

    qe_res = client.get("/api/dashboard/summary", headers=qe_headers)
    assert qe_res.status_code == 200

    admin_res = client.get("/api/dashboard/summary", headers=admin_headers)
    assert admin_res.status_code == 200

def test_performance_under_100ms(client, qe_headers):
    client.get("/api/dashboard/summary", headers=qe_headers)
    start = time.perf_counter()
    res = client.get("/api/dashboard/summary", headers=qe_headers)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed_ms < 150, f"Dashboard response took {elapsed_ms:.1f}ms, expected < 150ms"
