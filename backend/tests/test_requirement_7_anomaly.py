
import os
import json
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from sklearn.metrics import precision_score, recall_score, f1_score
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.anomaly_detection import (
    anomaly_detector,
    HybridAnomalyDetector,
    OPERATIONAL_THRESHOLDS,
)
from backend.app.database.session import SessionLocal
from backend.app.database.models import ProcessReading, ProcessBaseline, Batch
from backend.app.agents.process_agent import process_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.scenarios.test_scenarios import _run_tc04, _run_tc05

client = TestClient(app)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_check1_mechanisms_and_coverage():
    detector = anomaly_detector
    assert hasattr(detector, "compute_robust_z_score"), "Robust Z-score must be implemented"
    assert hasattr(detector, "compute_cusum"), "CUSUM must be implemented"
    assert hasattr(detector, "compute_ewma"), "EWMA must be implemented"
    assert hasattr(detector, "calculate_trend_statistics"), "Trend test must be implemented"
    assert hasattr(detector, "detect_drift_and_trends"), "Drift and trends alias must be implemented"
    assert hasattr(detector, "detect_multivariate_anomalies"), "Isolation Forest must be implemented"
    assert hasattr(detector, "_check_operational_thresholds"), "Threshold checking must be implemented"
    assert hasattr(detector, "detect_anomalies"), "Main ensemble detector must be implemented"

    coverage_map = {
        "sudden_change": ["compute_robust_z_score", "compute_cusum", "detect_anomalies"],
        "gradual_drift": ["compute_ewma", "compute_cusum", "detect_drift_and_trends"],
        "multivariate": ["detect_multivariate_anomalies", "detect_anomalies"],
        "operational_threshold": ["_check_operational_thresholds", "detect_anomalies"],
    }
    for req_type, funcs in coverage_map.items():
        for func_name in funcs:
            assert hasattr(detector, func_name), f"Function {func_name} required for {req_type}"

def test_check2_sudden_changes_and_numpy_recalculation():
    normal_vib = 2.10
    spike_vib = 3.80
    median_val = 2.10
    mad_val = 0.04
    sigma_val = 0.05

    numpy_robust_z = 0.6745 * abs(spike_vib - median_val) / mad_val
    assert numpy_robust_z > 25.0, f"Spike robust Z should be extreme, got {numpy_robust_z}"

    detector_z = anomaly_detector.compute_robust_z_score(spike_vib, median_val, mad_val)
    assert abs(detector_z - numpy_robust_z) < 1e-6, "Detector robust z-score must match numpy independent formula"

    k = 0.5 * sigma_val
    h = 4.0 * sigma_val
    numpy_c_plus = max(0.0, 0.0 + (spike_vib - median_val - k))
    assert numpy_c_plus > h, f"CUSUM statistic {numpy_c_plus} must exceed decision interval {h}"

    series = [normal_vib, normal_vib, spike_vib]
    cusum_res = anomaly_detector.compute_cusum(series, target=median_val, k=k, h=h, sigma=sigma_val)
    assert cusum_res.alarm_triggered is True, "CUSUM must trigger alarm on spike"
    assert cusum_res.alarm_index == 2, "Alarm must trigger at index 2 (detection delay = 0 samples from injection)"

    readings = [
        {"timestamp": f"2026-10-11T10:{i:02d}:00", "vibration": 2.10 if i < 5 else 3.80, "spindle_speed": 1200, "feed_rate": 0.20, "coolant_temp": 24.0, "tool_usage_cycles": 100}
        for i in range(10)
    ]
    df = pd.DataFrame(readings)
    anomalies = anomaly_detector.detect_anomalies(df)
    vib_anomalies = [a for a in anomalies if a.get("parameter") == "vibration"]
    assert len(vib_anomalies) > 0, "Step change must be detected in vibration"
    first_flag_ts = vib_anomalies[0]["timestamp"]
    assert first_flag_ts == "2026-10-11T10:05:00", "Must flag at the exact step change timestamp (0-sample delay)"

def test_check3_gradual_drift_flagged_before_first_out_of_spec():
    tc05_result = _run_tc05()
    assert tc05_result["status"] == "PASS", "TC-05 scenario verification must pass"

    diameters = [50.00, 50.01, 50.02, 50.03, 50.04, 50.06]
    lambda_ = 0.2
    L = 3.0
    sigma = 0.008
    target = 50.00

    ewma_vals = []
    ucl_vals = []
    z_prev = target
    alarm_idx = None
    for t, x in enumerate(diameters, 1):
        z_t = lambda_ * x + (1.0 - lambda_) * z_prev
        ewma_vals.append(z_t)
        sigma_zt = sigma * np.sqrt((lambda_ / (2.0 - lambda_)) * (1.0 - (1.0 - lambda_) ** (2 * t)))
        ucl = target + L * sigma_zt
        ucl_vals.append(ucl)
        if z_t > ucl and alarm_idx is None:
            alarm_idx = t
        z_prev = z_t

    assert alarm_idx in [3, 4], f"Independent EWMA should trigger at sample 3 or 4, got {alarm_idx}"
    assert diameters[alarm_idx - 1] <= 50.05, f"Part at sample {alarm_idx} ({diameters[alarm_idx-1]} mm) must be strictly IN-SPEC"

    det_ewma = anomaly_detector.compute_ewma(diameters, target=target, lambda_=lambda_, L=L, sigma=sigma)
    assert det_ewma.alarm_triggered is True
    assert det_ewma.alarm_index == alarm_idx - 1

def test_check4_unusual_parameter_combinations_multivariate_only():
    np.random.seed(42)
    n = 200
    normal_data = {
        "timestamp": [f"2026-10-11T08:{i:02d}:00" for i in range(n)],
        "spindle_speed": np.random.normal(1200.0, 15.0, n),
        "feed_rate": np.random.normal(0.20, 0.008, n),
        "coolant_temp": np.random.normal(24.0, 0.5, n),
        "vibration": np.random.normal(2.10, 0.05, n),
        "motor_current": np.random.normal(12.0, 1.0, n),
        "tool_usage_cycles": [200 + i for i in range(n)],
    }
    df_normal = pd.DataFrame(normal_data)

    anomaly_detector.train_multivariate_model(df_normal)

    unusual_pt = {
        "spindle_speed": 1168.0,
        "feed_rate": 0.214,
        "coolant_temp": 24.2,
        "vibration": 2.18,
        "motor_current": 14.1,
    }

    for p, val in unusual_pt.items():
        med = float(np.median(df_normal[p]))
        mad = float(np.median(np.abs(df_normal[p] - med)))
        z = 0.6745 * abs(val - med) / max(mad, 1e-4)
        assert z < 3.0, f"Univariate robust Z for {p} ({z:.2f}) must remain below 3.0"

    op_tripped = False
    for p, val in unusual_pt.items():
        th = OPERATIONAL_THRESHOLDS.get(p, {})
        if val < th.get("min", -1e9) or val > th.get("max", 1e9):
            op_tripped = True
    assert op_tripped is False, "Univariate operational thresholds must not trip"

    multi_res = anomaly_detector.detect_multivariate_anomalies(pd.DataFrame([unusual_pt]))
    assert len(multi_res) > 0, "Isolation Forest must flag this joint combination"
    assert multi_res[0]["is_anomaly"] is True
    assert "IsolationForest" in multi_res[0]["method"]

def test_check5_operational_thresholds_dynamic_change_and_distinction():
    orig_threshold = OPERATIONAL_THRESHOLDS["vibration"]["critical"]
    assert orig_threshold == 3.5, "Default critical vibration threshold is 3.5 mm/s"

    reading = {"vibration": 3.80, "spindle_speed": 1200, "feed_rate": 0.20, "coolant_temp": 24.0, "tool_usage_cycles": 500}

    status_default, alarms_default = anomaly_detector._check_operational_thresholds(reading)
    assert status_default == "ABNORMAL_CRITICAL"
    assert any("vibration" in a.lower() for a in alarms_default)

    OPERATIONAL_THRESHOLDS["vibration"]["critical"] = 4.5
    try:
        status_loosened, alarms_loosened = anomaly_detector._check_operational_thresholds(reading)
        assert status_loosened != "ABNORMAL_CRITICAL", "Loosening threshold must change detection result"
    finally:
        OPERATIONAL_THRESHOLDS["vibration"]["critical"] = orig_threshold

    status_restored, _ = anomaly_detector._check_operational_thresholds(reading)
    assert status_restored == "ABNORMAL_CRITICAL", "Restored threshold must re-activate critical alarm"

def test_check6_anchor_case_batch_0245_selective_flagging():
    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
    assert b is not None, "Batch BATCH-0245 must exist in database"
    readings = db.query(ProcessReading).filter(ProcessReading.batch_id == b.id).all()
    db.close()

    assert len(readings) > 0, "BATCH-0245 process readings must exist in database"
    df = pd.DataFrame([{
        "timestamp": r.ts.isoformat() if hasattr(r.ts, "isoformat") else str(r.ts),
        "spindle_speed": r.spindle_speed,
        "feed_rate": r.feed_rate,
        "coolant_temp": r.coolant_temp,
        "vibration": r.vibration,
        "tool_usage_cycles": r.tool_usage_cycles,
        "motor_current": r.motor_current or 12.0,
    } for r in readings])

    anomalies = anomaly_detector.detect_anomalies(df)
    flagged_params = {a["parameter"] for a in anomalies}

    assert "vibration" in flagged_params, "BATCH-0245 vibration must be flagged as anomalous"

    assert "tool_usage_cycles" in flagged_params, "BATCH-0245 tool wear must be flagged as anomalous"

    assert "spindle_speed" not in flagged_params, "BATCH-0245 spindle speed was constant and must NOT be flagged"
    assert "feed_rate" not in flagged_params, "BATCH-0245 feed rate was constant and must NOT be flagged"

    assert "coolant_temp" not in flagged_params, "BATCH-0245 coolant temp is within limits and must NOT be flagged"

def test_check7_dataset_counts_and_stratification():
    csv_path = os.path.join(BASE_DIR, "backend", "data", "process", "process_readings.csv")
    batches_path = os.path.join(BASE_DIR, "backend", "data", "production", "batches.csv")

    assert os.path.exists(csv_path), "process_readings.csv must exist"
    assert os.path.exists(batches_path), "batches.csv must exist"

    df = pd.read_csv(csv_path)
    batches = pd.read_csv(batches_path)

    assert len(df) == 780, f"Expected 780 readings, found {len(df)}"
    assert len(batches) == 25, f"Expected 25 batches, found {len(batches)}"

    sc_map = dict(zip(batches["batch_number"], batches["scenario_label"]))
    df["scenario"] = df["batch_id"].map(sc_map)

    scenario_counts = df["scenario"].value_counts().to_dict()
    assert scenario_counts.get("NORMAL_PRODUCTION", 0) >= 300
    assert "SUDDEN_VIBRATION" in scenario_counts
    assert "GRADUAL_DRIFT" in scenario_counts
    assert "MULTIVARIATE_ANOMALY" in scenario_counts
    assert "ANCHOR_TOOL_WEAR" in scenario_counts

def test_check8_independent_evaluation_recomputation_matches_json():
    metrics_path = os.path.join(BASE_DIR, "models", "anomaly_metrics.json")
    preds_path = os.path.join(BASE_DIR, "models", "anomaly_predictions.csv")

    assert os.path.exists(metrics_path), "models/anomaly_metrics.json must exist"
    assert os.path.exists(preds_path), "models/anomaly_predictions.csv must exist"

    with open(metrics_path, "r", encoding="utf-8") as f:
        stored_metrics = json.load(f)

    df_preds = pd.read_csv(preds_path)
    y_true = df_preds["y_true"].values
    norm_mask = (y_true == 0)
    total_normal = int(np.sum(norm_mask))

    model_mapping = {
        "univariate_zscore": "pred_z",
        "isolation_forest": "pred_iso",
        "hybrid_ensemble": "pred_hybrid",
    }

    for m_key, col in model_mapping.items():
        y_pred = df_preds[col].values
        p = round(float(precision_score(y_true, y_pred)), 4)
        r = round(float(recall_score(y_true, y_pred)), 4)
        f = round(float(f1_score(y_true, y_pred)), 4)
        fa_count = int(np.sum((y_pred == 1) & norm_mask))
        fa_rate = round(float((fa_count / total_normal) * 1000.0), 2)

        stored = stored_metrics["models"][m_key]
        assert abs(p - stored["precision"]) < 1e-6, f"{m_key} precision mismatch: {p} vs {stored['precision']}"
        assert abs(r - stored["recall"]) < 1e-6, f"{m_key} recall mismatch: {r} vs {stored['recall']}"
        assert abs(f - stored["f1"]) < 1e-6, f"{m_key} F1 mismatch: {f} vs {stored['f1']}"
        assert abs(fa_rate - stored["false_alarm_rate_per_1000"]) < 1e-6, f"{m_key} false alarm rate mismatch"

def test_check9_methodology_document_exists_and_covers_required_sections():
    doc_path = os.path.join(BASE_DIR, "docs", "anomaly_methodology.md")
    assert os.path.exists(doc_path), "docs/anomaly_methodology.md must exist"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Hybrid Multi-Layer Detection Architecture" in content
    assert "Assumptions" in content
    assert "Baseline Stationarity" in content
    assert "Known Failure Modes" in content
    assert "Synthetic Dataset Disclosure" in content
    assert "0.9542" in content, "Must include accurate measured hybrid precision"
    assert "0.9615" in content, "Must include accurate measured hybrid recall"

def test_check10_output_schema_and_epistemic_labeling():
    df_sample = pd.DataFrame([{
        "timestamp": "2026-10-11T12:00:00",
        "spindle_speed": 1200,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "vibration": 3.85,
        "tool_usage_cycles": 1150,
        "motor_current": 12.0
    }])
    anomalies = anomaly_detector.detect_anomalies(df_sample)
    assert len(anomalies) >= 2

    for a in anomalies:
        for field in ["parameter", "timestamp", "type", "observed_value", "baseline", "score", "method", "epistemic_label"]:
            assert field in a, f"Anomaly record missing field: {field}"
        assert a["epistemic_label"] in ["STATISTICAL_FINDING", "MODEL_PREDICTION", "[STATISTICAL_FINDING]", "[MODEL_PREDICTION]"]
        assert "proven cause" not in a.get("description", "").lower()

def test_check11_robustness_on_edge_cases():
    df_nan = pd.DataFrame({
        "timestamp": ["2026-10-11T10:00:00", "2026-10-11T10:01:00"],
        "vibration": [2.10, np.nan],
        "spindle_speed": [np.nan, 1200.0],
        "feed_rate": [0.20, 0.20],
        "coolant_temp": [24.0, 24.0],
        "tool_usage_cycles": [100, 101]
    })
    res_nan = anomaly_detector.detect_anomalies(df_nan)
    assert isinstance(res_nan, list)

    df_const = pd.DataFrame({
        "timestamp": [f"2026-10-11T10:{i:02d}:00" for i in range(10)],
        "vibration": [2.10] * 10,
        "spindle_speed": [1200.0] * 10,
        "feed_rate": [0.20] * 10,
        "coolant_temp": [24.0] * 10,
        "tool_usage_cycles": [100] * 10
    })
    res_const = anomaly_detector.detect_anomalies(df_const)
    assert isinstance(res_const, list)

    df_short = pd.DataFrame([{
        "timestamp": "2026-10-11T10:00:00",
        "vibration": 2.10,
        "spindle_speed": 1200.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "tool_usage_cycles": 100
    }])
    res_short = anomaly_detector.detect_anomalies(df_short)
    assert isinstance(res_short, list)

    df_unordered = pd.DataFrame({
        "timestamp": ["2026-10-11T10:05:00", "2026-10-11T10:01:00", "2026-10-11T10:01:00"],
        "vibration": [2.10, 2.15, 2.15],
        "spindle_speed": [1200, 1200, 1200],
        "feed_rate": [0.20, 0.20, 0.20],
        "coolant_temp": [24.0, 24.0, 24.0],
        "tool_usage_cycles": [105, 101, 101]
    })
    res_unordered = anomaly_detector.detect_anomalies(df_unordered)
    assert isinstance(res_unordered, list)

def test_check12_ui_api_endpoints_and_screenshots():
    resp = client.get("/api/process/anomalies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    spec = openapi_resp.json()
    paths = spec.get("paths", {})
    assert "/api/process/anomalies" in paths
    assert "/api/process/telemetry" in paths

    shots_dir = os.path.join(BASE_DIR, "docs", "screenshots", "requirement7")
    required_shots = [
        "01_dashboard_machine_anomalies.png",
        "02_process_monitoring_anomalies_view.png",
        "03_anomaly_registry_table.png",
        "04_swagger_process_endpoints.png",
    ]
    for s in required_shots:
        shot_path = os.path.join(shots_dir, s)
        assert os.path.exists(shot_path), f"Screenshot {s} must exist in {shots_dir}"
