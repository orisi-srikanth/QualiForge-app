import pytest
from tests.test_cases.fixtures import get_tc01_fixture, get_tc01_negative_control
from backend.app.orchestrator.engine import orchestrator

def test_tc01_all_measurements_within_spec():
    fixture = get_tc01_fixture()
    
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": fixture["batch_id"],
            "part_number": fixture["part_number"],
            "machine": fixture["machine"],
            "nominal_mm": fixture["nominal_mm"],
            "tolerance_mm": fixture["tolerance_mm"],
            "usl": fixture["usl"],
            "lsl": fixture["lsl"]
        },
        measurements=fixture["measurements"],
        telemetry_records=fixture["telemetry"]
    )
    
    assert state.dimensional_report is not None, "Dimensional report must be generated"
    assert state.dimensional_report.nonconforming == 0, f"Expected 0 nonconforming, got {state.dimensional_report.nonconforming}"
    assert state.dimensional_report.rejection_rate_percent == 0.0, f"Expected 0.0% rejection, got {state.dimensional_report.rejection_rate_percent}"
    assert state.dimensional_report.total_inspected == 32, f"Expected 32 total inspected parts, got {state.dimensional_report.total_inspected}"
    assert state.dimensional_report.accepted == 32, f"Expected 32 accepted parts, got {state.dimensional_report.accepted}"
    
    meas_map = {m.sample_id: m for m in state.dimensional_report.measurements}
    assert meas_map["P031"].is_conforming is True, "Boundary USL (50.05 mm) must be conforming"
    assert meas_map["P032"].is_conforming is True, "Boundary LSL (49.95 mm) must be conforming"
    
    assert state.process_report is not None, "Process report must be generated"
    assert state.process_report.anomalies_detected == 0, f"Expected 0 anomalies, got {state.process_report.anomalies_detected}"
    assert state.has_anomalies is False
    
    assert state.status == "CONFORMING_AUDITED", f"Expected CONFORMING_AUDITED, got {state.status}"
    agents_run = [step.agent_name for step in state.execution_trace]
    
    assert any("Agent 1" in a for a in agents_run), "Agent 1 must be in execution trace"
    assert any("Agent 3" in a for a in agents_run), "Agent 3 must be in execution trace"
    assert any("Agent 4" in a for a in agents_run), "Agent 4 must be in execution trace"
    assert any("Agent 5" in a for a in agents_run), "Agent 5 must be in execution trace"
    
    assert not any("Agent 6" in a for a in agents_run), "Agent 6 (RCA) must be skipped for conforming batch"
    assert not any("Agent 7" in a for a in agents_run), "Agent 7 (CAPA) must be skipped for conforming batch"
    assert not any("Agent 8" in a for a in agents_run), "Agent 8 (Critic) must be skipped for conforming batch"

def test_tc01_negative_control_fails_conformance():
    neg_fixture = get_tc01_negative_control()
    
    state = orchestrator.run_full_pipeline(
        batch_meta={
            "batch_id": neg_fixture["batch_id"],
            "part_number": neg_fixture["part_number"],
            "machine": neg_fixture["machine"],
            "nominal_mm": neg_fixture["nominal_mm"],
            "tolerance_mm": neg_fixture["tolerance_mm"]
        },
        measurements=neg_fixture["measurements"],
        telemetry_records=neg_fixture["telemetry"]
    )
    
    assert state.dimensional_report.nonconforming >= 1, "Negative control must detect nonconforming item"
    assert state.dimensional_report.rejection_rate_percent > 0.0, "Rejection rate must be > 0.0%"
    assert state.status != "CONFORMING_AUDITED", "Negative control must not be audited as conforming"
