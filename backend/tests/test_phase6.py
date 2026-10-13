"""
Unit Tests for Phase 6: Multi-Agent System & LangGraph Orchestration
Tests end-to-end execution of all 8 agents on BATCH-0245 and Critic causal claim interception.
"""
import pytest
from backend.app.orchestrator.engine import orchestrator
from backend.app.agents.critic_agent import critic_agent

def test_full_agent_pipeline_anchor_batch():
    batch_meta = {
        "batch_id": "BATCH-0245",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "material": "Carbon Steel",
        "shift": "Night Shift",
        "quantity": 500,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "usl": 50.05,
        "lsl": 49.95,
        "measurements": [
            {"sample_id": "P001", "measured_value": 50.01},
            {"sample_id": "P002", "measured_value": 50.03},
            {"sample_id": "P003", "measured_value": 50.06},
            {"sample_id": "P004", "measured_value": 50.08},
            {"sample_id": "P005", "measured_value": 50.07},
        ]
    }
    telemetry = [
        {"ts": "02:00", "vibration": 2.1, "tool_usage_cycles": 600, "spindle_speed": 1200.0, "feed_rate": 0.20, "coolant_temp": 24.0, "motor_current": 14.5, "cycle_time": 45.0},
        {"ts": "02:20", "vibration": 3.8, "tool_usage_cycles": 1150, "spindle_speed": 1200.0, "feed_rate": 0.20, "coolant_temp": 25.0, "motor_current": 16.8, "cycle_time": 46.2},
    ]

    # Execute full pipeline
    state = orchestrator.run_full_pipeline(
        batch_meta=batch_meta,
        measurements=batch_meta["measurements"],
        telemetry_records=telemetry,
        workflow_id="WF-TEST-0245"
    )

    # 1. Pipeline status must be paused at Human Approval Gate
    assert state.status == "PENDING_HUMAN_APPROVAL"
    assert "Human Quality Engineer" in state.current_agent

    # 2. Check all agents logged in execution trace
    agent_names = [log.agent_name for log in state.execution_trace]
    assert any("Intake" in name for name in agent_names), "Agent 1 must be present"
    assert any("Compliance" in name for name in agent_names), "Agent 3 must be present"
    assert any("Anomaly" in name for name in agent_names), "Agent 4 must be present"
    assert any("Statistical Process Control" in name or "SPC" in name for name in agent_names), "Agent 5 must be present"
    assert any("Root Cause" in name for name in agent_names), "Agent 6 must be present"
    assert any("Corrective" in name or "CAPA" in name for name in agent_names), "Agent 7 must be present"
    assert any("Critic" in name for name in agent_names), "Agent 8 must be present"

    # 3. Check Dimensional compliance results (P003, P004, P005 nonconforming)
    assert state.dimensional_report.nonconforming == 3
    assert state.dimensional_report.accepted == 2

    # 4. Check Process Anomaly findings (Vibration critical)
    assert state.process_report.vibration_current == 3.8
    assert state.process_report.vibration_status == "ABNORMAL_CRITICAL"

    # 5. Check RCA hypotheses (Ranked, tool wear highest)
    assert len(state.rca_report.ranked_hypotheses) >= 3
    assert state.rca_report.ranked_hypotheses[0].title == "Progressive Tool Flank Wear"

    # 6. Check Critic review verdict
    assert state.critic_review is not None
    assert state.critic_review.validated_calculations is True

def test_critic_catches_injected_causal_claim():
    # Inject forbidden causal claim
    injected_text = "The dimensional failure was definitely caused by incorrect cutting speed."
    found_claim = critic_agent.scan_unsupported_causal_claims(injected_text)
    assert found_claim is not None
    assert "definitely caused" in found_claim.lower()

    # Safe text must not trigger
    safe_text = "Progressive tool flank wear is a potential contributing factor requiring engineering verification."
    assert critic_agent.scan_unsupported_causal_claims(safe_text) is None
