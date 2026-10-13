"""
PyTest Test Suite for Mandatory Scenarios TC-01 to TC-08
"""
import pytest
from backend.app.scenarios.test_scenarios import run_test_scenario, run_all_scenarios

@pytest.mark.parametrize("scenario_id", ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07", "TC-08"])
def test_scenario_execution(scenario_id: str):
    res = run_test_scenario(scenario_id)
    assert res["status"] == "PASS", f"Scenario {scenario_id} failed: {res.get('actual_result')}"
    assert "evidence" in res and res["evidence"]
    assert "agents_involved" in res and len(res["agents_involved"]) > 0

def test_all_scenarios_pass_rate():
    all_res = run_all_scenarios()
    assert len(all_res) == 8
    assert all(r["status"] == "PASS" for r in all_res)
