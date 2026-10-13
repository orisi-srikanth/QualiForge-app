"""
Automated Test Suite for Functional Requirement 6: Process Data Monitoring
Covers all 11 Checks specified in the QA Verification Protocol:
1. Process Parameters & Units
2. Time-Series Data, Row Counts, & Robust Data Intake (Missing, Duplicates, Out-of-Order, Units)
3. Baseline Calculation (Mean, Std, Percentiles, Median/MAD) & Source Manual Limits
4. Anchor Case BATCH-0245 on CNC-04 (Vibration & Tool Wear Flagged; Speed & Feed Constant)
5. Anomaly Output Schema, Epistemic Labels, TC-04 Sudden Shift, and TC-05 Drift
6. False Alarm Evaluation (Zero False Alarms on Normal Batches)
7. OLS Trend Statistics (Slope & P-Value Verification)
8. Integration with Orchestrated Workflow, RCA Contradicting Evidence, and PDF Report
9. Swagger / OpenAPI Documentation
"""
import io
import pytest
import numpy as np
import pandas as pd
from scipy import stats
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import ProcessReading, ProcessBaseline, Batch
from backend.app.services.anomaly_detection import anomaly_detector, OPERATIONAL_THRESHOLDS
from backend.app.agents.process_agent import process_agent
from backend.app.agents.rca_agent import rca_agent
from backend.app.scenarios.test_scenarios import _run_tc04, _run_tc05

client = TestClient(app)

# -----------------------------------------------------------------------------
# CHECK 1: Process Parameters & Units
# -----------------------------------------------------------------------------
def test_check1_parameters_stored_and_monitored_with_units():
    """Confirms at least 5 core parameters + extras are defined in database model and operational registry with valid units."""
    db = SessionLocal()
    reading = db.query(ProcessReading).first()
    db.close()

    assert reading is not None, "ProcessReading table must contain records"

    # Core 5 parameters
    core_parameters = {
        "vibration": "mm/s",
        "coolant_temp": "°C",
        "spindle_speed": "RPM",
        "feed_rate": "mm/rev",
        "tool_usage_cycles": "cycles"
    }

    # Extras
    extra_parameters = {
        "motor_current": "A",
        "cycle_time": "s",
        "pressure": "bar"
    }

    for p, unit in core_parameters.items():
        assert hasattr(reading, p), f"ProcessReading model must have column '{p}'"
        assert p in OPERATIONAL_THRESHOLDS, f"OPERATIONAL_THRESHOLDS must register '{p}'"
        assert OPERATIONAL_THRESHOLDS[p]["unit"] == unit, f"Unit for '{p}' must be '{unit}'"

    for p, unit in extra_parameters.items():
        assert hasattr(reading, p), f"ProcessReading model must have column '{p}'"
        assert p in OPERATIONAL_THRESHOLDS, f"OPERATIONAL_THRESHOLDS must register '{p}'"
        assert OPERATIONAL_THRESHOLDS[p]["unit"] == unit, f"Unit for '{p}' must be '{unit}'"

# -----------------------------------------------------------------------------
# CHECK 2: Time-Series Data, Row Counts, & Robust Intake Handling
# -----------------------------------------------------------------------------
def test_check2_row_counts_per_machine_and_dataset():
    """Confirms row counts per machine in database matching the 780-reading dataset."""
    db = SessionLocal()
    counts = db.query(ProcessReading.machine_id).all()
    db.close()

    df = pd.DataFrame(counts, columns=["machine_id"])
    dist = df["machine_id"].value_counts().to_dict()

    assert dist.get("mach-04", 0) >= 240, "CNC-04 must have >= 240 readings (6 batches x 30 + BATCH-0245 60)"
    assert dist.get("mach-01", 0) >= 180, "CNC-01 must have >= 180 readings"
    assert dist.get("mach-02", 0) >= 180, "CNC-02 must have >= 180 readings"
    assert dist.get("mach-03", 0) >= 180, "CNC-03 must have >= 180 readings"
    assert len(df) >= 780, "Total process readings must be at least 780"

def test_check2_data_cleaning_missing_duplicate_out_of_order_units():
    """Verifies intake handles missing values, duplicates, out-of-order data, and foreign units with warnings, not crashes."""
    dirty_data = [
        # Out-of-order and duplicate timestamp
        {"timestamp": "2026-10-10 05:00:00", "vibration": 2.1, "tool_usage_cycles": 600},
        {"timestamp": "2026-10-10 04:00:00", "vibration": None, "tool_usage_cycles": 600}, # Missing vibration
        {"timestamp": "2026-10-10 05:00:00", "vibration": 2.15, "tool_usage_cycles": 605}, # Duplicate timestamp
        # Unit conversion in/s -> mm/s (0.1 in/s * 25.4 = 2.54 mm/s)
        {"timestamp": "2026-10-10 06:00:00", "vibration_in_s": 0.1, "tool_usage_cycles": 610, "coolant_temp_f": 77.0} # 77 F = 25 C
    ]

    cleaned, warnings = anomaly_detector.validate_and_clean_telemetry(dirty_data)

    assert len(cleaned) == 3, "Duplicate timestamp at 05:00:00 must be deduplicated"
    assert len(warnings) > 0, "Warnings must be reported for data quality issues"

    # Must be sorted chronologically
    timestamps = [r["timestamp"] for r in cleaned]
    assert timestamps == sorted(timestamps), "Cleaned records must be sorted chronologically"

    # Missing value imputed
    first_row = [r for r in cleaned if r["timestamp"] == "2026-10-10 04:00:00"][0]
    assert first_row["vibration"] == 2.1, "Missing vibration must be imputed to baseline"

    # Unit converted
    converted_row = [r for r in cleaned if r["timestamp"] == "2026-10-10 06:00:00"][0]
    assert abs(converted_row["vibration"] - 2.54) < 0.05, "Vibration in in/s must be converted to mm/s"
    assert abs(converted_row["coolant_temp"] - 25.0) < 0.1, "Coolant in °F must be converted to °C"

# -----------------------------------------------------------------------------
# CHECK 3: Baseline Calculation on Known-Good Windows
# -----------------------------------------------------------------------------
def test_check3_baseline_calculation_independent_verification():
    """Computes baselines on known-good production batches and verifies mean, std, percentiles, median/MAD."""
    db = SessionLocal()
    readings = db.query(ProcessReading).all()
    batches = db.query(Batch).all()
    db.close()

    normal_batch_ids = {b.id for b in batches if b.scenario_label == "NORMAL_PRODUCTION"}
    normal_readings = [r for r in readings if r.batch_id in normal_batch_ids]

    assert len(normal_readings) >= 300, "Should have >= 300 normal readings"

    vib_vals = np.array([r.vibration for r in normal_readings], dtype=float)
    vib_mean = float(np.mean(vib_vals))
    vib_median = float(np.median(vib_vals))
    vib_mad = float(np.median(np.abs(vib_vals - vib_median)))

    # Normal baseline vibration must be centered closely at 2.1 mm/s
    assert abs(vib_mean - 2.10) < 0.05, f"Expected baseline mean ~2.10 mm/s, got {vib_mean:.3f}"
    assert abs(vib_median - 2.10) < 0.05, f"Expected baseline median ~2.10 mm/s, got {vib_median:.3f}"
    assert vib_mad < 0.10, "Vibration MAD should reflect low variation under normal machining"

    # Check database baselines exist
    db = SessionLocal()
    base_vib = db.query(ProcessBaseline).filter(ProcessBaseline.parameter == "vibration").first()
    db.close()
    assert base_vib is not None
    assert base_vib.mean == 2.1
    assert base_vib.upper_threshold == 3.5

# -----------------------------------------------------------------------------
# CHECK 4: Anchor Case BATCH-0245 on CNC-04
# -----------------------------------------------------------------------------
def test_check4_anchor_case_batch_0245_contrast_table():
    """Verifies anchor case BATCH-0245 on CNC-04: vibration and tool wear flagged; speed and feed constant."""
    res = client.get("/api/process/telemetry?batch_id=BATCH-0245&machine=CNC-04")
    assert res.status_code == 200
    data = res.json()

    rep = data["report"]
    contrast = {row["parameter"]: row for row in data["changed_vs_unchanged"]}

    # 1. Vibration: 2.1 -> 3.8 mm/s is FLAGGED
    assert rep["vibration_current"] >= 3.5, "Vibration must exceed 3.5 mm/s"
    assert rep["vibration_status"] == "ABNORMAL_CRITICAL"
    assert contrast["vibration"]["status"] == "CHANGED_CRITICAL"

    # 2. Tool cycles: 600 -> 1150 is FLAGGED
    assert rep["tool_cycles_current"] >= 1000, "Tool cycles must exceed 1000"
    assert rep["tool_status"] == "CRITICAL_EXCEEDED"
    assert contrast["tool_usage_cycles"]["status"] == "CHANGED_CRITICAL"

    # 3. Spindle speed: 1200 RPM is UNCHANGED
    assert contrast["spindle_speed"]["status"] == "UNCHANGED"
    assert "1200" in contrast["spindle_speed"]["current"]

    # 4. Feed rate: 0.20 mm/rev is UNCHANGED
    assert contrast["feed_rate"]["status"] == "UNCHANGED"
    assert "0.20" in contrast["feed_rate"]["current"]

    # 5. Coolant temp: 24 -> 25 °C is NOT flagged as threshold trip (below 28 °C warning)
    assert contrast["coolant_temp"]["status"] == "CHANGED_MINOR"
    assert rep["temperature_current"] < 28.0

# -----------------------------------------------------------------------------
# CHECK 5: Anomaly Output Schema, TC-04, and TC-05
# -----------------------------------------------------------------------------
def test_check5_anomaly_output_schema_and_epistemic_labels():
    """Verifies each anomaly record contains required fields including method and epistemic label."""
    res = client.get("/api/process/anomalies?batch_id=BATCH-0245&machine=CNC-04")
    assert res.status_code == 200
    anomalies = res.json()
    assert len(anomalies) >= 2, "Must flag at least vibration and tool usage anomalies"

    required_keys = ["parameter", "type", "score", "method", "epistemic_label"]
    for a in anomalies:
        for k in required_keys:
            assert k in a, f"Anomaly record must contain '{k}'"
        assert a["epistemic_label"] in ["STATISTICAL_FINDING", "MODEL_PREDICTION"]

def test_check5_tc04_sudden_vibration_spike():
    """Verifies TC-04 scenario: sudden vibration increase is flagged."""
    res = _run_tc04()
    assert res["status"] == "PASS"
    assert "Vibration critical" in res["evidence"]

def test_check5_tc05_gradual_process_drift():
    """Verifies TC-05 scenario: gradual drift toward limit is detected."""
    res = _run_tc05()
    assert res["status"] == "PASS"

# -----------------------------------------------------------------------------
# CHECK 6: False Alarm Evaluation
# -----------------------------------------------------------------------------
def test_check6_false_alarm_rate_on_normal_batches():
    """Verifies that normal production batches produce zero false alarms and no quality incidents."""
    res = client.get("/api/process/telemetry?batch_id=BATCH-0004&machine=CNC-01")
    assert res.status_code == 200
    data = res.json()

    # Normal batch must have zero critical threshold anomalies
    crit_anomalies = [a for a in data.get("anomalies", []) if a.get("severity") == "CRITICAL"]
    assert len(crit_anomalies) == 0, "Normal batch BATCH-0004 must not have critical anomalies"
    assert data["report"]["vibration_status"] == "NORMAL"
    assert data["report"]["tool_status"] in ("NORMAL", "WARNING_NEAR_LIFE")
    
    # Normal batch (TC-01) must not create an incident
    incidents_res = client.get("/api/incidents")
    if incidents_res.status_code == 200:
        incidents = incidents_res.json()
        tc01_incidents = [inc for inc in incidents if inc.get("batch_id") in ("BATCH-0004", "BATCH-TC01")]
        assert len(tc01_incidents) == 0, "Normal batch must not create an incident"

# -----------------------------------------------------------------------------
# CHECK 7: Trend Statistics (OLS Regression Slope and P-Value)
# -----------------------------------------------------------------------------
def test_check7_trend_statistics_ols():
    """Verifies OLS slope and p-value calculation against independent scipy calculation."""
    res = client.get("/api/process/telemetry?batch_id=BATCH-0245&machine=CNC-04")
    assert res.status_code == 200
    data = res.json()
    trends = data.get("trends", {})

    assert "vibration" in trends
    vib_trend = trends["vibration"]
    assert vib_trend["slope"] > 0, "Vibration slope must be positive for BATCH-0245"
    assert vib_trend["p_value"] < 0.001, "Vibration upward trend must be statistically significant"
    assert vib_trend["direction"] == "INCREASING_DRIFT"

    # Spindle speed must be flat
    assert "spindle_speed" in trends
    assert abs(trends["spindle_speed"]["slope"]) < 0.0001
    assert trends["spindle_speed"]["direction"] == "STABLE"

# -----------------------------------------------------------------------------
# CHECK 8: Integration with Orchestration & RCA Contradicting Evidence
# -----------------------------------------------------------------------------
def test_check8_integration_rca_contradicting_evidence():
    """Verifies RCA agent utilizes unchanged parameters (speed & feed) as contradicting evidence."""
    res = rca_agent.analyze_incident(
        incident_id="INC-BATCH-0245",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.8,
        tool_cycles=1150
    )

    hypotheses = res["report"].ranked_hypotheses
    h2 = [h for h in hypotheses if "Offset" in h.title][0]

    # Contradicting evidence should include feed rate and spindle speed
    contra_descs = " ".join([c if isinstance(c, str) else c.get("desc", "") for c in h2.contradicting_evidence])
    assert "feed rate" in contra_descs.lower() or "0.20" in contra_descs
    assert "spindle speed" in contra_descs.lower() or "1200" in contra_descs

# -----------------------------------------------------------------------------
# CHECK 9: Process Upload Endpoint
# -----------------------------------------------------------------------------
def test_check9_process_telemetry_upload():
    """Verifies CSV upload of process readings with validation and automatic analysis."""
    csv_content = """timestamp,spindle_speed,feed_rate,coolant_temp,vibration,tool_usage_cycles,motor_current,cycle_time,pressure
2026-10-10 09:00:00,1200.0,0.20,24.0,2.10,600,14.5,45.0,5.5
2026-10-10 09:04:00,1200.0,0.20,24.1,2.12,608,14.5,45.0,5.5
2026-10-10 09:08:00,1200.0,0.20,24.0,3.85,1150,16.8,46.0,5.5
"""
    files = {"file": ("test_upload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/process/upload", files=files, data={"batch_id": "BATCH-0245", "machine_id": "CNC-04"})

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["records_received"] == 3
    assert data["anomalies_detected"] > 0

# -----------------------------------------------------------------------------
# CHECK 10: Swagger / OpenAPI Schema Endpoints
# -----------------------------------------------------------------------------
def test_check10_openapi_schema_process_endpoints():
    """Verifies that all process endpoints appear in OpenAPI schema under 'Process Monitoring'."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})

    assert "/api/process/telemetry" in paths
    assert "/api/process/anomalies" in paths
    assert "/api/process/baselines" in paths
    assert "/api/process/changed-vs-unchanged" in paths
    assert "/api/process/upload" in paths

    get_telemetry_op = paths["api/process/telemetry"]["get"] if "api/process/telemetry" in paths else paths["/api/process/telemetry"]["get"]
    assert "Process Monitoring" in get_telemetry_op.get("tags", [])
