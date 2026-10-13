"""
Unit Tests for Phase 1: Foundation, DB Models, Security, and Guardrails
"""
import pytest
from backend.app.db.session import SessionLocal
from backend.app.db.models import User, Product, Machine, InspectionCharacteristic, ProcessBaseline
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token, UserRole
from backend.app.core.guardrails import (
    guardrails, ForbiddenAutonomousAction, EpistemicViolation, EpistemicLabel
)

def test_database_models_seeded():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        assert len(users) >= 3, "Expected at least 3 seeded users"
        
        products = db.query(Product).all()
        assert len(products) >= 3, "Expected at least 3 products"
        
        machines = db.query(Machine).all()
        assert any(m.code == "CNC-04" for m in machines), "CNC-04 machine must exist"
        
        characteristics = db.query(InspectionCharacteristic).all()
        ps_char = next((c for c in characteristics if c.name == "shaft_diameter"), None)
        assert ps_char is not None, "Shaft diameter characteristic must exist"
        assert ps_char.nominal == 50.00
        assert ps_char.lsl == 49.95
        assert ps_char.usl == 50.05
        
        baselines = db.query(ProcessBaseline).all()
        assert len(baselines) >= 8, "Expected 8 process baselines for CNC-04"
    finally:
        db.close()

def test_password_hashing():
    raw_pw = "Engineer123!"
    hashed = hash_password(raw_pw)
    assert hashed != raw_pw
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_token_generation_and_decoding():
    data = {"sub": "usr-qe-01", "role": UserRole.QUALITY_ENGINEER.value, "email": "engineer@precisionaero.com"}
    token = create_access_token(data)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "usr-qe-01"
    assert decoded["role"] == UserRole.QUALITY_ENGINEER.value

def test_guardrails_permitted_actions():
    # Permitted actions should not raise exceptions
    guardrails.validate_action("compute_spec_limits", agent_name="Agent3_Dimensional")
    guardrails.validate_action("detect_sudden_step_change", agent_name="Agent4_Anomaly")
    guardrails.validate_action("formulate_containment_actions", agent_name="Agent7_CAPA")

def test_guardrails_forbidden_actions():
    # Forbidden autonomous actions MUST raise ForbiddenAutonomousAction
    with pytest.raises(ForbiddenAutonomousAction):
        guardrails.validate_action("release_batch", agent_name="Agent7_CAPA")
        
    with pytest.raises(ForbiddenAutonomousAction):
        guardrails.validate_action("modify_cnc_parameter", agent_name="Agent4_Anomaly")

    with pytest.raises(ForbiddenAutonomousAction):
        guardrails.validate_action("stop_machine", agent_name="Agent4_Anomaly")

    with pytest.raises(ForbiddenAutonomousAction):
        guardrails.validate_action("override_engineer_decision", agent_name="Agent8_Critic")

def test_guardrails_epistemic_enforcement():
    # Agents can emit OBSERVED_FACT, MODEL_PREDICTION, STATISTICAL_FINDING, HYPOTHESIS
    assert guardrails.validate_epistemic_label("OBSERVED_FACT", is_human_engineer=False) == EpistemicLabel.OBSERVED_FACT
    assert guardrails.validate_epistemic_label("MODEL_PREDICTION", is_human_engineer=False) == EpistemicLabel.MODEL_PREDICTION
    assert guardrails.validate_epistemic_label("STATISTICAL_FINDING", is_human_engineer=False) == EpistemicLabel.STATISTICAL_FINDING
    assert guardrails.validate_epistemic_label("HYPOTHESIS", is_human_engineer=False) == EpistemicLabel.HYPOTHESIS

    # Non-human agent cannot emit CONFIRMED_ROOT_CAUSE
    with pytest.raises(EpistemicViolation):
        guardrails.validate_epistemic_label("CONFIRMED_ROOT_CAUSE", is_human_engineer=False)

    # Human Quality Engineer CAN emit CONFIRMED_ROOT_CAUSE
    assert guardrails.validate_epistemic_label("CONFIRMED_ROOT_CAUSE", is_human_engineer=True) == EpistemicLabel.CONFIRMED_ROOT_CAUSE
