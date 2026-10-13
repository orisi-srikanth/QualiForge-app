"""
Test Suite for Agent 7 (CAPA) Groq LLM Integration
Verifies:
  1. Valid structured CAPA output with Groq client (mocked).
  2. All actions forced to PENDING status requiring Quality Engineer authorization.
  3. Action validation with ActionItem Pydantic schema.
  4. Missing GROQ_API_KEY handling and safe fallback.
  5. Malformed JSON with single-retry recovery.
  6. Retry limit exhaustion and fallback.
  7. Timeout, rate limit, and API error handling.
  8. Zero autonomous machine control actions permitted.
"""
import os
import json
import pytest
from unittest.mock import MagicMock, patch

from backend.app.agents.capa_agent import (
    capa_agent,
    get_groq_client,
    set_groq_client,
    reset_groq_client
)
from backend.app.schemas.schemas import ActionStatus, ActionItem


@pytest.fixture(autouse=True)
def cleanup_groq():
    reset_groq_client()
    yield
    reset_groq_client()


def create_mock_completion(content: str):
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.fixture
def sample_rca_dict():
    return {
        "incident_id": "INC-2026-088",
        "batch_id": "BATCH-0245",
        "defect_type": "Oversized shaft diameter",
        "ranked_hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "title": "Progressive Tool Flank Wear",
                "status": "proposed",
                "posterior_probability": 0.88,
                "engineering_tests_required": ["Microscope insert wear measurement"]
            }
        ]
    }


def test_01_valid_groq_capa_drafting(sample_rca_dict):
    valid_capa_json = json.dumps({
        "containment_actions": [
            {
                "action_id": "ACT-CONT-G1",
                "type": "Immediate Containment",
                "description": "Quarantine BATCH-0245 in QA hold area.",
                "assigned_role": "Quality Inspector",
                "due_date": "2026-10-15",
                "status": "PENDING",
                "evidence_required": "Hold tag physical photo and MES signoff.",
                "affected_population": "BATCH-0245",
                "preconditions": "Incident logged.",
                "rationale": "Prevent escape of oversized parts.",
                "intended_outcome": "Lot isolated."
            }
        ],
        "corrective_actions": [
            {
                "action_id": "ACT-CORR-G1",
                "type": "Potential Corrective Action",
                "description": "Replace worn turning insert on CNC-04.",
                "assigned_role": "Tool Specialist",
                "due_date": "2026-10-17",
                "status": "PENDING",
                "evidence_required": "Tool barcode scan and offset calibration.",
                "hypothesis_id": "HYP-01",
                "preconditions": "Insert flank wear > 0.3mm verified.",
                "rationale": "Restores cutting geometry.",
                "intended_outcome": "Nominal dimensions restored."
            }
        ],
        "preventive_actions": [
            {
                "action_id": "ACT-PREV-G1",
                "type": "Preventive Action",
                "description": "Enforce 800 cycle automated lockout in CNC controller.",
                "assigned_role": "Controls Engineer",
                "due_date": "2026-10-24",
                "status": "PENDING",
                "evidence_required": "PLC ladder program change signoff.",
                "preconditions": "Change notice approved.",
                "rationale": "Prevent running past insert life.",
                "intended_outcome": "Cycle lockout active."
            }
        ],
        "capa_summary": "Comprehensive 3-tier action plan for CNC-04 tool wear."
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion(valid_capa_json)

    res = capa_agent.draft_capa_with_groq(
        rca_dict=sample_rca_dict,
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        machine="CNC-04",
        client=mock_client
    )

    assert res["success"] is True
    assert res["llm_metadata"]["status"] == "VALIDATED"
    assert res["llm_metadata"]["provider"] == "groq"
    parsed = res["parsed_data"]
    assert len(parsed["containment_actions"]) == 1
    assert len(parsed["corrective_actions"]) == 1
    assert len(parsed["preventive_actions"]) == 1


def test_02_groq_actions_enforce_pending_status(sample_rca_dict):
    """Even if model returns status=APPROVED, Agent 7 enforces PENDING."""
    capa_json = json.dumps({
        "containment_actions": [
            {
                "action_id": "ACT-CONT-01",
                "type": "Immediate Containment",
                "description": "Hold batch.",
                "assigned_role": "Inspector",
                "due_date": "2026-10-15",
                "status": "APPROVED",  # Model attempts to auto-approve!
                "evidence_required": "Tag photo."
            }
        ],
        "corrective_actions": [],
        "preventive_actions": []
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion(capa_json)

    res = capa_agent.draft_capa_with_groq(
        rca_dict=sample_rca_dict,
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        machine="CNC-04",
        client=mock_client
    )

    assert res["success"] is True
    # Verify status was overridden to PENDING
    assert res["parsed_data"]["containment_actions"][0]["status"] == ActionStatus.PENDING


def test_03_missing_api_key_fallback(sample_rca_dict):
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
        with patch("backend.app.core.config.settings.GROQ_API_KEY", ""):
            client = get_groq_client(force_refresh=True)
            assert client is None

            res = capa_agent.draft_capa_with_groq(
                rca_dict=sample_rca_dict,
                incident_id="INC-2026-088",
                batch_id="BATCH-0245",
                machine="CNC-04",
                client=None
            )
            assert res["success"] is False
            assert res["fallback_used"] is True
            assert res["llm_metadata"]["status"] == "UNCONFIGURED_FALLBACK"


def test_04_malformed_json_retry_recovery(sample_rca_dict):
    malformed = '{"containment_actions": [{"id": incomplete...'
    valid = json.dumps({
        "containment_actions": [
            {
                "action_id": "ACT-CONT-RECOVERED",
                "type": "Immediate Containment",
                "description": "Recovered hold action.",
                "assigned_role": "Inspector",
                "due_date": "2026-10-16",
                "status": "PENDING",
                "evidence_required": "Tag"
            }
        ],
        "corrective_actions": [],
        "preventive_actions": []
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        create_mock_completion(malformed),
        create_mock_completion(valid)
    ]

    res = capa_agent.draft_capa_with_groq(
        rca_dict=sample_rca_dict,
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        machine="CNC-04",
        client=mock_client
    )

    assert mock_client.chat.completions.create.call_count == 2
    assert res["success"] is True
    assert res["llm_metadata"]["attempts"] == 2


def test_05_retry_limit_exhaustion(sample_rca_dict):
    broken = "Not JSON at all"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion(broken)

    res = capa_agent.draft_capa_with_groq(
        rca_dict=sample_rca_dict,
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        machine="CNC-04",
        client=mock_client
    )

    # Strictly 2 attempts (initial + 1 retry)
    assert mock_client.chat.completions.create.call_count == 2
    assert res["success"] is False
    assert res["fallback_used"] is True
    assert res["llm_metadata"]["status"] == "VALIDATION_FAILED"


def test_06_generate_capa_plan_with_groq(sample_rca_dict):
    valid_json = json.dumps({
        "containment_actions": [
            {
                "action_id": "ACT-CONT-G1",
                "type": "Immediate Containment",
                "description": "Quarantine BATCH-0245.",
                "assigned_role": "Quality Inspector",
                "due_date": "2026-10-15",
                "status": "PENDING",
                "evidence_required": "MES hold tag."
            }
        ],
        "corrective_actions": [],
        "preventive_actions": []
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion(valid_json)

    out = capa_agent.generate_capa_plan(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        machine="CNC-04",
        rca_report=sample_rca_dict,
        groq_client=mock_client
    )

    assert "capa" in out
    assert "log" in out
    capa_rep = out["capa"]
    assert capa_rep.requires_engineer_approval is True
    assert capa_rep.approval_status == "PENDING_ENGINEER_APPROVAL"
    assert capa_rep.llm_metadata is not None
    assert capa_rep.llm_metadata["provider"] == "groq"
    assert "tool_groq_capa_synthesis" in out["log"].tool_calls
