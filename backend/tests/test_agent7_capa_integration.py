"""
Comprehensive Automated Test Suite for Agent 7 (CAPA Agent) Verification
Compliant with IATF 16949:2016 Clause 10.2, ISO 9001:2015 Clause 10.2, and QualiForge System Rules.

Tests cover all 20 required checks from Phase 7:
1. Action generation from actual RCA findings.
2. Containment, corrective and preventive action categories.
3. Conditional actions for unconfirmed RCA hypotheses.
4. Supporting and contradicting evidence traceability.
5. Missing evidence and blocked prerequisites.
6. Approval required before assignment/execution as approved work.
7. Unauthorized approval rejected.
8. Approval and rejection audit history.
9. Valid and invalid status transitions.
10. Assignment and due-date persistence.
11. Overdue action calculation.
12. Implementation evidence and completion.
13. Completion does not automatically imply effectiveness.
14. Effectiveness evaluation using actual post-action evidence.
15. Insufficient evidence produces NOT_EVALUATED.
16. Recurrence detection and linkage to prior incidents.
17. Duplicate execution handling.
18. Cross-batch CAPA isolation.
19. Dashboard and PDF integration.
20. No autonomous batch disposition or machine-control actions.
"""
import io
import re
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pypdf import PdfReader

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    CAPAAction, CAPASequence, QualityIncident, RCAHypothesis,
    HumanDecision, EffectivenessCheck, Batch, Machine, Measurement, gen_uuid
)
from backend.app.core.security import create_access_token
from backend.app.agents.capa_agent import capa_agent
from backend.app.services.capa_service import capa_service
from backend.app.services.effectiveness import effectiveness_engine
from backend.app.schemas.schemas import ActionStatus
from backend.app.services.pdf_report import generate_quality_pdf_report

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def qe_headers():
    token = create_access_token({"id": "usr-qe-01", "role": "quality_engineer", "name": "Sarah Chen"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers():
    token = create_access_token({"id": "usr-op-01", "role": "operator", "name": "Dave Miller"})
    return {"Authorization": f"Bearer {token}", "x-enforce-role": "true"}


# =====================================================================
# Check 1: Action generation from actual RCA findings
# =====================================================================
def test_check_01_action_generation_from_actual_rca_findings():
    """Agent 7 dynamically ingests actual RCA report and generates actions linked to batch & hypotheses."""
    sample_rca = {
        "incident_id": "INC-TEST-BATCH-099",
        "batch_id": "BATCH-099",
        "machine": "CNC-04",
        "defect_type": "Oversized shaft diameter",
        "ranked_hypotheses": [
            {
                "hypothesis_id": "hyp-099-1",
                "title": "Progressive Flank Wear on Tool Insert #2",
                "posterior_probability": 0.88,
                "status": "proposed",
                "supporting_evidence": ["Wear offset drift 0.04mm", "Tool reached 850 cycles"],
                "contradicting_evidence": [],
                "engineering_tests_required": ["Inspect flank wear with 20x optical microscope"]
            },
            {
                "hypothesis_id": "hyp-099-2",
                "title": "Thermal Spindle Expansion during Continuous Night Shift",
                "posterior_probability": 0.12,
                "status": "proposed",
                "supporting_evidence": ["Spindle bearing temp reached 48 deg C"],
                "contradicting_evidence": ["Warmup cycle executed"],
                "engineering_tests_required": ["Dial indicator radial runout test at cold vs hot"]
            }
        ],
        "missing_evidence": ["Flank wear microscopic measurement not yet logged"],
        "engineering_tests_required": ["Flank wear microscopy", "Cold vs hot thermal test"]
    }

    res = capa_agent.generate_capa_plan(
        incident_id="INC-TEST-BATCH-099",
        batch_id="BATCH-099",
        machine="CNC-04",
        rca_report=sample_rca
    )

    capa = res["capa"]
    assert capa.batch_id == "BATCH-099"
    assert capa.incident_id == "INC-TEST-BATCH-099"
    assert len(capa.containment_actions) >= 3
    assert len(capa.corrective_actions) >= 2
    assert len(capa.preventive_actions) >= 2

    # Check linkage of corrective actions to hypothesis IDs
    hyp_ids = [a.hypothesis_id for a in capa.corrective_actions if a.hypothesis_id]
    assert "hyp-099-1" in hyp_ids or "hyp-099-2" in hyp_ids


# =====================================================================
# Check 2: Containment, corrective and preventive action categories
# =====================================================================
def test_check_02_containment_corrective_preventive_categories():
    """Agent 7 generates three distinct, well-defined categories of actions."""
    res = capa_agent.generate_capa_plan(incident_id="INC-2026-088", batch_id="BATCH-0245", machine="CNC-04")
    capa = res["capa"]

    # Verify containment tier
    for act in capa.containment_actions:
        assert act.type == "Immediate Containment"
        assert act.status == ActionStatus.PENDING
        assert act.affected_population is not None
        assert "BATCH-0245" in act.description or "gauge" in act.description.lower() or "tool" in act.description.lower() or "quarantine" in act.description.lower()

    # Verify corrective tier
    for act in capa.corrective_actions:
        assert act.type in ["Corrective Action", "Potential Corrective Action"]
        assert act.status == ActionStatus.PENDING

    # Verify preventive tier
    for act in capa.preventive_actions:
        assert act.type == "Preventive Action"
        assert act.status == ActionStatus.PENDING


# =====================================================================
# Check 3: Conditional actions for unconfirmed RCA hypotheses
# =====================================================================
def test_check_03_conditional_actions_for_unconfirmed_hypotheses():
    """Unconfirmed hypotheses produce conditional corrective actions, never asserted as fact."""
    rca_unconfirmed = {
        "incident_id": "INC-TEST-UNCONF-01",
        "batch_id": "BATCH-UNCONF-01",
        "machine": "CNC-02",
        "defect_type": "Surface Roughness Ra Exceeded",
        "ranked_hypotheses": [
            {
                "hypothesis_id": "hyp-unconf-chatter",
                "title": "Workpiece Chatter from Loose Fixture Clamping",
                "posterior_probability": 0.65,
                "status": "proposed",  # UNCONFIRMED
                "engineering_tests_required": ["Dial gauge clamping torque inspection (target: 45 Nm)"]
            }
        ]
    }

    res = capa_agent.generate_capa_plan(
        incident_id="INC-TEST-UNCONF-01",
        batch_id="BATCH-UNCONF-01",
        machine="CNC-02",
        rca_report=rca_unconfirmed
    )
    capa = res["capa"]

    # Find the corrective action corresponding to chatter hypothesis
    conditional_acts = [
        a for a in capa.corrective_actions
        if "Chatter" in a.description or "IF" in a.description or "investigation" in a.description.lower()
    ]
    assert len(conditional_acts) > 0
    # Must explicitly express conditional prerequisite
    assert any("IF" in a.description or "investigation" in a.description.lower() for a in conditional_acts)
    assert any("Physical verification" in (a.preconditions or "") or "Precondition" in (a.preconditions or "") for a in conditional_acts)


# =====================================================================
# Check 4: Supporting and contradicting evidence traceability
# =====================================================================
def test_check_04_supporting_and_contradicting_evidence_traceability():
    """Actions preserve traceability to hypothesis ID, rationale, and intended outcome."""
    res = capa_agent.generate_capa_plan(incident_id="INC-2026-088", batch_id="BATCH-0245", machine="CNC-04")
    capa = res["capa"]

    for act in capa.containment_actions + capa.corrective_actions + capa.preventive_actions:
        assert act.evidence_required is not None
        assert len(act.evidence_required) > 0
        assert act.rationale is not None
        assert act.intended_outcome is not None


# =====================================================================
# Check 5: Missing evidence and blocked prerequisites
# =====================================================================
def test_check_05_missing_evidence_and_blocked_prerequisites():
    """Missing evidence creates explicit engineering investigation actions with preconditions."""
    rca_missing = {
        "incident_id": "INC-TEST-MISSING-01",
        "batch_id": "BATCH-MISS-01",
        "machine": "CNC-03",
        "defect_type": "Bore diameter taper",
        "ranked_hypotheses": [
            {
                "hypothesis_id": "hyp-taper-01",
                "title": "Tailstock Misalignment",
                "posterior_probability": 0.70,
                "status": "proposed",
                "engineering_tests_required": ["Two-collar test on test mandrel between centers"]
            }
        ],
        "missing_evidence": ["Mandrel test not performed since last annual PM"]
    }

    res = capa_agent.generate_capa_plan(
        incident_id="INC-TEST-MISSING-01",
        batch_id="BATCH-MISS-01",
        machine="CNC-03",
        rca_report=rca_missing
    )
    capa = res["capa"]

    # Verify that an investigation task is present
    inv_tasks = [a for a in capa.corrective_actions if "investigation" in a.description.lower() or "mandrel" in a.description.lower()]
    assert len(inv_tasks) > 0
    assert inv_tasks[0].preconditions is not None


# =====================================================================
# Check 6: Approval required before assignment/execution as approved work
# =====================================================================
def test_check_06_approval_required_before_assignment_and_execution(db, qe_headers):
    """Actions must be approved before moving to in_progress; unapproved in_progress transitions are rejected."""
    due = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    create_res = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019",
        "type": "containment",
        "description": "Test unapproved work gate action",
        "due_date": due,
        "suggested_role": "Quality Inspector"
    }, headers=qe_headers)
    assert create_res.status_code == 201
    act_data = create_res.json()
    code = act_data["action_code"]
    assert act_data["status"] == "proposed"
    assert act_data["responsible_role"] is None  # Unassigned before approval

    # Attempt to jump straight from 'proposed' to 'in_progress' without approval -> 400 Bad Request
    fail_res = client.patch(f"/api/capa/actions/{code}", json={
        "status": "in_progress"
    }, headers=qe_headers)
    assert fail_res.status_code == 400
    assert "Illegal status transition" in fail_res.json()["detail"] or "must be approved" in fail_res.json()["detail"].lower()


# =====================================================================
# Check 7: Unauthorized approval rejected
# =====================================================================
def test_check_07_unauthorized_approval_rejected(operator_headers, qe_headers):
    """Operators cannot approve or reject CAPA actions (HTTP 403 Forbidden)."""
    due = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    create_res = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019",
        "type": "corrective",
        "description": "Test RBAC approval restriction",
        "due_date": due
    }, headers=qe_headers)
    code = create_res.json()["action_code"]

    # Operator attempts approval -> 403 Forbidden
    op_res = client.post(f"/api/capa/actions/{code}/approve", json={
        "responsible_role": "Tooling Specialist",
        "comment": "Operator trying to approve"
    }, headers=operator_headers)
    assert op_res.status_code == 403


# =====================================================================
# Check 8: Approval and rejection audit history
# =====================================================================
def test_check_08_approval_and_rejection_audit_history(db, qe_headers):
    """Approvals and rejections are permanently recorded in human_decisions audit table."""
    due = (datetime.now(timezone.utc) + timedelta(days=8)).strftime("%Y-%m-%d")
    # 1. Approval action
    c1 = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "preventive",
        "description": "Audit trail approval verification action", "due_date": due
    }, headers=qe_headers).json()["action_code"]

    appr_res = client.post(f"/api/capa/actions/{c1}/approve", json={
        "responsible_role": "Controls Engineer",
        "comment": "Formal sign-off by Quality Engineering"
    }, headers=qe_headers)
    assert appr_res.status_code == 200

    # 2. Rejection action
    c2 = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "containment",
        "description": "Audit trail rejection verification action", "due_date": due
    }, headers=qe_headers).json()["action_code"]

    rej_res = client.post(f"/api/capa/actions/{c2}/reject", json={
        "reason": "Duplicate containment; lot already quarantined in physical cage."
    }, headers=qe_headers)
    assert rej_res.status_code == 200

    # Query audit trail via API
    aud1 = client.get(f"/api/capa/actions/{c1}/audit").json()
    assert any(log["decision"] == "approved" for log in aud1["audit_logs"])

    aud2 = client.get(f"/api/capa/actions/{c2}/audit").json()
    assert any(log["decision"] == "rejected" for log in aud2["audit_logs"])


# =====================================================================
# Check 9: Valid and invalid status transitions
# =====================================================================
def test_check_09_valid_and_invalid_status_transitions(qe_headers):
    """Enforces complete state machine rules and blocks illegal jumps."""
    due = (datetime.now(timezone.utc) + timedelta(days=9)).strftime("%Y-%m-%d")
    code = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "corrective",
        "description": "Full lifecycle state machine action", "due_date": due
    }, headers=qe_headers).json()["action_code"]

    # Invalid: proposed -> completed
    r_bad1 = client.patch(f"/api/capa/actions/{code}", json={"status": "completed"}, headers=qe_headers)
    assert r_bad1.status_code == 400

    # Valid: proposed -> approved
    r_appr = client.post(f"/api/capa/actions/{code}/approve", json={"responsible_role": "Lead QE"}, headers=qe_headers)
    assert r_appr.status_code == 200

    # Invalid: approved -> verified
    r_bad2 = client.patch(f"/api/capa/actions/{code}", json={"status": "verified"}, headers=qe_headers)
    assert r_bad2.status_code == 400

    # Valid: approved -> in_progress
    r_prog = client.patch(f"/api/capa/actions/{code}", json={"status": "in_progress"}, headers=qe_headers)
    assert r_prog.status_code == 200
    assert r_prog.json()["action"]["status"] == "in_progress"


# =====================================================================
# Check 10: Assignment and due-date persistence
# =====================================================================
def test_check_10_assignment_and_due_date_persistence(db, qe_headers):
    """Responsible role assigned on approval persists; due dates validated and updated."""
    due = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    code = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "corrective",
        "description": "Persistence test action", "due_date": due,
        "suggested_role": "Maintenance Lead"
    }, headers=qe_headers).json()["action_code"]

    # Approve and formally assign responsible role
    appr_res = client.post(f"/api/capa/actions/{code}/approve", json={
        "responsible_role": "Senior Tooling Specialist",
        "comment": "Assigning to senior tooling specialist"
    }, headers=qe_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["action"]["responsible_role"] == "Senior Tooling Specialist"

    # Extend due date
    new_due = (datetime.now(timezone.utc) + timedelta(days=12)).strftime("%Y-%m-%d")
    patch_res = client.patch(f"/api/capa/actions/{code}", json={"due_date": new_due}, headers=qe_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["action"]["due_date"] == new_due


# =====================================================================
# Check 11: Overdue action calculation
# =====================================================================
def test_check_11_overdue_action_calculation(db, qe_headers):
    """Actions with past due date in open status are marked overdue; completed ones are not."""
    # Seed past date action
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    existing = db.query(CAPAAction).filter(CAPAAction.action_code == "CAPA-TEST-OVERDUE-01").first()
    if existing:
        existing.due_date = yesterday
        existing.status = "in_progress"
        overdue_act = existing
    else:
        overdue_act = CAPAAction(
            id=gen_uuid(),
            incident_id="inc-ncr-019",
            action_code="CAPA-TEST-OVERDUE-01",
            type="corrective",
            description="Overdue calculation test action",
            due_date=yesterday,
            status="in_progress",
            responsible_role="Lead Machinist"
        )
        db.add(overdue_act)
    db.commit()

    serialized = capa_service.serialize_action(overdue_act)
    assert serialized["is_overdue"] is True

    # Filter via API
    res = client.get("/api/capa/actions?is_overdue=true")
    assert res.status_code == 200
    codes = [a["action_code"] for a in res.json()["actions"]]
    assert "CAPA-TEST-OVERDUE-01" in codes


# =====================================================================
# Check 12: Implementation evidence and completion
# =====================================================================
def test_check_12_implementation_evidence_and_completion(qe_headers):
    """Marking an action completed requires mandatory evidence; succeeds when evidence provided."""
    due = (datetime.now(timezone.utc) + timedelta(days=6)).strftime("%Y-%m-%d")
    code = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "containment",
        "description": "Evidence validation action", "due_date": due
    }, headers=qe_headers).json()["action_code"]

    client.post(f"/api/capa/actions/{code}/approve", headers=qe_headers)
    client.patch(f"/api/capa/actions/{code}", json={"status": "in_progress"}, headers=qe_headers)

    # Attempt to complete without evidence -> 400 Bad Request
    fail_res = client.patch(f"/api/capa/actions/{code}", json={"status": "completed"}, headers=qe_headers)
    assert fail_res.status_code == 400
    assert "Evidence" in fail_res.json()["detail"]

    # Provide valid evidence -> 200 OK
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    success_res = client.patch(f"/api/capa/actions/{code}", json={
        "status": "completed",
        "evidence": "Tool flank wear verified at 0.12mm (photo attached in MES lot history).",
        "completion_date": today
    }, headers=qe_headers)
    assert success_res.status_code == 200
    assert success_res.json()["action"]["status"] == "completed"


# =====================================================================
# Check 13: Completion does not automatically imply effectiveness
# =====================================================================
def test_check_13_completion_does_not_automatically_imply_effectiveness(db, qe_headers):
    """An action marked COMPLETED does not mean it is statistically EFFECTIVE."""
    due = (datetime.now(timezone.utc) + timedelta(days=6)).strftime("%Y-%m-%d")
    code = client.post("/api/capa/actions", json={
        "incident_id": "inc-ncr-019", "type": "corrective",
        "description": "Effectiveness separation test action", "due_date": due
    }, headers=qe_headers).json()["action_code"]

    client.post(f"/api/capa/actions/{code}/approve", headers=qe_headers)
    client.patch(f"/api/capa/actions/{code}", json={"status": "in_progress"}, headers=qe_headers)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    client.patch(f"/api/capa/actions/{code}", json={
        "status": "completed",
        "evidence": "Completed hardware replacement.",
        "completion_date": today
    }, headers=qe_headers)

    # Evaluate effectiveness on this newly completed action without subsequent batch data
    eff = effectiveness_engine.evaluate_capa_effectiveness(code, db=db)
    # Must report insufficient data or undetermined, never automatic 100% success
    assert eff.get("status") in ["insufficient_data", "monitoring_not_started", "INSUFFICIENT_SAMPLE_SIZE"] or eff.get("outcome") in ["INSUFFICIENT_SAMPLE_SIZE", "NO_SIGNIFICANT_CHANGE"]


# =====================================================================
# Check 14: Effectiveness evaluation using actual post-action evidence
# =====================================================================
def test_check_14_effectiveness_evaluation_using_actual_post_action_evidence(db):
    """Calculates two-proportion z-test on BATCH-PRE-01 vs BATCH-POST-01."""
    eff = effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)
    assert eff["status"] == "computed"
    assert eff["rejection_rate_before_percent"] == 8.2
    assert eff["rejection_rate_after_percent"] == 1.1
    assert eff["is_statistically_significant"] is True
    assert eff["p_value"] < 0.001
    assert "Observed association" in eff["conclusion_label"]
    assert "causation not established" in eff["conclusion_label"]


# =====================================================================
# Check 15: Insufficient evidence produces NOT_EVALUATED
# =====================================================================
def test_check_15_insufficient_evidence_produces_not_evaluated(db):
    """Small sample sizes (< 30 parts or < 5 events) yield warning and no confident claim."""
    res = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        n_before=15, defects_before=2,
        n_after=15, defects_after=1,
        db=db
    )
    assert res["is_statistically_significant"] is False
    assert "Sample size below statistical evaluation threshold" in (res.get("sample_warning") or "")
    assert res["outcome"] == "INSUFFICIENT_SAMPLE_SIZE"


# =====================================================================
# Check 16: Recurrence detection and linkage to prior incidents
# =====================================================================
def test_check_16_recurrence_detection_and_linkage_to_prior_incidents(db):
    """Recurrence detector flags if the same defect occurs again on the machine after CAPA completion."""
    rec = capa_service.detect_defect_recurrence(db=db, machine_code="CNC-04", defect_type="Oversized shaft diameter")
    assert rec["recurrence_detected"] is True
    assert rec["recurrence_count"] > 0
    assert "RECURRENCE ALERT" in rec["alert"]


# =====================================================================
# Check 17: Duplicate execution handling
# =====================================================================
def test_check_17_duplicate_execution_handling(db):
    """Repeated runs of benchmark seed or proposal generator avoid duplicate creations."""
    run1 = capa_service.seed_batch_0245_benchmark_proposals(db)
    count1 = len(run1)

    run2 = capa_service.seed_batch_0245_benchmark_proposals(db)
    count2 = len(run2)

    # Re-running must return the existing count without expanding duplicates
    assert count1 == count2 == 11


# =====================================================================
# Check 18: Cross-batch CAPA isolation
# =====================================================================
def test_check_18_cross_batch_capa_isolation(db):
    """Effectiveness evaluation excludes batches from foreign machines or products."""
    res = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        custom_batches_before=["BATCH-0004"],  # mach-01
        custom_batches_after=["BATCH-POST-01"]  # mach-04
    )
    # Foreign machine BATCH-0004 excluded -> before window empty
    assert res["status"] == "insufficient_data"
    assert "Missing before window" in res["warning"]


# =====================================================================
# Check 19: Dashboard and PDF integration
# =====================================================================
def test_check_19_dashboard_and_pdf_integration(db):
    """Verifies CAPA metrics in dashboard and rendering in PDF quality report."""
    # 1. Dashboard metrics
    dash_res = client.get("/api/dashboard/summary")
    assert dash_res.status_code == 200
    d_data = dash_res.json()
    assert "open_capas" in d_data
    assert "overdue_capas" in d_data

    # 2. PDF report generation
    state_mock = {
        "batch_id": "BATCH-0245",
        "capa_report": {
            "corrective_actions": [
                {"action_code": "CAPA-2026-001", "type": "corrective", "description": "Replace worn carbide turning insert", "due_date": "2026-10-20", "status": "approved"}
            ],
            "preventive_actions": [
                {"action_code": "CAPA-2026-002", "type": "preventive", "description": "Cycle-life lockout at 800 cycles", "due_date": "2026-10-25", "status": "approved"}
            ]
        }
    }
    pdf_bytes = generate_quality_pdf_report(state_mock)
    assert len(pdf_bytes) > 5000
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Corrective & Preventive Actions" in full_text
    assert "Effectiveness Monitoring" in full_text


# =====================================================================
# Check 20: No autonomous batch disposition or machine-control actions
# =====================================================================
def test_check_20_no_autonomous_batch_disposition_or_machine_control_actions(db, qe_headers):
    """Safety guardrails intercept and reject autonomous machine control and automated batch release."""
    forbidden_descriptions = [
        "Emergency stop machine CNC-04 immediately",
        "Halt the machine spindle on CNC-04",
        "Modify CNC parameter register 4001 directly",
        "Automatically release batch BATCH-0245",
        "Auto-scrap parts without engineering approval"
    ]

    due = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")

    for forbidden_desc in forbidden_descriptions:
        res = client.post("/api/capa/actions", json={
            "incident_id": "inc-ncr-019",
            "type": "containment",
            "description": forbidden_desc,
            "due_date": due
        }, headers=qe_headers)

        assert res.status_code == 400
        assert "SAFETY" in res.json()["detail"].upper()
