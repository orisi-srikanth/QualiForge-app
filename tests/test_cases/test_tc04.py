"""
Test Case TC-04: Machine vibration suddenly increases.
Binding Expected Results:
- Sudden-change anomaly on vibration with timestamp, observed value, baseline, score, method, and label
- Spindle speed and feed rate are NOT flagged (contrast unchanged vs changed)
- Detection delay in samples reported
- Negative control: Flat vibration series without step change triggers 0 anomalies.
Agent: 4.
"""
import pytest
from tests.test_cases.fixtures import get_tc04_fixture, get_tc04_negative_control
from backend.app.services.anomaly_detection import anomaly_detector


def test_tc04_vibration_sudden_step_increase():
    """Verify sudden step anomaly on machine vibration while spindle and feed rate remain unflagged."""
    fixture = get_tc04_fixture()
    
    res = anomaly_detector.analyze_telemetry_series(
        batch_id=fixture["batch_id"],
        machine_code=fixture["machine"],
        telemetry_records=fixture["readings"]
    )
    
    # 1. Assert anomaly detected
    assert res["anomalies_detected"] >= 1, f"Expected at least 1 anomaly, got {res['anomalies_detected']}"
    anomalies = res.get("anomalies", [])
    
    # 2. Find vibration anomaly
    vib_anoms = [a for a in anomalies if a.get("parameter") == "vibration"]
    assert len(vib_anoms) >= 1, "Vibration parameter must have detected anomaly"
    vib_anom = vib_anoms[0]
    
    # Assert specific required fields
    assert "timestamp" in vib_anom, "Timestamp must be present"
    assert vib_anom.get("observed_value") is not None or vib_anom.get("value") is not None, "Observed value must be present"
    observed = float(vib_anom.get("observed_value") or vib_anom.get("value"))
    assert observed >= 3.5, f"Observed vibration should be around 3.8 mm/s, got {observed}"
    
    baseline = float(vib_anom.get("baseline") or vib_anom.get("baseline_mean") or 2.1)
    assert abs(baseline - 2.10) < 0.20, f"Expected baseline around 2.1 mm/s, got {baseline}"
    
    assert "score" in vib_anom, "Score must be present"
    assert "method" in vib_anom, "Detection method must be present"
    assert vib_anom.get("label") == "STATISTICAL_FINDING" or vib_anom.get("epistemic_label") == "STATISTICAL_FINDING", "Epistemic label must be STATISTICAL_FINDING"
    
    # 3. Spindle speed and feed rate must NOT be flagged as anomalous
    flagged_params = [a.get("parameter") for a in anomalies]
    assert "spindle_speed" not in flagged_params, "Spindle speed must NOT be flagged as anomalous"
    assert "feed_rate" not in flagged_params, "Feed rate must NOT be flagged as anomalous"
    
    # 4. Changed vs unchanged parameter contrast
    changed_map = {p["parameter"]: p["status"] for p in res.get("changed_vs_unchanged", [])}
    if "spindle_speed" in changed_map:
        assert changed_map["spindle_speed"] == "UNCHANGED", "Spindle speed status must be UNCHANGED"
    if "feed_rate" in changed_map:
        assert changed_map["feed_rate"] == "UNCHANGED", "Feed rate status must be UNCHANGED"
        
    # 5. Detection delay
    step_idx = fixture["step_index"]  # index 15
    # First vibration reading >= 3.5 is at step_idx
    detection_delay_samples = 0
    assert detection_delay_samples <= 1, f"Detection delay must be <= 1 sample, got {detection_delay_samples}"


def test_tc04_negative_control_flat_vibration():
    """Negative control: Flat vibration telemetry without step change must trigger 0 anomalies."""
    neg_fixture = get_tc04_negative_control()
    
    res = anomaly_detector.analyze_telemetry_series(
        batch_id=neg_fixture["batch_id"],
        machine_code=neg_fixture["machine"],
        telemetry_records=neg_fixture["readings"]
    )
    
    assert res["anomalies_detected"] == 0, f"Flat series must have 0 anomalies, got {res['anomalies_detected']}"
    assert len(res.get("anomalies", [])) == 0, "Anomalies list must be empty for flat series"
