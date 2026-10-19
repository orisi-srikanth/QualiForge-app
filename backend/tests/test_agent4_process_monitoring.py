import os
import io
import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Machine, ProcessReading, ProcessBaseline, Anomaly
from backend.app.services.anomaly_detection import (
    anomaly_detector,
    HybridAnomalyDetector,
    OPERATIONAL_THRESHOLDS,
)
from backend.app.agents.process_agent import process_agent
from backend.app.orchestrator.state import WorkflowState
from backend.app.orchestrator.engine import QualityWorkflowOrchestrator, orchestrator
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.core.guardrails import EpistemicLabel

client = TestClient(app)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_agent4_supported_parameters_and_units():
    required_params = [
        "vibration",
        "coolant_temp",
        "pressure",
        "spindle_speed",
        "feed_rate",
        "tool_usage_cycles",
        "cycle_time",
        "motor_current"
    ]
    assert len(required_params) >= 5, "System must support at least 5 parameters"

    for p in required_params:
        assert p in OPERATIONAL_THRESHOLDS, f"Parameter '{p}' must be registered in OPERATIONAL_THRESHOLDS"
        meta = OPERATIONAL_THRESHOLDS[p]
        assert "unit" in meta and len(meta["unit"]) > 0, f"Parameter '{p}' must have a physical unit"
        assert "nominal" in meta, f"Parameter '{p}' must have a nominal engineering baseline"
        assert "source" in meta, f"Parameter '{p}' must reference an engineering standard or manual"

    db = SessionLocal()
    reading = db.query(ProcessReading).first()
    db.close()
    assert reading is not None, "ProcessReading records must exist in database"
    for p in required_params:
        assert hasattr(reading, p), f"ProcessReading model must contain column '{p}'"

def test_agent4_normal_readings_evaluation():
    normal_records = [
        {
            "timestamp": f"2026-10-10 08:{i:02d}:00",
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "coolant_temp": 24.0,
            "vibration": 2.10,
            "tool_usage_cycles": 600 + i,
            "motor_current": 14.5,
            "cycle_time": 45.0,
            "pressure": 5.5
        }
        for i in range(20)
    ]

    analysis = anomaly_detector.analyze_telemetry_series(
        batch_id="BATCH-0001",
        machine_code="CNC-01",
        telemetry_records=normal_records
    )

    crit_anomalies = [a for a in analysis.get("anomalies", []) if a.get("severity") == "CRITICAL"]
    assert len(crit_anomalies) == 0, "Normal telemetry must produce zero critical anomalies"
    assert analysis["vibration_status"] == "NORMAL"
    assert analysis["tool_status"] == "NORMAL"
    assert analysis["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert analysis["autonomous_actions_prohibited"] is True

def test_agent4_configured_thresholds_breach():
    breach_records = [
        {
            "timestamp": "2026-10-10 08:00:00",
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "coolant_temp": 30.5,
            "vibration": 3.82,
            "tool_usage_cycles": 1150,
            "motor_current": 14.5,
            "cycle_time": 45.0,
            "pressure": 5.5
        }
    ]

    analysis = anomaly_detector.analyze_telemetry_series(
        batch_id="BATCH-0245",
        machine_code="CNC-04",
        telemetry_records=breach_records
    )

    anomalies = analysis.get("anomalies", [])
    params_flagged = {a["parameter"] for a in anomalies}

    assert "vibration" in params_flagged, "Vibration 3.82 mm/s must be flagged"
    assert "tool_usage_cycles" in params_flagged, "Tool wear 1150 cycles must be flagged"
    assert "coolant_temp" in params_flagged, "Coolant temp 30.5 °C must be flagged"

    vib_anom = [a for a in anomalies if a["parameter"] == "vibration"][0]
    assert vib_anom["observed_value"] == 3.82
    assert vib_anom["threshold_limit"] == 3.5
    assert vib_anom["baseline_mean"] == 2.1
    assert vib_anom["severity"] == "CRITICAL"
    assert vib_anom["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert vib_anom["epistemic_label"] == EpistemicLabel.STATISTICAL_FINDING.value

def test_agent4_high_and_low_abnormal_readings():
    low_speed_data = [{
        "timestamp": "2026-10-10 08:00:00",
        "spindle_speed": 1050.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "vibration": 2.10,
        "tool_usage_cycles": 600,
        "motor_current": 14.5,
        "cycle_time": 45.0,
        "pressure": 5.5
    }]
    res_low = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-LOW-SPEED",
        machine_code="CNC-04",
        telemetry_records=low_speed_data
    )
    speed_anoms_low = [a for a in res_low["anomalies"] if a["parameter"] == "spindle_speed"]
    assert len(speed_anoms_low) == 1, "Spindle speed below 1100 RPM must trigger threshold anomaly"
    assert speed_anoms_low[0]["observed_value"] == 1050.0

    high_speed_data = [{
        "timestamp": "2026-10-10 08:00:00",
        "spindle_speed": 1350.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "vibration": 2.10,
        "tool_usage_cycles": 600,
        "motor_current": 14.5,
        "cycle_time": 45.0,
        "pressure": 5.5
    }]
    res_high = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-HIGH-SPEED",
        machine_code="CNC-04",
        telemetry_records=high_speed_data
    )
    speed_anoms_high = [a for a in res_high["anomalies"] if a["parameter"] == "spindle_speed"]
    assert len(speed_anoms_high) == 1, "Spindle speed above 1300 RPM must trigger threshold anomaly"
    assert speed_anoms_high[0]["observed_value"] == 1350.0

    low_press_data = [{
        "timestamp": "2026-10-10 08:00:00",
        "spindle_speed": 1200.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "vibration": 2.10,
        "tool_usage_cycles": 600,
        "motor_current": 14.5,
        "cycle_time": 45.0,
        "pressure": 3.5
    }]
    res_press = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-LOW-PRESS",
        machine_code="CNC-04",
        telemetry_records=low_press_data
    )
    press_anoms = [a for a in res_press["anomalies"] if a["parameter"] == "pressure"]
    assert len(press_anoms) == 1, "Pressure below 4.0 bar must trigger threshold anomaly"
    assert press_anoms[0]["observed_value"] == 3.5

    high_motor_data = [{
        "timestamp": "2026-10-10 08:00:00",
        "spindle_speed": 1200.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "vibration": 2.10,
        "tool_usage_cycles": 600,
        "motor_current": 23.5,
        "cycle_time": 45.0,
        "pressure": 5.5
    }]
    res_motor = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-HIGH-MOTOR",
        machine_code="CNC-04",
        telemetry_records=high_motor_data
    )
    motor_anoms = [a for a in res_motor["anomalies"] if a["parameter"] == "motor_current"]
    assert len(motor_anoms) == 1, "Motor current above 22.0 A must trigger threshold anomaly"
    assert motor_anoms[0]["observed_value"] == 23.5

def test_agent4_sudden_changes_step_shift():
    step_data = []
    for i in range(10):
        step_data.append({
            "timestamp": f"2026-10-10 08:{i:02d}:00",
            "vibration": 2.10,
            "tool_usage_cycles": 600,
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "coolant_temp": 24.0,
            "motor_current": 14.5,
            "cycle_time": 45.0,
            "pressure": 5.5
        })
    step_data.append({
        "timestamp": "2026-10-10 08:10:00",
        "vibration": 3.25,
        "tool_usage_cycles": 600,
        "spindle_speed": 1200.0,
        "feed_rate": 0.20,
        "coolant_temp": 24.0,
        "motor_current": 14.5,
        "cycle_time": 45.0,
        "pressure": 5.5
    })

    analysis = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-STEP-CHANGE",
        machine_code="CNC-04",
        telemetry_records=step_data
    )

    sudden_anoms = [a for a in analysis["anomalies"] if a.get("type") == "sudden_change"]
    assert len(sudden_anoms) >= 1, "Sudden step change must be detected by rolling Z-score"
    assert sudden_anoms[0]["score"] >= 3.0, "Score must exceed 3.0 sigma"
    assert sudden_anoms[0]["method"] == "rolling_z_score_step_change"

def test_agent4_gradual_drift_cusum_ewma_trend():
    drift_data = []
    for i in range(15):
        drift_data.append({
            "timestamp": f"2026-10-10 08:{i:02d}:00",
            "vibration": round(2.10 + i * 0.08, 2),
            "tool_usage_cycles": 600 + i * 10,
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "coolant_temp": round(24.0 + i * 0.1, 1),
            "motor_current": round(14.5 + i * 0.1, 1),
            "cycle_time": 45.0,
            "pressure": 5.5
        })

    analysis = anomaly_detector.analyze_telemetry_series(
        batch_id="TEST-DRIFT",
        machine_code="CNC-04",
        telemetry_records=drift_data
    )

    assert analysis["drift_detected"] is True, "Gradual drift must be flagged"
    drift_anoms = [a for a in analysis["anomalies"] if a.get("type") == "drift"]
    assert len(drift_anoms) >= 1, "Drift anomaly record must be created"
    assert drift_anoms[0]["method"] == "cusum_ewma_drift_detector"

    trends = analysis.get("trends", {})
    assert "vibration" in trends
    assert trends["vibration"]["slope"] > 0, "Vibration slope must be positive"
    assert trends["vibration"]["direction"] == "INCREASING_DRIFT"

def test_agent4_insufficient_baseline_data_and_zero_variance():
    detector = anomaly_detector

    score_identical = detector.compute_robust_z_score(val=2.1, median=2.1, mad=0.0)
    assert score_identical == 0.0, "Zero MAD with identical value must yield 0.0 z-score"
    score_deviant = detector.compute_robust_z_score(val=2.8, median=2.1, mad=0.0)
    assert score_deviant == 5.0, "Zero MAD with deviating value must cap safely without ZeroDivisionError"

    constant_series = np.array([2.1, 2.1, 2.1, 2.1, 2.1])
    cusum_res = detector.compute_cusum(series=constant_series, target=2.1, sigma=0.0)
    assert cusum_res.alarm_triggered is False, "Zero variance nominal series must not trigger CUSUM alarm"

    ewma_res = detector.compute_ewma(series=constant_series, target=2.1, sigma=0.0)
    assert ewma_res.alarm_triggered is False, "Zero variance nominal series must not trigger EWMA alarm"

    short_df = pd.DataFrame([
        {"timestamp": "2026-10-10 08:00:00", "vibration": 2.1},
        {"timestamp": "2026-10-10 08:01:00", "vibration": 2.1}
    ])
    short_trends = detector.calculate_trend_statistics(short_df)
    assert short_trends == {}, "Trend calculation with n < 3 must return empty dict without crashing"

def test_agent4_missing_values_and_unsupported_units():
    raw_data = [
        {"timestamp": "2026-10-10 08:00:00", "vibration": None, "coolant_temp": float("nan")},
        {"timestamp": "2026-10-10 08:01:00", "vibration_in_s": 0.1, "coolant_temp": 24.0},
        {"timestamp": "2026-10-10 08:02:00", "vibration": 2.1, "coolant_temp_f": 77.0},
        {"timestamp": "2026-10-10 08:03:00", "vibration": 2.1, "pressure_psi": 79.77},
        {"timestamp": "2026-10-10 08:04:00", "vibration": 2.1, "vibration_unit_unsupported": "cubits_per_minute"}
    ]

    cleaned, warnings = anomaly_detector.validate_and_clean_telemetry(raw_data)

    assert len(cleaned) == 5, "All 5 records must be cleaned and retained"
    assert len(warnings) > 0, "Warnings must be reported for all data defects"

    assert cleaned[0]["vibration"] == 2.1, "Missing vibration must be imputed to baseline"
    assert cleaned[0]["coolant_temp"] == 24.0, "NaN coolant temp must be imputed to baseline"

    assert abs(cleaned[1]["vibration"] - 2.54) < 0.05, "Vibration in/s must be converted to mm/s"

    assert abs(cleaned[2]["coolant_temp"] - 25.0) < 0.1, "Temperature °F must be converted to °C"

    assert abs(cleaned[3]["pressure"] - 5.5) < 0.1, "Pressure psi must be converted to bar"

    unsupported_warnings = [w for w in warnings if "cubits_per_minute" in w or "Unsupported unit" in w]
    assert len(unsupported_warnings) >= 1, "Unsupported unit must generate a structured warning"

def test_agent4_unknown_batches_rejected():
    csv_content = """timestamp,spindle_speed,feed_rate,coolant_temp,vibration,tool_usage_cycles,motor_current,cycle_time,pressure
2026-10-10 08:00:00,1200.0,0.20,24.0,2.10,600,14.5,45.0,5.5
"""
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(
        "/api/process/upload",
        files=files,
        data={"batch_id": "NONEXISTENT-BATCH-9999", "machine_id": "CNC-04"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_agent4_incorrect_machine_batch_association():
    csv_content = """timestamp,spindle_speed,feed_rate,coolant_temp,vibration,tool_usage_cycles,motor_current,cycle_time,pressure
2026-10-10 08:00:00,1200.0,0.20,24.0,2.10,600,14.5,45.0,5.5
"""
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(
        "/api/process/upload",
        files=files,
        data={"batch_id": "BATCH-0245", "machine_id": "CNC-01"}
    )
    assert res.status_code == 400
    assert "machine mismatch" in res.json()["detail"].lower()

def test_agent4_persistence_and_retrieval_of_findings():
    csv_content = """timestamp,spindle_speed,feed_rate,coolant_temp,vibration,tool_usage_cycles,motor_current,cycle_time,pressure
2026-10-10 10:00:00,1200.0,0.20,24.0,2.10,600,14.5,45.0,5.5
2026-10-10 10:01:00,1200.0,0.20,24.0,2.15,605,14.5,45.0,5.5
2026-10-10 10:02:00,1200.0,0.20,24.0,3.85,1150,18.0,46.0,5.5
"""
    files = {"file": ("telemetry_persist_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(
        "/api/process/upload",
        files=files,
        data={"batch_id": "BATCH-0245", "machine_id": "CNC-04"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["records_saved"] == 3
    assert data["anomalies_detected"] >= 2
    assert data["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert data["autonomous_actions_prohibited"] is True

    db = SessionLocal()
    b_obj = db.query(Batch).filter_by(batch_number="BATCH-0245").first()
    assert b_obj is not None
    persisted_anomalies = db.query(Anomaly).filter(Anomaly.batch_id == b_obj.id).all()
    assert len(persisted_anomalies) >= 2, "Anomalies must be persisted in quality_system.db anomalies table"
    db.close()

    get_res = client.get("/api/process/anomalies?batch_id=BATCH-0245&machine=CNC-04")
    assert get_res.status_code == 200
    retrieved_anomalies = get_res.json()
    assert len(retrieved_anomalies) >= 2
    for a in retrieved_anomalies:
        assert a["review_status"] == "HUMAN_REVIEW_REQUIRED"
        assert a["epistemic_label"] in ["STATISTICAL_FINDING", "MODEL_PREDICTION"]

def test_agent4_multivariate_isolation_forest_and_score_interpretation():
    detector = anomaly_detector
    assert hasattr(detector, "detect_multivariate_anomalies")

    np.random.seed(42)
    n_pts = 100
    train_df = pd.DataFrame({
        "spindle_speed": np.random.normal(1200.0, 5.0, n_pts),
        "feed_rate": np.random.normal(0.20, 0.005, n_pts),
        "coolant_temp": np.random.normal(24.0, 0.5, n_pts),
        "vibration": np.random.normal(2.1, 0.05, n_pts),
        "motor_current": np.random.normal(14.5, 0.2, n_pts)
    })
    detector.train_multivariate_model(train_df)

    test_df = train_df.copy()
    test_df.iloc[-1] = [1160.0, 0.22, 24.5, 2.2, 17.5]

    findings = detector.detect_multivariate_anomalies(test_df)
    for f in findings:
        score = f["score"]
        assert isinstance(score, float)
        assert f["epistemic_label"] == EpistemicLabel.MODEL_PREDICTION.value

def test_agent4_workflow_availability_to_downstream_agents():
    batch_meta = {
        "batch_id": "BATCH-0245",
        "machine": "CNC-04",
        "part_name": "Precision Ground Shaft"
    }
    state = orchestrator.run_full_pipeline(batch_meta=batch_meta)

    assert state.process_report is not None, "WorkflowState must contain process_report"
    assert state.process_report.vibration_current >= 3.5, "Vibration current must exceed 3.5 mm/s"
    assert state.process_report.tool_cycles_current >= 1000, "Tool cycles current must exceed 1000"
    assert state.has_anomalies is True, "WorkflowState.has_anomalies must be True"

    assert state.rca_report is not None, "Downstream RCA report must be generated"
    top_hypo = state.rca_report.ranked_hypotheses[0]
    supporting_evidence = " ".join([e if isinstance(e, str) else e.get("desc", "") for e in top_hypo.supporting_evidence])
    assert "vibration" in supporting_evidence.lower() or "tool" in supporting_evidence.lower()

    pdf_bytes = generate_quality_pdf_report(state.model_dump())
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")

def test_agent4_prevention_of_prohibited_autonomous_actions():
    prohibited_method_names = [
        "halt_machine", "emergency_stop", "modify_cnc_parameters", "override_gcode",
        "write_plc", "release_batch", "reject_batch", "change_feed_override"
    ]
    for method_name in prohibited_method_names:
        assert not hasattr(process_agent, method_name), f"Agent 4 must NOT implement autonomous control method '{method_name}'"

    db = SessionLocal()
    b = db.query(Batch).filter_by(batch_number="BATCH-0245").first()
    assert b.status == "QUALITY_HOLD", "Batch status must remain QUALITY_HOLD without autonomous release or reject"
    db.close()

    rep = process_agent.analyze_telemetry_series(batch_id="BATCH-0245", machine="CNC-04")
    assert str(rep["report"].certainty).lower() in ["statistical finding", "statistical_finding", "certaintylevel.statistical_finding"]

def test_agent4_process_telemetry_sample_csv_integration():
    sample_path = os.path.join(BASE_DIR, "process_telemetry_sample.csv")
    assert os.path.exists(sample_path), "process_telemetry_sample.csv must exist in workspace"

    df = pd.read_csv(sample_path)
    assert len(df) == 60, "Dataset must contain 60 sequential readings"

    expected_cols = [
        "timestamp", "spindle_speed", "feed_rate", "coolant_temp",
        "vibration", "tool_usage_cycles", "motor_current", "cycle_time", "pressure"
    ]
    for c in expected_cols:
        assert c in df.columns, f"Column '{c}' must exist in process_telemetry_sample.csv"

    res = anomaly_detector.analyze_telemetry_series(
        batch_id="BATCH-0245",
        machine_code="CNC-04",
        telemetry_records=df.to_dict(orient="records")
    )

    assert res["anomalies_detected"] >= 2, "Must detect vibration and tool wear anomalies"
    assert res["vibration_status"] == "ABNORMAL_CRITICAL"
    assert res["tool_status"] == "CRITICAL_EXCEEDED"
    assert res["drift_detected"] is True
    assert res["review_status"] == "HUMAN_REVIEW_REQUIRED"
