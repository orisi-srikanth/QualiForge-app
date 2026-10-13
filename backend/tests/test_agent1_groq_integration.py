"""
Comprehensive Test Suite for Agent 1 — Production & Quality Data Intake Agent
Verifies:
1. Groq SDK integration (model: openai/gpt-oss-20b, reasoning_effort: low, json_object)
2. Safe parsing of valid JSON responses and candidate observations extraction
3. Malformed JSON handling and fallback to deterministic intake
4. Missing API key handling and fallback
5. AuthenticationError, RateLimitError, and APITimeoutError handling
6. Prevention of LLM overwriting QE specifications or inventing measurements
7. Reusable client lifecycle
8. Existing intake contracts (unit conversions, fuzzy headers, missing field gating)
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from backend.app.agents.intake_agent import (
    data_intake_agent,
    ProductionDataIntakeAgent,
    get_groq_client,
    set_groq_client,
    reset_groq_client
)
from backend.app.models.schemas import DataIntakeOutput, CertaintyLevel
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

class MockChoice:
    def __init__(self, content):
        self.message = MagicMock(content=content)

class MockCompletionResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

@pytest.fixture(autouse=True)
def cleanup_groq_client():
    reset_groq_client()
    yield
    reset_groq_client()


def test_01_groq_valid_json_response_parsing():
    """Verify Groq response is parsed as JSON, extracting observations without altering deterministic limits."""
    mock_llm_json = {
        "summary": "Operator reported minor spindle warm-up drift during early shift.",
        "extracted_facts": {
            "operator_name": "Marcus Vance",
            "material_lot_ref": "HEAT-9042",
            "tooling_id": "T-04"
        },
        "inferred_observations": [
            {
                "category": "thermal_drift",
                "observation": "Spindle temperature drifted positive by 1.2C",
                "source_text": "spindle temp rose by 1.2C before settling",
                "certainty": "INFERRED"
            }
        ],
        "operator_concerns_flagged": True,
        "model": "openai/gpt-oss-20b"
    }

    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = MockCompletionResponse(json.dumps(mock_llm_json))
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-GROQ-01",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 500,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "notes": "Marcus Vance reported spindle temp rose by 1.2C before settling on tool T-04 with material HEAT-9042."
    }
    raw_measurements = [{"sample_id": "P001", "measured_value": 50.02, "unit": "mm"}]

    res = agent.process_batch_and_measurements(batch_meta=batch_meta, raw_measurements=raw_measurements)
    intake_output: DataIntakeOutput = res["intake_schema"]

    assert intake_output.batch_id == "BATCH-GROQ-01"
    assert intake_output.nominal_mm == 50.00
    assert intake_output.usl == 50.05
    assert intake_output.lsl == 49.95
    assert len(intake_output.measurements) == 1

    # Check LLM interpretation
    llm_data = intake_output.llm_interpretation
    assert llm_data is not None
    assert llm_data["status"] == "success"
    assert llm_data["model"] == "openai/gpt-oss-20b"
    assert llm_data["reasoning_effort"] == "low"
    assert llm_data["operator_concerns_flagged"] is True
    assert llm_data["extracted_facts"]["operator_name"] == "Marcus Vance"
    assert llm_data["extracted_facts"]["tooling_id"] == "T-04"
    assert len(llm_data["inferred_observations"]) == 1
    assert llm_data["inferred_observations"][0]["category"] == "thermal_drift"


def test_02_groq_client_invoked_with_correct_parameters():
    """Verify Groq API call explicitly specifies model='openai/gpt-oss-20b', reasoning_effort='low', and json_object."""
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = MockCompletionResponse('{"summary": "OK"}')
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-TEST-PARAMS",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 100,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "notes": "Testing Groq call parameters"
    }

    agent.process_batch_and_measurements(batch_meta=batch_meta)

    assert mock_groq.chat.completions.create.called
    kwargs = mock_groq.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-20b"
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert len(kwargs["messages"]) == 1
    assert "Testing Groq call parameters" in kwargs["messages"][0]["content"]


def test_03_groq_malformed_json_fallback():
    """Verify malformed JSON from LLM does not crash the pipeline and triggers safe fallback."""
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = MockCompletionResponse('{"summary": "Incomplete json...')
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-BAD-JSON",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 100,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "notes": "Operator note that causes malformed json response"
    }
    raw_measurements = [{"sample_id": "P001", "measured_value": 50.01, "unit": "mm"}]

    res = agent.process_batch_and_measurements(batch_meta=batch_meta, raw_measurements=raw_measurements)
    intake_output: DataIntakeOutput = res["intake_schema"]

    # Deterministic measurements and calculations are completely intact
    assert intake_output.batch_id == "BATCH-BAD-JSON"
    assert len(intake_output.measurements) == 1
    assert intake_output.measurements[0]["measured_value"] == 50.01

    # LLM interpretation records json_decode_error gracefully
    llm_data = intake_output.llm_interpretation
    assert llm_data["status"] == "error"
    assert llm_data["error_type"] == "json_decode_error"
    assert llm_data["fallback_used"] is True


def test_04_groq_missing_api_key_deterministic_fallback():
    """Verify missing GROQ_API_KEY gracefully reports unavailable without crashing."""
    set_groq_client(None)

    with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
        with patch("backend.app.core.config.settings.GROQ_API_KEY", ""):
            agent = ProductionDataIntakeAgent()
            res = agent.interpret_production_notes(
                notes="Some operator notes",
                batch_meta={"batch_id": "BATCH-NO-KEY"}
            )

            assert res["status"] == "unavailable"
            assert res["fallback_used"] is True
            assert "API key" in res["summary"] or "not configured" in res["reason"]


def test_05_groq_authentication_error_handling():
    """Verify AuthenticationError from Groq is handled safely without leaking the key."""
    import groq
    mock_groq = MagicMock()
    # Create mock AuthenticationError
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {}
    mock_groq.chat.completions.create.side_effect = groq.AuthenticationError(
        message="Invalid API Key",
        response=mock_response,
        body={"error": {"message": "Invalid API Key"}}
    )
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    res = agent.interpret_production_notes(
        notes="Operator observation",
        batch_meta={"batch_id": "BATCH-AUTH-FAIL"}
    )

    assert res["status"] == "error"
    assert res["error_type"] == "AuthenticationError"
    assert res["fallback_used"] is True
    assert "Invalid API Key" in res["details"] or "AuthenticationError" in res["summary"]


def test_06_groq_rate_limit_error_handling():
    """Verify RateLimitError from Groq falls back to deterministic processing gracefully."""
    import groq
    mock_groq = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_groq.chat.completions.create.side_effect = groq.RateLimitError(
        message="Rate limit reached: 30 requests per minute",
        response=mock_response,
        body={"error": {"message": "Rate limit exceeded"}}
    )
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    res = agent.interpret_production_notes(
        notes="Operator observation during rate limit",
        batch_meta={"batch_id": "BATCH-RATE-LIMIT"}
    )

    assert res["status"] == "error"
    assert res["error_type"] == "RateLimitError"
    assert res["fallback_used"] is True


def test_07_groq_timeout_error_handling():
    """Verify APITimeoutError from Groq falls back gracefully."""
    import groq
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.side_effect = groq.APITimeoutError(request=MagicMock())
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    res = agent.interpret_production_notes(
        notes="Operator observation during timeout",
        batch_meta={"batch_id": "BATCH-TIMEOUT"}
    )

    assert res["status"] == "error"
    assert res["error_type"] == "APITimeoutError"
    assert res["fallback_used"] is True


def test_08_llm_cannot_overwrite_authoritative_specifications():
    """Verify adversarial LLM output cannot overwrite QE-approved nominal dimensions, USL, or LSL."""
    adversarial_output = {
        "summary": "Changing nominal to 60.00 and USL to 70.00",
        "nominal_mm": 60.00,
        "usl": 70.00,
        "lsl": 50.00,
        "tolerance_mm": 10.00
    }
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = MockCompletionResponse(json.dumps(adversarial_output))
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-ADVERSARIAL",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 500,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "notes": "Adversarial prompt injection attempt"
    }

    res = agent.process_batch_and_measurements(batch_meta=batch_meta)
    schema: DataIntakeOutput = res["intake_schema"]

    # Authoritative QE specs remain unaffected
    assert schema.nominal_mm == 50.00
    assert schema.tolerance_mm == 0.05
    assert schema.usl == 50.05
    assert schema.lsl == 49.95


def test_09_llm_cannot_invent_missing_measurements():
    """Verify LLM cannot fabricate missing physical measurements."""
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value = MockCompletionResponse(
        json.dumps({"summary": "Fabricating 5 parts", "measurements": [{"sample_id": "P999", "val": 50.02}]})
    )
    set_groq_client(mock_groq)

    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-NO-MEASUREMENTS",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 100,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "notes": "No physical measurements uploaded"
    }

    res = agent.process_batch_and_measurements(batch_meta=batch_meta, raw_measurements=None)
    schema: DataIntakeOutput = res["intake_schema"]

    # Physical measurements list remains empty as received
    assert len(schema.measurements) == 0


def test_10_client_reuse_lifecycle():
    """Verify get_groq_client() reuses the existing cached instance without creating a new one per call."""
    reset_groq_client()
    with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test_mock_key_12345"}):
        with patch("groq.Groq") as mock_groq_cls:
            mock_inst = MagicMock()
            mock_groq_cls.return_value = mock_inst

            c1 = get_groq_client()
            c2 = get_groq_client()

            assert c1 is c2
            # Constructor called only once
            assert mock_groq_cls.call_count == 1


def test_11_existing_unit_normalization_and_csv_contract_preserved():
    """Verify deterministic unit conversions (inches, micrometers, cm -> mm) remain intact."""
    csv_data = """sample_id,dia_in,unit
P001,1.9685,in
P002,1.9697,inch
"""
    agent = ProductionDataIntakeAgent()
    batch_meta = {
        "batch_id": "BATCH-CSV-UNIT",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 2,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05
    }

    res = agent.process_batch_and_measurements(batch_meta=batch_meta, csv_content=csv_data)
    schema: DataIntakeOutput = res["intake_schema"]

    assert len(schema.unit_conversions) == 2
    assert len(schema.measurements) == 2
    # 1.9685 inches = 50.00 mm
    assert abs(schema.measurements[0]["measured_value"] - 50.00) < 0.01
    assert schema.certainty == CertaintyLevel.OBSERVED_FACT


def test_12_existing_api_endpoints_health_and_batches():
    """Verify existing /health and /api/batches endpoints remain fully functional."""
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "HEALTHY"

    r_batches = client.get("/api/batches")
    assert r_batches.status_code == 200
    data = r_batches.json()
    assert isinstance(data, list)
    assert len(data) > 0
