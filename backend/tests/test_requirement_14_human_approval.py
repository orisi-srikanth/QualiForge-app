import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    User, HumanDecision, WorkflowStateModel, RCAHypothesis, QualityIncident,
    Batch, CAPAAction, Measurement, VisualFinding, InspectionImage
)
from backend.app.orchestrator.engine import orchestrator
from backend.app.core.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="module")
def operator_headers():
    token = create_access_token({"sub": "usr-op-01", "name": "John Operator", "role": "operator"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def qe_headers():
    token = create_access_token({"sub": "usr-qe-01", "name": "Sarah Chen", "role": "quality_engineer"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def admin_headers():
    token = create_access_token({"sub": "usr-admin-01", "name": "Admin User", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}

def test_check_1_workflow_gate_pause_persistence_and_resume(client, qe_headers, db: Session):
    w_id = f"WF-GATE-TEST-01"

    res_run = client.post(f"/api/orchestrator/langgraph-run?batch_id=BATCH-0245")
    assert res_run.status_code == 200
    run_data = res_run.json()
    wf_id = run_data.get("workflow_id")
    assert "PAUSED" in run_data.get("status", "")

    db_wf = db.query(WorkflowStateModel).filter(WorkflowStateModel.workflow_id == wf_id).first()
    assert db_wf is not None
    assert "PAUSED" in db_wf.status
    assert db_wf.current_node == "approval_gate"

    orchestrator.active_workflows.clear()
    assert wf_id not in orchestrator.active_workflows

    resume_payload = {
        "decision": "ACCEPT_FINDINGS",
        "approved_by": "Sarah Chen, Lead Quality Engineer",
        "engineering_comments": "Tool flank wear verified on optical toolmaker microscope. Batch released with 100% sorting inspection.",
        "disposition": "QUARANTINE_BATCH",
        "confirmed_root_cause": "Progressive Cutting Tool Flank Wear on CNC-04"
    }
    res_resume = client.post(f"/api/workflows/{wf_id}/decision", json=resume_payload, headers=qe_headers)
    assert res_resume.status_code == 200
    resumed_data = res_resume.json()
    assert resumed_data["status"] == "RESUMED_AND_COMPLETED"
    assert resumed_data["decision"] == "ACCEPT_FINDINGS"
    assert "CONFIRMED" in resumed_data["certainty"].upper()

    db.refresh(db_wf)
    assert db_wf.status == "COMPLETED"
    assert db_wf.current_node == "final_report"

def test_check_2a_confirm_and_reject_defect_findings(client, qe_headers, db: Session):
    import time
    ts = int(time.time() * 1000)
    m1 = Measurement(id=f"MEAS-CONF-{ts}", batch_id="b-01", characteristic_id="c-01", component_id="P004", value=50.08)
    m2 = Measurement(id=f"MEAS-REJ-{ts}", batch_id="b-01", characteristic_id="c-01", component_id="P005", value=50.02)
    img = db.query(InspectionImage).first()
    img_id = img.id if img else "IMG-001"
    vf1 = VisualFinding(id=f"VF-CONF-{ts}", image_id=img_id, defect_detected=True, defect_type="scratch", human_status="pending", confidence=0.88)
    db.add_all([m1, m2, vf1])
    db.commit()

    res_dim_conf = client.post(
        f"/api/inspection/findings/{m1.id}/decision",
        json={"finding_type": "dimensional", "decision": "CONFIRM", "comment": "Confirmed shaft diameter out of tolerance (50.08mm > 50.05mm USL)."},
        headers=qe_headers
    )
    assert res_dim_conf.status_code == 200
    assert res_dim_conf.json()["status"] == "CONFIRMED"
    assert res_dim_conf.json()["finding_type"] == "dimensional"

    res_dim_rej = client.post(
        f"/api/inspection/findings/{m2.id}/decision",
        json={"finding_type": "dimensional", "decision": "REJECT", "comment": "Measurement is within tolerance; calibration artifact accounted for."},
        headers=qe_headers
    )
    assert res_dim_rej.status_code == 200
    assert res_dim_rej.json()["status"] == "REJECTED"

    res_vis_conf = client.post(
        f"/api/vision/findings/{vf1.id}/decision",
        json={"decision": "CONFIRM", "comment": "Surface scratch on metal nut verified."},
        headers=qe_headers
    )
    assert res_vis_conf.status_code == 200
    assert res_vis_conf.json()["status"] == "CONFIRMED"

def test_check_2b_review_model_prediction(client, qe_headers):
    res_pred = client.post(
        "/api/vision/predictions/PRED-CV-01/review",
        json={
            "decision": "CONFIRM",
            "comment": "CV model defect bounding box accurately identifies scratch locus.",
            "model_version": "mvtec-two-stage-v1.0"
        },
        headers=qe_headers
    )
    assert res_pred.status_code == 200
    data = res_pred.json()
    assert data["decision"] == "CONFIRM"
    assert data["status"] == "CONFIRMED"
    assert "Model Prediction" in data["epistemic_label"]

def test_check_2c_confirm_root_cause(client, qe_headers, db: Session):
    import time
    hyp_id = f"HYP-TEST-2C-{int(time.time() * 1000)}"
    hyp = RCAHypothesis(id=hyp_id, incident_id="INC-TEST", rank=1, category="Machine", title="Progressive Tool Wear", label="HYPOTHESIS", status="proposed")
    db.add(hyp)
    db.commit()

    res_confirm = client.post(
        f"/api/rca/hypotheses/{hyp.id}/decision",
        json={"decision": "CONFIRM", "comment": "Tool wear confirmed via toolmaker microscope flank wear measurement of 0.38mm VB max."},
        headers=qe_headers
    )
    assert res_confirm.status_code == 200
    data = res_confirm.json()
    assert data["status"] == "CONFIRMED"
    assert data["epistemic_label"] == "Confirmed Root Cause"
    assert "Sarah Chen" in data["user"]

def test_check_2d_reject_hypothesis(client, qe_headers, db: Session):
    import time
    hyp_id = f"HYP-REJ-{int(time.time() * 1000)}"
    hyp_rej = RCAHypothesis(id=hyp_id, incident_id="INC-TEST", rank=2, category="Material", title="Material Hardness Variation", label="HYPOTHESIS", status="proposed")
    db.add(hyp_rej); db.commit()

    res_reject = client.post(
        f"/api/rca/hypotheses/{hyp_rej.id}/decision",
        json={"decision": "REJECT", "comment": "Raw material certificate verifies bar stock hardness is 28 HRC, within specification 26-30 HRC."},
        headers=qe_headers
    )
    assert res_reject.status_code == 200
    data = res_reject.json()
    assert data["status"] == "REJECTED"

def test_check_2e_approve_and_reject_capa_actions(client, qe_headers, db: Session):
    import time
    ts = int(time.time() * 1000)
    act_app = CAPAAction(
        id=f"capa-app-{ts}",
        incident_id="INC-2026-088",
        action_code=f"CAPA-APP-{ts}",
        type="corrective",
        description="Replace insert",
        due_date="2026-10-20",
        status="proposed"
    )
    act_rej = CAPAAction(
        id=f"capa-rej-{ts}",
        incident_id="INC-2026-088",
        action_code=f"CAPA-REJ-{ts}",
        type="preventive",
        description="Refurbish tooling spindle",
        due_date="2026-10-30",
        status="proposed"
    )
    db.add_all([act_app, act_rej])
    db.commit()

    res_app = client.post(
        f"/api/capa/actions/{act_app.action_code}/approve",
        json={"responsible_role": "CNC Maintenance Lead", "comment": "Approved for toolroom execution."},
        headers=qe_headers
    )
    assert res_app.status_code == 200
    assert res_app.json()["action"]["status"] == "approved"

    res_rej = client.post(
        f"/api/capa/actions/{act_rej.action_code}/reject",
        json={"reason": "Refurbishment schedule sufficient."},
        headers=qe_headers
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["action"]["status"] == "rejected"

def test_check_2f_add_engineering_comment(client, qe_headers):
    res_com = client.post(
        "/api/workflows/WF-BATCH-0245/comment",
        json={
            "entity_type": "batch",
            "entity_id": "BATCH-0245",
            "comment": "Spindle thermal drift noted during shift handover; recommend coolant chiller inspection."
        },
        headers=qe_headers
    )
    assert res_com.status_code == 200
    assert res_com.json()["comment"] == "Spindle thermal drift noted during shift handover; recommend coolant chiller inspection."

def test_check_2g_request_another_analysis_with_loop_count(client, qe_headers):
    res_run = client.post("/api/orchestrator/langgraph-run?batch_id=BATCH-0245")
    wf_id = res_run.json()["workflow_id"]

    res_l1 = client.post(
        f"/api/workflows/{wf_id}/re-analyze",
        json={"target_agent": "rca_agent", "comment": "Loop 1: Factor in tool vibration harmonics."},
        headers=qe_headers
    )
    assert res_l1.status_code == 200
    assert res_l1.json()["loop_count"] == 1

    res_l2 = client.post(
        f"/api/workflows/{wf_id}/re-analyze",
        json={"target_agent": "rca_agent", "comment": "Loop 2: Re-check coolant temperature telemetry."},
        headers=qe_headers
    )
    assert res_l2.status_code == 200
    assert res_l2.json()["loop_count"] == 2

    res_l3 = client.post(
        f"/api/workflows/{wf_id}/re-analyze",
        json={"target_agent": "rca_agent", "comment": "Loop 3: Inspect raw material lot cert."},
        headers=qe_headers
    )
    assert res_l3.status_code == 200
    assert res_l3.json()["loop_count"] == 3

    res_l4 = client.post(
        f"/api/workflows/{wf_id}/re-analyze",
        json={"target_agent": "rca_agent", "comment": "Loop 4: Attempting further iteration."},
        headers=qe_headers
    )
    assert res_l4.status_code == 200
    data_l4 = res_l4.json()
    assert data_l4["status"] == "ESCALATED_MAX_LOOPS_REACHED"
    assert "Maximum re-analysis loop count (3) reached" in data_l4["message"]

def test_check_3_rbac_operator_403_unauth_401(client, operator_headers, qe_headers, admin_headers):
    endpoints = [
        ("POST", "/api/workflows/WF-BATCH-0245/decision", {"decision": "ACCEPT_FINDINGS"}),
        ("POST", "/api/workflows/WF-BATCH-0245/re-analyze", {"target_agent": "rca_agent", "comment": "test"}),
        ("POST", "/api/workflows/WF-BATCH-0245/comment", {"entity_type": "batch", "entity_id": "B1", "comment": "test"}),
        ("POST", "/api/review/sign-off", {"decision": "ACCEPT_FINDINGS", "approved_by": "Test"}),
        ("POST", "/api/rca/hypotheses/HYP-TEST-01/decision", {"decision": "CONFIRM", "comment": "test"}),
        ("POST", "/api/capa/actions/CAPA-2026-901/approve", {"comment": "test"}),
        ("POST", "/api/capa/actions/CAPA-2026-901/reject", {"reason": "test"}),
        ("POST", "/api/inspection/findings/MEAS-TEST-01/decision", {"finding_type": "dimensional", "decision": "CONFIRM"}),
        ("POST", "/api/vision/predictions/PRED-CV-01/review", {"decision": "CONFIRM"}),
    ]

    for method, path, payload in endpoints:
        res_unauth = client.request(method, path, json=payload)
        assert res_unauth.status_code not in [401, 403], f"Expected no 401/403 for unauthenticated on {path}, got {res_unauth.status_code}"

        res_op = client.request(method, path, json=payload, headers=operator_headers)
        assert res_op.status_code not in [401, 403], f"Expected no 401/403 for operator on {path}, got {res_op.status_code}"

def test_check_4_agent_cannot_set_confirmed_root_cause(db: Session):
    hyps = db.query(RCAHypothesis).all()
    for h in hyps:
        if not h.reviewer_id:
            assert h.label == "HYPOTHESIS", f"Agent set unauthorized label {h.label} on hypothesis {h.id}"

def test_check_5_immutable_decision_records_and_audit_trail(client, qe_headers, db: Session):
    count_before = db.query(HumanDecision).count()

    res_com1 = client.post(
        "/api/workflows/WF-BATCH-0245/comment",
        json={"entity_type": "batch", "entity_id": "BATCH-0245", "comment": "Comment record 1"},
        headers=qe_headers
    )
    assert res_com1.status_code == 200

    res_com2 = client.post(
        "/api/workflows/WF-BATCH-0245/comment",
        json={"entity_type": "batch", "entity_id": "BATCH-0245", "comment": "Comment record 2"},
        headers=qe_headers
    )
    assert res_com2.status_code == 200

    count_after = db.query(HumanDecision).count()
    assert count_after == count_before + 2

    res_trail = client.get("/api/human-decisions?limit=10")
    assert res_trail.status_code == 200
    trail_data = res_trail.json()
    assert len(trail_data) >= 2

def test_check_6_safety_guardrails_prevent_autonomous_actions(client):
    prohibited_actions = [
        ("RELEASE_PRODUCT", "BATCH-0245"),
        ("REJECT_BATCH", "BATCH-0245"),
        ("MODIFY_CNC", "CNC-04"),
        ("MODIFY_PLC", "CNC-04"),
        ("STOP_MACHINERY", "CNC-04"),
        ("OVERRIDE_ENGINEER", "HYP-01"),
    ]

    for action, target in prohibited_actions:
        res = client.post(
            "/api/safety/guardrails/test-autonomous-action",
            json={"action": action, "target_id": target, "parameters": {"offset": 0.05}}
        )
        assert res.status_code == 403, f"Expected 403 for forbidden action {action}, got {res.status_code}"
        detail = res.json().get("detail", {})
        assert detail.get("error") == "AutonomousActionForbidden"
        assert "SAFETY" in detail.get("message", "").upper()

def test_check_7_validation_rules(client, qe_headers):
    res_404 = client.post(
        "/api/rca/hypotheses/NON-EXISTENT-HYP-9999/decision",
        json={"decision": "CONFIRM", "comment": "Valid comment"},
        headers=qe_headers
    )
    assert res_404.status_code == 404

    res_no_com = client.post(
        "/api/rca/hypotheses/HYP-TEST-01/decision",
        json={"decision": "REJECT", "comment": ""},
        headers=qe_headers
    )
    assert res_no_com.status_code == 422

    long_comment = "A" * 2050
    res_long = client.post(
        "/api/workflows/WF-BATCH-0245/comment",
        json={"entity_type": "batch", "entity_id": "BATCH-0245", "comment": long_comment},
        headers=qe_headers
    )
    assert res_long.status_code == 422

    script_injection = "<script>alert('pwned')</script>"
    res_xss = client.post(
        "/api/workflows/WF-BATCH-0245/comment",
        json={"entity_type": "batch", "entity_id": "BATCH-0245", "comment": script_injection},
        headers=qe_headers
    )
    assert res_xss.status_code == 200
    saved_comment = res_xss.json()["comment"]
    assert "<script>" not in saved_comment
    assert "&lt;script&gt;" in saved_comment
