"""
Unit Tests for Phase 2: Data Generation and Anchor Scenario Verification
"""
import os
import json
import pytest
from decimal import Decimal
from backend.app.db.session import SessionLocal
from backend.app.db.models import Batch, Measurement, ProcessReading, HistoricalIncident

def test_anchor_scenario_batch_and_spec():
    db = SessionLocal()
    try:
        b245 = db.query(Batch).filter_by(batch_number="BATCH-0245").first()
        assert b245 is not None, "BATCH-0245 must exist in database"
        assert b245.product.part_number == "PS-2026-101"
        assert b245.quantity == 500
        assert b245.shift == "Night Shift"
        assert b245.scenario_label == "ANCHOR_TOOL_WEAR"

        # Check measurements
        measurements = db.query(Measurement).filter_by(batch_id=b245.id).order_by(Measurement.component_id).all()
        assert len(measurements) == 5, f"Expected exactly 5 measurements for anchor sample, found {len(measurements)}"

        expected_map = {
            "P001": 50.01,
            "P002": 50.03,
            "P003": 50.06,
            "P004": 50.08,
            "P005": 50.07
        }
        for m in measurements:
            exp_val = expected_map[m.component_id]
            assert abs(m.value - exp_val) < 1e-4, f"Sample {m.component_id} value mismatch: {m.value} vs {exp_val}"

        # Check conformance calculations
        conforming = [m for m in measurements if m.status == "conforming"]
        nonconforming = [m for m in measurements if m.status == "nonconforming"]
        assert len(conforming) == 2, "Expected 2 conforming parts (P001, P002)"
        assert len(nonconforming) == 3, "Expected 3 nonconforming parts (P003, P004, P005)"

        # Verify deviation beyond USL (50.05 mm)
        p003 = next(m for m in measurements if m.component_id == "P003")
        p004 = next(m for m in measurements if m.component_id == "P004")
        p005 = next(m for m in measurements if m.component_id == "P005")

        assert abs(p003.deviation_from_limit - 0.01) < 1e-4
        assert abs(p004.deviation_from_limit - 0.03) < 1e-4
        assert abs(p005.deviation_from_limit - 0.02) < 1e-4

        # Check telemetry readings for BATCH-0245
        readings = db.query(ProcessReading).filter_by(batch_id=b245.id).all()
        assert len(readings) > 0, "Telemetry readings for BATCH-0245 must exist"

        max_vib = max(r.vibration for r in readings)
        max_tool = max(r.tool_usage_cycles for r in readings)
        assert max_vib >= 3.7, f"Expected peak vibration >= 3.7 mm/s, found {max_vib}"
        assert max_tool >= 1150, f"Expected peak tool cycles >= 1150, found {max_tool}"

        # Unchanged parameters: spindle speed and feed rate
        for r in readings:
            assert r.spindle_speed == 1200.0, "Spindle speed must remain unchanged at 1200 RPM"
            assert r.feed_rate == 0.20, "Feed rate must remain unchanged at 0.20 mm/rev"
    finally:
        db.close()

def test_extended_batches_count():
    db = SessionLocal()
    try:
        batches = db.query(Batch).all()
        assert len(batches) >= 25, f"Expected >= 25 batches, found {len(batches)}"
    finally:
        db.close()

def test_historical_ncrs_and_ncr019():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    ncr_file = os.path.join(base_dir, "historical_ncrs.json")
    assert os.path.exists(ncr_file), "historical_ncrs.json must exist"

    with open(ncr_file, "r", encoding="utf-8") as f:
        ncrs = json.load(f)
    assert len(ncrs) >= 20, f"Expected >= 20 historical NCRs, found {len(ncrs)}"

    ncr019 = next((n for n in ncrs if n["id"] == "NCR-019"), None)
    assert ncr019 is not None, "NCR-019 must exist in knowledge base"
    assert "tool wear" in ncr019["title"].lower()
    assert ncr019["machine"] == "CNC-02"

def test_mvtec_manifest_and_splits_no_leakage():
    """Verify MVTec manifest and splits integrity with zero train/val/test data leakage."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    manifest_file = os.path.join(base_dir, "mvtec_manifest.csv")
    splits_file = os.path.join(base_dir, "splits.json")

    assert os.path.exists(manifest_file), "mvtec_manifest.csv must exist"
    assert os.path.exists(splits_file), "splits.json must exist"

    with open(splits_file, "r", encoding="utf-8") as f:
        splits = json.load(f)

    train_paths = {r["path"] for r in splits["train"]}
    val_paths = {r["path"] for r in splits["val"]}
    test_paths = {r["path"] for r in splits["test"]}

    assert len(train_paths & val_paths) == 0, "Train and Val splits must have zero overlap"
    assert len(train_paths & test_paths) == 0, "Train and Test splits must have zero overlap"
    assert len(val_paths & test_paths) == 0, "Val and Test splits must have zero overlap"
    assert len(train_paths) + len(val_paths) + len(test_paths) == 1502

def test_held_out_curated_samples_exist():
    """Verify held-out proxy samples exist in static/uploads/samples/ including IMG-001.png."""
    samples_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples")
    )
    img001 = os.path.join(samples_dir, "IMG-001.png")
    assert os.path.exists(img001), "Held-out test image IMG-001.png must exist"

    manifest_path = os.path.join(samples_dir, "samples_manifest.json")
    assert os.path.exists(manifest_path), "samples_manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    assert len(items) >= 15, "Expected >= 15 curated real proxy-part test samples"
    for item in items:
        assert item["source"] == "MVTec AD (proxy part)"

def test_out_of_domain_handling():
    """Verify non-proxy images return out_of_domain classification."""
    from backend.app.cv_model.defect_detector import vision_model
    # Test path that does not match any of the 4 approved categories
    dummy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "IMG-001.png"))
    res = vision_model.inspect_image(dummy_path, category="gear_assembly")
    assert res["category"] == "out_of_domain"
    assert res["defect_type"] == "out_of_domain"
    assert res["confidence"] == 0.0
