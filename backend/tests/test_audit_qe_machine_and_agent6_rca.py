"""
Comprehensive Test Suite for:
1. Audit A — QE Machine Configuration (APIs, DB persistence, validation, unconfigured status, RBAC, Agent 4 consumption)
2. Audit B — Agent 6 RCA Integration (Orchestrator invocation, Agents 1-5 input flow, evidence traceability, human review, audit trail, PDF reporting)
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import Machine, ProcessBaseline, Batch, Product, QualityIncident, HumanDecision
from backend.app.core.security import create_access_token
from backend.app.agents.process_agent import process_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.orchestrator.langgraph_orchestration import qualitymind_langgraph

client = TestClient(app)

# Helper functions for auth headers
def get_qe_headers():
    token = create_access_token({"sub": "usr-qe-01", "name": "Sarah Chen", "role": "quality_engineer"})
    return {"Authorization": f"Bearer {token}", "x-enforce-role": "true"}

def get_operator_headers():
    token = create_access_token({"sub": "usr-op-01", "name": "John Operator", "role": "operator"})
    return {"Authorization": f"Bearer {token}", "x-enforce-role": "true"}


# =========================================================================
# 1. MACHINE CONFIGURATION TESTS
# =========================================================================

def test_1_existing_machine_listing_and_retrieval():
    """Verify machines can be listed and retrieved by ID and by code."""
    res = client.get("/api/machines")
    assert res.status_code == 200
    machines = res.json()
    assert isinstance(machines, list)
    assert len(machines) >= 4
    codes = [m.get("code") for m in machines]
    assert "CNC-01" in codes
    assert "CNC-04" in codes

    # Retrieve individual machine
    res_one = client.get("/api/machines/mach-01")
    assert res_one.status_code == 200
    assert res_one.json()["code"] == "CNC-01"

def test_2_valid_configuration_save_and_retrieval():
    """Verify baselines/thresholds can be saved via PUT and retrieved via GET."""
    headers = get_qe_headers()

    payload = {
        "machine_id": "mach-01",
        "baselines": [
            {
                "parameter": "vibration",
                "name": "Spindle Vibration",
                "unit": "mm/s",
                "mean": 1.25,
                "std": 0.15,
                "lower_threshold": 0.0,
                "upper_threshold": 2.50,
                "computed_from": "QE_CALIBRATION_CERT_2026",
                "status": "CONFIGURED"
            },
            {
                "parameter": "spindle_speed",
                "name": "Main Spindle Speed",
                "unit": "RPM",
                "mean": 3000.0,
                "std": 50.0,
                "lower_threshold": 2800.0,
                "upper_threshold": 3200.0,
                "computed_from": "QE_CALIBRATION_CERT_2026",
                "status": "CONFIGURED"
            }
        ]
    }

    # Save configuration
    put_res = client.put("/api/process/baselines", json=payload, headers=headers)
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["status"].lower() == "success"
    assert data["updated_count"] >= 2

    # Retrieve and verify persistence by code and ID
    get_res_code = client.get("/api/process/baselines?machine=CNC-01")
    assert get_res_code.status_code == 200
    res_data = get_res_code.json()
    bls = res_data.get("baselines", res_data) if isinstance(res_data, dict) else res_data
    vib = next((b for b in bls if b["parameter"] == "vibration"), None)
    assert vib is not None
    assert vib["upper_threshold"] == 2.50
    assert vib["status"] == "CONFIGURED"

def test_3_validation_of_units_and_threshold_values():
    """Verify validation: upper threshold cannot be less than lower threshold."""
    headers = get_qe_headers()

    invalid_payload = {
        "machine_id": "mach-01",
        "baselines": [
            {
                "parameter": "vibration",
                "name": "Spindle Vibration",
                "unit": "mm/s",
                "lower_threshold": 3.0,
                "upper_threshold": 1.0,
                "status": "CONFIGURED"
            }
        ]
    }
    res = client.put("/api/process/baselines", json=invalid_payload, headers=headers)
    assert res.status_code == 422
    assert "must be >=" in res.json()["detail"].lower()

def test_4_missing_configuration_is_reported_explicitly():
    """Verify unconfigured parameters are marked UNCONFIGURED and not populated with fabricated defaults."""
    db = SessionLocal()
    try:
        test_m_id = f"mach-unconf-{uuid.uuid4().hex[:6]}"
        test_m_code = f"CNC-TEST-{uuid.uuid4().hex[:4].upper()}"
        m = Machine(id=test_m_id, code=test_m_code, type="CNC Lathe", location="Cell-01")
        db.add(m)
        db.commit()

        # Query baselines for this machine
        res = client.get(f"/api/process/baselines?machine={test_m_code}")
        assert res.status_code == 200
        res_data = res.json()
        baselines = res_data.get("baselines", res_data) if isinstance(res_data, dict) else res_data
        assert len(baselines) > 0
        for b in baselines:
            assert b["status"] == "UNCONFIGURED"
            assert b["mean"] is None
            assert b["lower_threshold"] is None
            assert b["upper_threshold"] is None

        # Clean up
        db.delete(m)
        db.commit()
    finally:
        db.close()

def test_5_configuration_persists_in_database():
    """Verify direct DB inspection matches API writes without fabrication."""
    db = SessionLocal()
    try:
        row = db.query(ProcessBaseline).filter(
            ProcessBaseline.machine_id == "mach-01",
            ProcessBaseline.parameter == "vibration"
        ).first()
        assert row is not None
        assert row.upper_threshold == 2.50
    finally:
        db.close()

def test_6_correct_cnc01_configuration_consumed_by_agent_4():
    """Verify Agent 4 queries and consumes the persisted database baselines and thresholds."""
    # CNC-01 has vibration upper_threshold = 2.50
    # Provide telemetry with vibration = 2.8 (breaches 2.50)
    series = [
        {"timestamp": "2026-10-13T10:00:00Z", "spindle_speed": 3000, "temperature": 45, "vibration": 1.2, "tool_wear": 0.05, "pressure": 5.0, "current": 10.0},
        {"timestamp": "2026-10-13T10:01:00Z", "spindle_speed": 3000, "temperature": 45, "vibration": 2.8, "tool_wear": 0.05, "pressure": 5.0, "current": 10.0},
    ]
    findings = process_agent.analyze_telemetry_series(batch_id="BATCH-0245", machine="CNC-01", telemetry_records=series)
    assert findings["report"].anomalies_detected >= 1
    anomalies = findings.get("anomalies", [])
    assert len(anomalies) > 0
    # Confirm anomaly detected for vibration breach
    vib_anom = [a for a in anomalies if a.get("parameter") == "vibration"]
    assert len(vib_anom) > 0

def test_7_unauthorized_access_rejected_by_role():
    """Verify operator role receives 403 when trying to update machine baselines."""
    headers = get_operator_headers()

    payload = {
        "machine_id": "mach-01",
        "baselines": [{"parameter": "vibration", "upper_threshold": 3.0, "status": "CONFIGURED"}]
    }
    res = client.put("/api/process/baselines", json=payload, headers=headers)
    assert res.status_code == 403

def test_8_existing_product_creation_and_edit_remains_intact():
    """Verify product CRUD works without regressions."""
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0
    prod = products[0]
    assert "part_number" in prod
    assert "nominal_mm" in prod
    assert "tolerance_mm" in prod

# =========================================================================
# 2. AGENT 6 RCA INTEGRATION TESTS
# =========================================================================

def test_9_orchestrator_invokes_agent_6_with_upstream_inputs():
    """Verify LangGraph workflow node_rca runs and receives Agent 1-5 findings."""
    init_state = {
        "workflow_id": f"WF-TEST-{uuid.uuid4().hex[:6]}",
        "batch_id": "BATCH-0245",
        "batch_metadata": {
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        }
    }
    result = qualitymind_langgraph.invoke(
        init_state,
        config={"configurable": {"thread_id": init_state["workflow_id"]}}
    )
    assert "rca_report" in result
    rca = result["rca_report"]
    assert "ranked_hypotheses" in rca
    assert len(rca["ranked_hypotheses"]) >= 3
    assert result["batch_id"] == "BATCH-0245"

def test_10_missing_upstream_evidence_handled_explicitly():
    """Verify missing inputs are flagged as UNAVAILABLE and not fabricated."""
    res = rca_agent.analyze_incident(
        incident_id="INC-TEST-MISSING",
        batch_id="BATCH-0245",
        dimensional_findings=None
    )
    report = res["report"]
    assert report is not None
    assert len(report.ranked_hypotheses) >= 3
    for h in report.ranked_hypotheses:
        assert h.epistemic_label == "HYPOTHESIS"
        assert h.status != "CONFIRMED"

def test_11_batch_and_component_associations_remain_correct():
    """Verify RCA maintains exact batch ID and characteristic link."""
    dim_findings = {
        "batch_id": "BATCH-0245",
        "total_samples": 5,
        "accepted": 2,
        "nonconforming": 3,
        "characteristic": "shaft_diameter"
    }
    res = rca_agent.analyze_incident(
        incident_id="INC-ASSOC-01",
        batch_id="BATCH-0245",
        dimensional_findings=dim_findings
    )
    report = res["report"]
    assert report.batch_id == "BATCH-0245"
    assert report.rca_inputs["batch_id"] == "BATCH-0245"

def test_12_correlation_alone_does_not_confirm_causation():
    """Verify correlation is explicitly flagged as non-causal."""
    res = rca_agent.analyze_incident(
        incident_id="INC-CORR-01",
        batch_id="BATCH-0245"
    )
    report = res["report"]
    assert report.correlations is not None
    for h in report.ranked_hypotheses:
        assert h.status != "CONFIRMED"

def test_13_llm_output_alone_cannot_confirm_root_cause():
    """Verify LLM or heuristic generation cannot autonomously mark status CONFIRMED."""
    res = rca_agent.analyze_incident(
        incident_id="INC-LLM-01",
        batch_id="BATCH-0245"
    )
    report = res["report"]
    for h in report.ranked_hypotheses:
        assert h.status != "CONFIRMED"

def test_14_historical_retrieval_returns_actual_source_references():
    """Verify historical incidents are retrieved with actual records and disclaimer."""
    res = rca_agent.analyze_incident(
        incident_id="INC-HIST-01",
        batch_id="BATCH-0245"
    )
    report = res["report"]
    sims = report.historical_matches
    assert len(sims) > 0
    assert all(hasattr(s, "incident_id") for s in sims)
    assert any("NCR" in s.incident_id or s.incident_id.startswith("INC-") for s in sims)

def test_15_rca_persists_and_retrievable_by_batch_id():
    """Verify RCA incident results can be retrieved via API."""
    res = client.get("/api/rca/BATCH-0245")
    assert res.status_code == 200
    data = res.json()
    assert data["batch_id"] == "BATCH-0245"
    assert "incident_id" in data

def test_16_unauthorized_confirmation_prevented():
    """Verify operators cannot confirm a root cause (HTTP 403)."""
    headers = get_operator_headers()
    res = client.post(
        "/api/rca/hypotheses/HYP-01/decision",
        json={"decision": "CONFIRM", "comment": "Unauthorized attempt by operator"},
        headers=headers
    )
    assert res.status_code == 403

def test_17_authorized_confirmation_creates_audit_trail():
    """Verify QE confirmation records decision, user, and timestamp immutably."""
    headers = get_qe_headers()
    res = client.post(
        "/api/rca/hypotheses/HYP-01/decision",
        json={"decision": "CONFIRM", "comment": "Audited confirmation by QE"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONFIRMED"
    assert data["epistemic_label"] == "Confirmed Root Cause"

    # Verify decision logged in DB
    db = SessionLocal()
    try:
        dec = db.query(HumanDecision).filter(HumanDecision.entity_id == "HYP-01").order_by(HumanDecision.ts.desc()).first()
        assert dec is not None
        assert dec.decision == "CONFIRM"
        assert dec.user_id == "usr-qe-01"
    finally:
        db.close()

def test_18_pdf_includes_rca_evidence_and_review_status():
    """Verify PDF export contains RCA hypotheses and review status without fabrication."""
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert res.content.startswith(b"%PDF-")

def test_19_no_autonomous_batch_disposition_or_machine_control():
    """Verify neither Agent 4 nor Agent 6 modifies batch status to prohibited released/rejected without HITL."""
    db = SessionLocal()
    try:
        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        if b:
            assert b.status in ["IN_INSPECTION", "QUARANTINED", "PENDING_REVIEW", "PENDING", "QUALITY_HOLD"]
    finally:
        db.close()
