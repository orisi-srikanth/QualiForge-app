"""
Test Case TC-05: Measurements gradually move toward USL.
Binding Expected Results:
- Drift identified (EWMA or CUSUM plus trend test with p-value) BEFORE first measurement above USL
- Show index of first alarm and index of first out-of-spec part
- Assert alarm_index < out_of_spec_index
- SPC rule violations listed (Nelson Rule 3 / trend / mean shift)
- Negative control: Stable stationary series triggers 0 drift alarms.
Agents: 3, 4, 5.
"""
import pytest
import numpy as np
from scipy import stats
from tests.test_cases.fixtures import get_tc05_fixture, get_tc05_negative_control
from backend.app.agents.spc_agent import spc_agent
from backend.app.services.anomaly_detection import HybridAnomalyDetector


def test_tc05_gradual_measurement_drift_before_usl():
    """Verify EWMA / CUSUM and SPC Nelson Rule 3 detect drift prior to first out-of-spec part."""
    fixture = get_tc05_fixture()
    values = fixture["values"]
    usl = fixture["usl"]
    first_oos_index = fixture["expected_first_oos_index"]
    assert first_oos_index is not None, "Fixture must contain an out-of-spec boundary part"
    
    # 1. CUSUM detector
    vals_arr = np.array(values, dtype=float)
    cusum_res = HybridAnomalyDetector.compute_cusum(vals_arr, target=50.00, sigma=0.005)
    
    # 2. EWMA detector
    ewma_res = HybridAnomalyDetector.compute_ewma(vals_arr, target=50.00, sigma=0.005)
    
    # 3. Statistical trend test (Linear regression slope and p-value)
    steps = np.arange(len(values))
    reg = stats.linregress(steps, vals_arr)
    assert reg.slope > 0.0, f"Drift must have positive upward slope, got {reg.slope}"
    assert reg.pvalue < 0.001, f"Trend p-value must be statistically significant (<0.001), got {reg.pvalue}"
    
    # 4. Assert alarm triggered BEFORE first out-of-spec part
    first_alarm_index = min(
        cusum_res.alarm_index if cusum_res.alarm_triggered else 999,
        ewma_res.alarm_index if ewma_res.alarm_triggered else 999
    )
    assert first_alarm_index < first_oos_index, (
        f"Assertion Failed: First alarm index ({first_alarm_index}) must precede "
        f"first out-of-spec index ({first_oos_index})"
    )
    
    # 5. SPC Agent analysis
    spc_report = spc_agent.analyze_process_capability_and_control(
        batch_id=fixture["batch_id"],
        values=values,
        usl=usl,
        lsl=fixture["lsl"],
        nominal=fixture["nominal_mm"]
    )["report"]
    
    # Assert SPC rule violations listed
    assert len(spc_report.nelson_violations) > 0, "SPC report must list Nelson rule violations"
    rule_numbers = [v.rule_number for v in spc_report.nelson_violations]
    assert 3 in rule_numbers or 2 in rule_numbers, "Nelson Rule 3 (Trend/Wear) or Rule 2 (Shift) must be triggered"


def test_tc05_negative_control_stable_process():
    """Negative control: Stable centered process does not trigger drift alarm or Nelson Rule 3."""
    neg_fixture = get_tc05_negative_control()
    vals_arr = np.array(neg_fixture["values"], dtype=float)
    
    # Linear trend test
    steps = np.arange(len(vals_arr))
    reg = stats.linregress(steps, vals_arr)
    assert abs(reg.slope) < 0.001, "Stable process should have near-zero slope"
    
    # SPC Agent
    spc_report = spc_agent.analyze_process_capability_and_control(
        batch_id=neg_fixture["batch_id"],
        values=neg_fixture["values"],
        usl=neg_fixture["usl"],
        lsl=neg_fixture["lsl"],
        nominal=neg_fixture["nominal_mm"]
    )["report"]
    
    rule_numbers = [v.rule_number for v in spc_report.nelson_violations]
    assert 3 not in rule_numbers, "Stable process must NOT trigger Nelson Rule 3 (drift)"
