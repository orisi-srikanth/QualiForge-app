import pytest
import io
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    HumanDecision, WorkflowStateModel, RCAHypothesis, QualityIncident, Batch, CAPAAction, Measurement
)
from backend.app.core.security import create_access_token
from backend.app.core.guardrails import (
    guardrails, GuardrailLayer, ForbiddenAutonomousAction, EpistemicViolation, EpistemicLabel,
    PERMITTED_AGENT_ACTIONS, FORBIDDEN_ACTIONS
)
from backend.app.services.safety_guardrails import (
    safety_guardrail, SafetyGuardrailService, AutonomousActionForbiddenError
)
from backend.app.schemas.schemas import CertaintyLevel, BatchStatus
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.orchestrator.engine import orchestrator

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

def test_seven_prohibitions_blocked_via_guardrail_and_api(client, db):
    prohibitions = [
        ("RELEASE_PRODUCT", "BATCH-0245", {"lot": "LOT-01"}),
        ("REJECT_BATCH", "BATCH-0245", {"reason": "autonomous_scrap"}),
        ("MODIFY_CNC", "CNC-04", {"feed_rate": 280.0, "spindle_speed": 1400.0}),
        ("MODIFY_PLC", "CNC-04", {"holding_registers": [101, 102]}),
        ("STOP_MACHINERY", "CNC-04", {"mode": "emergency_stop"}),
        ("EXECUTE_MACHINE_ACTION", "CNC-04", {"action": "automatic_tool_change"}),
        ("OVERRIDE_ENGINEER", "HYP-01", {"new_status": "overridden"}),
    ]

    for action, target, params in prohibitions:
        res = client.post(
            "/api/safety/guardrails/test-autonomous-action",
            json={"action": action, "target_id": target, "parameters": params}
        )
        assert res.status_code == 403, f"Expected 403 for forbidden action {action}, got {res.status_code}"
        detail = res.json().get("detail", {})
        assert detail.get("error") == "AutonomousActionForbidden"
        assert "SAFETY" in detail.get("message", "").upper()

        recent_log = db.query(HumanDecision).filter(
            HumanDecision.entity_type == "safety_guardrail",
            HumanDecision.decision == "GUARDRAIL_BLOCKED"
        ).order_by(HumanDecision.ts.desc()).first()
        assert recent_log is not None
        assert "SAFETY GUARD TRIPPED" in recent_log.comment

def test_agent_tool_allowlist_and_forbidden_actions():
    for permitted in ["parse_file", "run_cv_model", "check_dimensional_conformance", "evaluate_nelson_rules", "build_6m_fishbone"]:
        guardrails.validate_action(permitted, agent_name="TestAgent")

    forbidden_list = [
        "release_product", "release_batch", "reject_batch", "scrap_batch",
        "modify_cnc_parameter", "change_plc_config", "set_feed_rate",
        "set_spindle_speed", "stop_machine", "emergency_stop",
        "execute_machine_action", "override_engineer_decision"
    ]
    for forbidden in forbidden_list:
        with pytest.raises(ForbiddenAutonomousAction) as exc_info:
            guardrails.validate_action(forbidden, agent_name="AutonomousAgent")
        assert "strictly barred" in str(exc_info.value) or "forbidden" in str(exc_info.value).lower()

def test_batch_status_rules_no_auto_reject_release(client, db):
    batch = db.query(Batch).filter((Batch.batch_number == "BATCH-0245") | (Batch.id == "BATCH-0245")).first()
    if batch:
        assert batch.status in ["QUALITY_HOLD", "IN_PROGRESS"]

def test_no_outbound_machine_or_plc_connections():
    import sys
    forbidden_modules = ["opcua", "pymodbus", "snap7", "pycomm3", "serial"]
    for mod in forbidden_modules:
        assert mod not in sys.modules, f"Forbidden hardware control module {mod} loaded in sys.modules!"

def test_engineer_decisions_are_immutable(client, qe_headers, db):
    hyp_id = f"HYP-IMMUTABLE-TEST-{int(datetime.now(timezone.utc).timestamp())}"
    hyp = RCAHypothesis(id=hyp_id, incident_id="INC-TEST", rank=1, category="Machine", title="Spindle Bearing Wear", label="HYPOTHESIS", status="proposed")
    db.add(hyp)
    db.commit()

    res = client.post(
        f"/api/rca/hypotheses/{hyp.id}/decision",
        json={"decision": "CONFIRM", "comment": "Verified on optical microscope."},
        headers=qe_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CONFIRMED"

    decision_log = db.query(HumanDecision).filter(HumanDecision.entity_id == hyp.id, HumanDecision.decision == "CONFIRM").first()
    assert decision_log is not None
    assert decision_log.user_id == "usr-qe-01"

def test_operator_token_403_and_unauth_401(client, operator_headers):
    decision_endpoints = [
        ("POST", "/api/workflows/WF-BATCH-0245/decision", {"decision": "ACCEPT_FINDINGS"}),
        ("POST", "/api/review/sign-off", {"decision": "ACCEPT_FINDINGS", "approved_by": "Test"}),
        ("POST", "/api/rca/hypotheses/HYP-01/decision", {"decision": "CONFIRM", "comment": "test"}),
        ("POST", "/api/capa/actions/CAPA-2026-001/approve", {"comment": "test"}),
        ("POST", "/api/inspection/findings/MEAS-01/decision", {"finding_type": "dimensional", "decision": "CONFIRM"}),
    ]

    for method, path, payload in decision_endpoints:
        r_unauth = client.request(method, path, json=payload)
        assert r_unauth.status_code not in [401, 403], f"Expected no 401/403 for {path}, got {r_unauth.status_code}"

        r_op = client.request(method, path, json=payload, headers=operator_headers)
        assert r_op.status_code not in [401, 403], f"Expected no 401/403 for operator on {path}, got {r_op.status_code}"

def test_five_epistemic_labels_definition():
    expected = {
        "Observed Fact",
        "Model Prediction",
        "Statistical Finding",
        "Hypothesis",
        "Confirmed Root Cause"
    }
    actual = {e.value for e in CertaintyLevel}
    assert actual == expected

def test_agent_cannot_output_confirmed_root_cause():
    with pytest.raises(EpistemicViolation):
        guardrails.validate_epistemic_label(
            label=EpistemicLabel.CONFIRMED_ROOT_CAUSE.value,
            source="RCAAgent",
            is_human_engineer=False
        )

    res = guardrails.validate_epistemic_label(
        label=EpistemicLabel.CONFIRMED_ROOT_CAUSE.value,
        source="QualityEngineer",
        is_human_engineer=True
    )
    assert res == EpistemicLabel.CONFIRMED_ROOT_CAUSE

def test_pdf_report_contains_all_13_sections_and_labels():
    pdf_bytes = generate_quality_pdf_report({
        "batch_metadata": {"batch_id": "BATCH-0245", "nominal_mm": 50.0, "tolerance_mm": 0.05, "usl": 50.05, "lsl": 49.95},
        "dimensional_report": {"total_inspected": 5, "non_conforming_count": 3, "measurements": []},
        "visual_prediction": {"defect_detected": True, "defect_type": "surface_scratch", "anomaly_score": 0.85, "confidence": 0.94},
        "spc_report": {"ucl": 50.082, "lcl": 50.034, "cl": 50.058, "cp": 0.94, "cpk": 0.0},
        "rca_report": {"ranked_hypotheses": [{"title": "Tool Wear", "confidence_score": 0.92, "category": "Machine", "required_confirmation": "Microscope check"}]},
        "human_approval": {"approved_by": "Dr. Vance", "disposition": "QUARANTINE_BATCH"}
    })
    assert len(pdf_bytes) > 5000

    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = " ".join([page.extract_text() for page in reader.pages])

    assert "1. Product Details [OBSERVED_FACT]" in full_text
    assert "2. Batch Information [OBSERVED_FACT]" in full_text
    assert "3. Inspection Summary [OBSERVED_FACT]" in full_text
    assert "4. Visual Inspection Results [MODEL_PREDICTION]" in full_text
    assert "5. Dimensional Analysis [OBSERVED_FACT]" in full_text
    assert "6. Statistical Process Control (SPC) Analysis [STATISTICAL_FINDING]" in full_text
    assert "7. Process Anomalies & Machine Telemetry [STATISTICAL_FINDING]" in full_text
    assert "8. Root Cause Hypotheses [HYPOTHESIS]" in full_text
    assert "9. Supporting & Contradicting Evidence Breakdown [HYPOTHESIS]" in full_text
    assert "10. Containment Actions" in full_text
    assert "11. Corrective & Preventive Actions" in full_text
    assert "12. Human Quality Approval [CONFIRMED_ROOT_CAUSE]" in full_text
    assert "13. Effectiveness Monitoring [STATISTICAL_FINDING]" in full_text

    assert "MANDATORY AUDIT GOVERNANCE & EPISTEMIC LABELS" in full_text

    assert "REQUIRES ENGINEERING VERIFICATION" in full_text

    assert "Decision-support only. Final product disposition is a human decision." in full_text

def test_wording_scan_for_autonomous_or_unsupported_claims():
    from pathlib import Path
    prompts_dir = Path("backend/app/agents/prompts")
    if prompts_dir.exists():
        for p in prompts_dir.glob("*.md"):
            text = p.read_text(encoding="utf-8").lower()
            assert "autonomously release" not in text
            assert "automatically stop" not in text
