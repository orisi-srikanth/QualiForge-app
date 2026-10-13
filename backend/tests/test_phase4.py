"""
Unit Tests for Phase 4: Machine Learning & Computer Vision
Tests CV Inference, Grad-CAM integration, and Hybrid Anomaly Detection.
"""
import os
import pytest
from backend.app.ml.cv.infer import vision_inference
from backend.app.services.anomaly import anomaly_detector
from backend.app.core.guardrails import EpistemicLabel

def test_cv_inference_scratch_detection():
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "IMG-001.png")
    )
    assert os.path.exists(sample_path), f"Sample scratch image must exist at {sample_path}"

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "annotated"))
    res = vision_inference.predict(sample_path, image_id="IMG-001", output_dir=out_dir)

    assert res["image_id"] == "IMG-001"
    assert res["data_source"] == "synthetic"
    assert res["defect_detected"] is True
    assert res["defect_type"] == "surface_scratch"
    assert res["confidence"] >= 0.70
    assert res["bbox"] is not None
    assert res["label"] == EpistemicLabel.MODEL_PREDICTION.value

def test_cv_inference_normal_conforming():
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "shaft_normal.png")
    )
    if not os.path.exists(sample_path):
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "metal_nut_normal.png")
        )
    assert os.path.exists(sample_path), f"Sample normal image must exist at {sample_path}"
    res = vision_inference.predict(sample_path, image_id="IMG-TEST-02")
    assert res["data_source"] in ["synthetic", "real_proxy"]
    assert res["label"] == EpistemicLabel.MODEL_PREDICTION.value

def test_no_leakage_between_splits():
    """Verify strictly zero SHA-256 and pHash leakage across train, val, test, and hard test splits."""
    from ml.cv.make_splits import verify_shaft_splits
    stats = verify_shaft_splits()
    assert stats["sha256_overlap_count"] == 0, "SHA-256 overlap must be strictly 0"
    assert stats["phash_overlap_count"] == 0, "Perceptual hash overlap must be strictly 0"
    assert stats["train_count"] == 1764
    assert stats["val_count"] == 378
    assert stats["test_count"] == 378
    assert stats["hard_test_count"] == 300

def test_cv_hard_split_performance_drop():
    """Verify evaluation records Macro-F1 drop between normal and hard test splits."""
    import json
    metrics_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "cv_metrics.json"))
    assert os.path.exists(metrics_path), "cv_metrics.json must exist"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    
    drop = metrics["performance_drop_normal_vs_hard"]
    assert drop["macro_f1_drop"] > 0.40, "Expected significant Macro-F1 drop under unseen severe corruptions"
    assert drop["accuracy_drop"] > 0.40, "Expected significant accuracy drop under unseen severe corruptions"
    assert metrics["normal_test_split"]["macro_f1"] > 0.90, "Normal test Macro-F1 must be > 0.90"

def test_cv_honest_disclosure_payload():
    """Verify vision inspection response carries data_source: 'synthetic' and honest disclosure."""
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "IMG-001.png")
    )
    res = vision_inference.predict(sample_path, image_id="IMG-001")
    assert res.get("data_source") == "synthetic"
    assert "metrics" in res
    assert res["metrics"].get("uncalibrated_probability") is True


def test_anomaly_detector_anchor_telemetry():
    telemetry = [
        {"ts": "02:00", "vibration": 2.1, "tool_usage_cycles": 600, "spindle_speed": 1200.0, "feed_rate": 0.20, "coolant_temp": 24.0, "motor_current": 14.5, "cycle_time": 45.0},
        {"ts": "02:10", "vibration": 2.2, "tool_usage_cycles": 620, "spindle_speed": 1200.0, "feed_rate": 0.20, "coolant_temp": 24.1, "motor_current": 14.6, "cycle_time": 45.0},
        {"ts": "02:20", "vibration": 3.8, "tool_usage_cycles": 1150, "spindle_speed": 1200.0, "feed_rate": 0.20, "coolant_temp": 25.0, "motor_current": 16.8, "cycle_time": 46.2},
    ]
    res = anomaly_detector.analyze_telemetry_series(
        batch_id="BATCH-0245",
        machine_code="CNC-04",
        telemetry_records=telemetry
    )
    assert res["anomalies_detected"] > 0
    assert res["vibration_status"] == "ABNORMAL_CRITICAL"
    assert res["tool_status"] == "CRITICAL_EXCEEDED"
    assert res["vibration_current"] == 3.8
    assert res["tool_cycles_current"] == 1150

    # Test changed vs unchanged table
    tbl = res["changed_vs_unchanged"]
    spindle_entry = next(e for e in tbl if e["parameter"] == "spindle_speed")
    feed_entry = next(e for e in tbl if e["parameter"] == "feed_rate")
    vib_entry = next(e for e in tbl if e["parameter"] == "vibration")

    assert spindle_entry["status"] == "UNCHANGED"
    assert "rules out" in spindle_entry["evidence_role"].lower()
    assert feed_entry["status"] == "UNCHANGED"
    assert vib_entry["status"] == "CHANGED_CRITICAL"
