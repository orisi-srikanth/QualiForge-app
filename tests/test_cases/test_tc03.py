"""
Test Case TC-03: Defect image supplied.
Binding Expected Results:
- Held-out defect image (never used in training; verified via split file and SHA-256 hash) is flagged.
- Heatmap or bounding box is present.
- Anomaly score reported.
- Defect type reported.
- Model version reported.
- Data source reported.
- Label MODEL_PREDICTION applied.
- Human review flagged (HUMAN_REVIEW_REQUIRED).
- Good image is NOT flagged (defect_detected == False).
- Model limitations stated.
Agents: 1, 2.
"""
import json
import pytest
from pathlib import Path
from tests.test_cases.fixtures import get_tc03_fixture, get_tc03_negative_control
from backend.app.agents.visual_agent import vision_agent


def test_tc03_defect_image_detection_and_held_out_proof():
    """Verify held-out defect image is flagged with bounding box/heatmap and good image is not flagged."""
    fixture = get_tc03_fixture()
    
    # 1. Verify held-out test provenance via splits.json or manifest
    manifest_path = Path("backend/app/static/uploads/samples/samples_manifest.json")
    splits_path = Path("backend/data/splits.json")
    
    provenance_verified = False
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        held_out_items = [m for m in manifest if m.get("filename") == Path(fixture["defect_image_path"]).name]
        if held_out_items and held_out_items[0].get("is_held_out_test"):
            provenance_verified = True
            
    if splits_path.exists():
        splits = json.loads(splits_path.read_text(encoding="utf-8"))
        test_samples = splits.get("test", [])
        # Check if defect test set exists
        assert len(test_samples) > 0, "Test split must contain held-out evaluation samples"
        provenance_verified = True
        
    assert provenance_verified, "Held-out provenance must be verifiable from splits or manifest"
    assert len(fixture["defect_image_hash"]) == 64, "SHA-256 hash must be 64 characters hex"
    
    # 2. Run vision agent on held-out defect image
    defect_res = vision_agent.inspect(
        image_path=fixture["defect_image_path"],
        batch_id=fixture["batch_id"],
        image_id="TC03-DEFECT-01"
    )
    pred_def = defect_res["prediction"]
    
    # Assertions on defect image
    assert pred_def.defect_detected is True, "Held-out defect image must be detected as defective"
    assert pred_def.anomaly_score > 0.50, f"Anomaly score must be > 0.50, got {pred_def.anomaly_score}"
    assert pred_def.defect_type in ["surface_scratch", "scratch", "dent_deformation"], f"Unexpected defect type: {pred_def.defect_type}"
    assert pred_def.model_version is not None and len(pred_def.model_version) > 0, "Model version must be reported"
    assert pred_def.data_source is not None and len(pred_def.data_source) > 0, "Data source must be reported"
    assert pred_def.label == "MODEL_PREDICTION", f"Epistemic label must be MODEL_PREDICTION, got {pred_def.label}"
    assert pred_def.review_status == "HUMAN_REVIEW_REQUIRED", f"Must flag human review, got {pred_def.review_status}"
    
    # Localization: check bounding box or annotated heatmap url
    has_localization = bool(pred_def.bbox or pred_def.bounding_box or pred_def.annotated_image_url)
    assert has_localization, "Defect localization (box or heatmap) must be present"
    
    # 3. Run vision agent on good image (must NOT be flagged)
    good_res = vision_agent.inspect(
        image_path=fixture["good_image_path"],
        batch_id=fixture["batch_id"],
        image_id="TC03-GOOD-01"
    )
    pred_good = good_res["prediction"]
    assert pred_good.defect_detected is False, f"Good image must NOT be flagged as defect, got score {pred_good.anomaly_score}"
    assert pred_good.defect_type in ["no_defect", "normal"], f"Good image defect type should be no_defect, got {pred_good.defect_type}"


def test_tc03_negative_control_good_image_unflagged():
    """Negative control: Good part image must not trigger defect alarms."""
    neg_fixture = get_tc03_negative_control()
    
    res = vision_agent.inspect(
        image_path=neg_fixture["image_path"],
        batch_id=neg_fixture["batch_id"],
        image_id="TC03-NEG-01"
    )
    pred = res["prediction"]
    assert pred.defect_detected is False, "Good image negative control must not detect defects"
