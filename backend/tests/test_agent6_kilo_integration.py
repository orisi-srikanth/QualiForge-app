"""
Test Suite for Kilo Gateway + NVIDIA Nemotron Integration for Agent 6 (RCA)
Covers all 12 verification areas specified in the task:
  1. Valid structured RCA response.
  2. Supporting and contradicting evidence.
  3. Unsupported evidence IDs.
  4. Fabricated or missing source references.
  5. Unsupported causal claims.
  6. Malformed JSON and Pydantic validation failure with single-retry recovery.
  7. Gateway timeout, rate limiting, authentication failure, and unavailable model.
  8. Missing API key.
  9. Retry limit and invalid-response fallback.
 10. Human approval and batch-disposition safety.
 11. Agent 7, Agent 8, and PDF report compatibility.
 12. Regression verification.
All tests use mock gateway calls and do not burn live API credits.
"""
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from openai import RateLimitError, APITimeoutError, AuthenticationError

from backend.app.agents.rca_agent import (
    rca_agent,
    get_kilo_client,
    set_kilo_client,
    reset_kilo_client,
    strip_markdown_json_fences,
    verify_kilo_model_availability
)
from backend.app.models.schemas import (
    CertaintyLevel, RCAReport, HypothesisEvidence
)
from backend.app.agents.capa_agent import capa_agent
from backend.app.agents.reviewer_agent import reviewer_agent
from backend.app.services.pdf_report import pdf_report_generator


@pytest.fixture(autouse=True)
def cleanup_kilo_client():
    """Ensure mock client does not leak across test boundaries."""
    reset_kilo_client()
    yield
    reset_kilo_client()


@pytest.fixture
def sample_evidence_payload():
    return {
        "incident_id": "INC-2026-088",
        "batch_id": "BATCH-0245",
        "defect_type": "Oversized shaft diameter",
        "nominal_spec": {
            "characteristic": "outer_diameter_mm",
            "usl": 50.05,
            "max_measured_val": 50.08
        },
        "measurements": {
            "nonconforming_samples": ["P003 (50.06 mm)", "P004 (50.08 mm)", "P005 (50.07 mm)"]
        },
        "process_parameters": {
            "vibration": 3.8,
            "tool_cycles": 1150
        },
        "historical_incidents": [
            {
                "incident_id": "NCR-019",
                "title": "Tool Wear Shaft Deflection",
                "defect_type": "Oversized shaft diameter",
                "confirmed_root_cause": "Progressive tool flank wear (VB > 0.35 mm)",
                "similarity_score": 0.88
            }
        ],
        "valid_source_ids": [
            "measurements:P001",
            "measurements:P002",
            "measurements:P003",
            "measurements:P004",
            "measurements:P005",
            "process_reading:02:20",
            "process_reading:vibration",
            "maintenance_record:CAL-CERT-2026-004",
            "kb_document:NCR-019",
            "batch_metadata:shift",
            "qe_spec:outer_diameter_mm"
        ]
    }


def create_mock_completion_choice(content: str):
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ---------------------------------------------------------------------------
# 1. Valid structured RCA response
# ---------------------------------------------------------------------------
def test_01_valid_structured_rca_response(sample_evidence_payload):
    valid_json_output = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Progressive Carbide Insert Flank Wear",
                "category": "Machine",
                "description": "Tool wear exceeding 1150 cycles led to radial cutting edge loss and part growth.",
                "confidence_score": 0.88,
                "evidence_score": 0.88,
                "supporting_evidence": [
                    "Tool cycles at 1150 exceed nominal wear threshold of 600 cycles",
                    "Monotonic diameter increase observed across parts P003, P004, and P005"
                ],
                "contradicting_evidence": [
                    "Micrometer calibration verified on 2026-10-01 (CAL-CERT-2026-004)"
                ],
                "missing_evidence": [
                    "Optical microscope flank wear scar measurement (VB) pending"
                ],
                "alternative_explanations": [
                    "Thermal workpiece expansion"
                ],
                "required_confirmation": "Perform tool insert optical microscope inspection.",
                "sources": ["process_reading:02:20", "measurements:P003", "kb_document:NCR-019"],
                "confidence_text": "Requires engineering verification",
                "epistemic_label": "HYPOTHESIS"
            }
        ],
        "reasoning_summary": "Telemetry spike in vibration and high tool cycles support tool wear as leading hypothesis.",
        "correlation_vs_causation_note": "Observed statistical correlation between cycles and diameter requires physical insert wear measurement.",
        "requires_reassessment": False,
        "reassessment_reason": None
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(
        f"```json\n{valid_json_output}\n```"
    )

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)

    assert res["success"] is True
    assert len(res["hypotheses"]) == 1
    hyp = res["hypotheses"][0]
    assert isinstance(hyp, HypothesisEvidence)
    assert hyp.hypothesis_id == "HYP-01"
    assert hyp.rank == 1
    assert hyp.title == "Progressive Carbide Insert Flank Wear"
    assert hyp.epistemic_label == "HYPOTHESIS"
    assert hyp.certainty == CertaintyLevel.HYPOTHESIS
    assert res["llm_metadata"]["status"] == "VALIDATED"
    assert res["llm_metadata"]["provider"] == "kilo_gateway"
    assert res["llm_metadata"]["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert res["requires_reassessment"] is False


# ---------------------------------------------------------------------------
# 2. Supporting and contradicting evidence
# ---------------------------------------------------------------------------
def test_02_supporting_and_contradicting_evidence(sample_evidence_payload):
    json_output = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Spindle Vibration Deflection",
                "category": "Machine",
                "description": "Vibration elevated to 3.8 mm/s causing tool chatter.",
                "confidence_score": 0.75,
                "supporting_evidence": ["Vibration spiked to 3.8 mm/s at 02:20"],
                "contradicting_evidence": ["Spindle speed remained stable at 1200 RPM nominal"],
                "missing_evidence": ["FFT accelerometer spectrum not recorded"],
                "required_confirmation": "Spindle bearing runout dial indicator test",
                "sources": ["process_reading:vibration", "process_reading:02:20"]
            }
        ],
        "reasoning_summary": "Vibration observed prior to defect.",
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(json_output)

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res["success"] is True
    hyp = res["hypotheses"][0]
    # Verify non-empty supporting and contradicting evidence
    assert len(hyp.supporting_evidence) > 0
    assert "Vibration spiked" in hyp.supporting_evidence[0]
    assert len(hyp.contradicting_evidence) > 0
    assert "Spindle speed remained stable" in hyp.contradicting_evidence[0]


# ---------------------------------------------------------------------------
# 3. Unsupported evidence IDs
# ---------------------------------------------------------------------------
def test_03_unsupported_evidence_ids(sample_evidence_payload):
    json_output = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Coolant Concentration Fluctuation",
                "category": "Method",
                "description": "Coolant refractometer Brix value out of range.",
                "confidence_score": 0.60,
                "supporting_evidence": ["Refractometer reading was low"],
                "contradicting_evidence": ["Coolant temp nominal at 24.5 C"],
                "required_confirmation": "Lab refractometer titration",
                "sources": [
                    "measurements:P003",
                    "telemetry:uncalibrated_refractometer_sensor_99"  # Unsupported source!
                ]
            }
        ],
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(json_output)

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res["success"] is True
    # Unsupported source detected and captured
    assert "telemetry:uncalibrated_refractometer_sensor_99" in res["unsupported_sources_detected"]
    # Filtered out from validated hypothesis sources
    assert "telemetry:uncalibrated_refractometer_sensor_99" not in res["hypotheses"][0].sources
    # Detection of unsupported source forces reassessment recommendation
    assert res["requires_reassessment"] is True


# ---------------------------------------------------------------------------
# 4. Fabricated or missing source references
# ---------------------------------------------------------------------------
def test_04_fabricated_source_references(sample_evidence_payload):
    json_output = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Historical Tool Fixture Failure",
                "category": "Machine",
                "description": "Similar to unrecorded incident.",
                "confidence_score": 0.50,
                "supporting_evidence": ["Matches prior failure"],
                "contradicting_evidence": ["No recent fixture maintenance on record"],
                "required_confirmation": "Inspect fixture clamps",
                "sources": [
                    "kb_document:NCR-FABRICATED-777",  # Fabricated historical incident
                    "maintenance_record:FAKE-MAINT-999"  # Fabricated maintenance log
                ]
            }
        ],
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(json_output)

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res["success"] is True
    assert "kb_document:NCR-FABRICATED-777" in res["unsupported_sources_detected"]
    assert "maintenance_record:FAKE-MAINT-999" in res["unsupported_sources_detected"]
    assert res["requires_reassessment"] is True
    assert "Unsupported sources detected" in (res["reassessment_reason"] or "")


# ---------------------------------------------------------------------------
# 5. Unsupported causal claims
# ---------------------------------------------------------------------------
def test_05_unsupported_causal_claims(sample_evidence_payload):
    json_output = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Tool Wear",
                "category": "Machine",
                "description": "Vibration correlation proves causation for the shaft oversize defect.",
                "confidence_score": 0.95,
                "supporting_evidence": ["Correlation proves causation definitely."],
                "contradicting_evidence": ["No contradicting facts"],
                "required_confirmation": "None needed",
                "sources": ["process_reading:02:20"],
                "epistemic_label": "CONFIRMED_ROOT_CAUSE"  # LLM attempts to assert confirmed cause!
            }
        ],
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(json_output)

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res["success"] is True
    hyp = res["hypotheses"][0]
    # Epistemic safety override: LLM cannot assert confirmed cause
    assert hyp.epistemic_label == "HYPOTHESIS"
    assert hyp.certainty == CertaintyLevel.HYPOTHESIS
    # Causal claim detected and disclaimer appended
    assert "HYP-01" in res["unsupported_causal_claims_detected"]
    assert "association, not proven causation" in hyp.description


# ---------------------------------------------------------------------------
# 6. Malformed JSON and single-retry recovery
# ---------------------------------------------------------------------------
def test_06_malformed_json_and_single_retry_recovery(sample_evidence_payload):
    malformed_raw = '{"hypotheses": [{"hypothesis_id": "HYP-01", "title": "Incomplete'
    valid_raw = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Recovered Tool Wear",
                "category": "Machine",
                "description": "Recovered on retry.",
                "confidence_score": 0.80,
                "supporting_evidence": ["Cycles 1150"],
                "contradicting_evidence": ["Calibration OK"],
                "required_confirmation": "Microscope check",
                "sources": ["measurements:P001"]
            }
        ],
        "requires_reassessment": False
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        create_mock_completion_choice(malformed_raw),
        create_mock_completion_choice(valid_raw)
    ]

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    # Exactly one retry triggered
    assert mock_client.chat.completions.create.call_count == 2
    assert res["success"] is True
    assert res["llm_metadata"]["attempts"] == 2
    assert res["hypotheses"][0].title == "Recovered Tool Wear"


# ---------------------------------------------------------------------------
# 7. Gateway timeout, rate limiting, authentication failure, and model check
# ---------------------------------------------------------------------------
def test_07_gateway_errors_handling(sample_evidence_payload):
    mock_client = MagicMock()

    # 7a: Timeout Error
    mock_client.chat.completions.create.side_effect = APITimeoutError(request=None)
    res_timeout = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res_timeout["success"] is False
    assert res_timeout["fallback_used"] is True
    assert res_timeout["llm_metadata"]["status"] == "GATEWAY_APITIMEOUTERROR"

    # 7b: Rate Limit Error
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="429 Too Many Requests", response=MagicMock(), body=None
    )
    res_rate = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res_rate["success"] is False
    assert res_rate["llm_metadata"]["status"] == "GATEWAY_RATELIMITERROR"

    # 7c: Authentication Error
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message="401 Invalid Token", response=MagicMock(), body=None
    )
    res_auth = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    assert res_auth["success"] is False
    assert res_auth["llm_metadata"]["status"] == "GATEWAY_AUTHENTICATIONERROR"

    # 7d: Unavailable Model
    mock_model_obj = MagicMock()
    mock_model_obj.id = "openai/gpt-4o"
    mock_client.models.list.return_value = MagicMock(data=[mock_model_obj])
    res_avail = verify_kilo_model_availability(
        client=mock_client,
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free"
    )
    assert res_avail["available"] is False
    assert "nvidia/nemotron-3-ultra-550b-a55b:free" not in res_avail["matching_nemotron_models"]


# ---------------------------------------------------------------------------
# 8. Missing API key
# ---------------------------------------------------------------------------
def test_08_missing_api_key_handling(sample_evidence_payload):
    with patch.dict(os.environ, {"KILO_API_KEY": ""}, clear=False):
        with patch("backend.app.core.config.settings.KILO_API_KEY", ""):
            client = get_kilo_client(force_refresh=True)
            assert client is None

            res = rca_agent.reason_with_kilo(sample_evidence_payload, client=None)
            assert res["success"] is False
            assert res["fallback_used"] is True
            assert "KILO_API_KEY" in res["error"]
            assert res["llm_metadata"]["status"] == "UNCONFIGURED_FALLBACK"


# ---------------------------------------------------------------------------
# 9. Retry limit and invalid-response fallback
# ---------------------------------------------------------------------------
def test_09_retry_limit_and_fallback(sample_evidence_payload):
    broken_content = "This is not JSON at all."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(broken_content)

    res = rca_agent.reason_with_kilo(sample_evidence_payload, client=mock_client)
    # Stopped at max 2 calls (initial + 1 retry)
    assert mock_client.chat.completions.create.call_count == 2
    assert res["success"] is False
    assert res["fallback_used"] is True
    assert res["llm_metadata"]["status"] == "VALIDATION_FAILED_REASSESSMENT_REQUIRED"
    assert res["llm_metadata"]["requires_reassessment"] is True


# ---------------------------------------------------------------------------
# 10. Human approval and batch-disposition safety
# ---------------------------------------------------------------------------
def test_10_human_approval_safety(sample_evidence_payload):
    valid_json = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Tool Wear",
                "category": "Machine",
                "description": "Tool wear investigation hypothesis.",
                "confidence_score": 0.85,
                "supporting_evidence": ["High cycles"],
                "contradicting_evidence": ["None"],
                "required_confirmation": "QE visual check",
                "sources": ["measurements:P001"]
            }
        ],
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(valid_json)

    out = rca_agent.analyze_incident(
        incident_id="INC-SAFETY-01",
        batch_id="BATCH-0245",
        kilo_client=mock_client
    )
    report = out["report"]

    # Verify Agent 6 safety assertions
    assert report.autonomous_actions_prohibited is True
    assert report.review_status == "HUMAN_REVIEW_REQUIRED"
    assert report.certainty == CertaintyLevel.HYPOTHESIS
    assert report.llm_metadata is not None
    assert report.llm_metadata["provider"] == "kilo_gateway"
    assert "tool_kilo_nemotron_rca_synthesis" in out["log"].tool_calls


# ---------------------------------------------------------------------------
# 11. Agent 7, Agent 8, and PDF report compatibility
# ---------------------------------------------------------------------------
def test_11_downstream_agent_and_pdf_compatibility():
    valid_json = json.dumps({
        "hypotheses": [
            {
                "hypothesis_id": "HYP-01",
                "rank": 1,
                "title": "Tool Flank Wear",
                "category": "Machine",
                "description": "Carbide insert flank wear exceeding tolerance.",
                "confidence_score": 0.89,
                "supporting_evidence": ["Cycles: 1150", "Vibration: 3.8 mm/s"],
                "contradicting_evidence": ["Feed and speed unchanged"],
                "required_confirmation": "Optical tool measurement",
                "sources": ["process_reading:02:20", "measurements:P003"]
            }
        ],
        "reasoning_summary": "High cycle count correlates with progressive tool wear.",
        "requires_reassessment": False
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = create_mock_completion_choice(valid_json)

    out = rca_agent.analyze_incident(
        incident_id="INC-COMPAT-01",
        batch_id="BATCH-0245",
        kilo_client=mock_client
    )
    report = out["report"]

    # 1. Agent 7 (CAPA) generates plan from RCA report
    capa_out = capa_agent.generate_capa_plan(
        incident_id="INC-COMPAT-01",
        batch_id="BATCH-0245",
        rca_report=report
    )
    assert capa_out is not None
    capa_report = capa_out["capa"]
    assert len(capa_report.containment_actions) > 0
    assert len(capa_report.corrective_actions) > 0
    assert len(capa_report.preventive_actions) > 0
    assert capa_report.approval_status == "PENDING_ENGINEER_APPROVAL"

    # 2. Agent 8 (Reviewer) critiques report
    critique_out = reviewer_agent.review_workflow(
        intake_data={"batch_data": {"nominal_mm": 50.0, "tolerance_mm": 0.05}},
        compliance_data={"report": {"usl": 50.05, "lsl": 49.95}},
        vision_data=None,
        anomaly_data={},
        spc_data={},
        rca_data={"report": report.model_dump()},
        capa_data={"capa": capa_report.model_dump()}
    )
    assert critique_out is not None
    assert "review" in critique_out
    assert critique_out["review"].critic_verdict in ["APPROVED", "CONDITIONAL_APPROVAL", "REASSESS"]

    # 3. PDF generator creates valid PDF bytes
    state_mock = {
        "batch_id": "BATCH-0245",
        "rca_report": report.model_dump(),
        "capa_plan": capa_report.model_dump()
    }
    pdf_buf = pdf_report_generator.generate_audit_report(state_mock)
    pdf_bytes = pdf_buf.getvalue()
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# 12. Model availability verification check
# ---------------------------------------------------------------------------
def test_12_model_availability_live_check_function():
    mock_client = MagicMock()
    mock_m1 = MagicMock()
    mock_m1.id = "nvidia/nemotron-3-ultra-550b-a55b:free"
    mock_m2 = MagicMock()
    mock_m2.id = "google/gemini-2.5-flash"
    mock_client.models.list.return_value = MagicMock(data=[mock_m1, mock_m2])

    res = verify_kilo_model_availability(
        client=mock_client,
        model_id="nvidia/nemotron-3-ultra-550b-a55b:free"
    )
    assert res["available"] is True
    assert res["total_available"] == 2
    assert "nvidia/nemotron-3-ultra-550b-a55b:free" in res["matching_nemotron_models"]
