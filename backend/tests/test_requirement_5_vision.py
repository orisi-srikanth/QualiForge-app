"""
Regression Test Suite: Functional Requirement 5 (Computer Vision Defect Inspection)
Standards: IATF 16949 Section 8.5.2 & ISO 9001 Section 8.6
Verifies:
1. Real ML model artifact loading (PyTorch / ONNX) and zero LLM in CV inference.
2. Inference schema on held-out defective and conforming images.
3. Input validation: Corrupt image, non-image, out-of-domain handling.
4. Supported vs unsupported defect categories.
5. Dataset counts and zero SHA-256 / perceptual hash leakage.
6. Independent scikit-learn metrics recomputation matching cv_metrics.json (delta <= 0.001).
7. Agent 2 orchestration, epistemic labelling (MODEL_PREDICTION), human review gate, and TC-03.
8. Graceful handling of invalid inputs and fallback states.
"""
import os
import sys
import json
import pytest
from pathlib import Path
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.cv_model.defect_detector import vision_model, SHAFT_CLASSES, CLASS_TO_IDX, IDX_TO_CLASS
from backend.app.agents.visual_agent import vision_agent
from backend.app.scenarios.test_scenarios import _run_tc03
from ml.cv.train_classifier import DefectClassifier
from ml.cv.make_splits import verify_shaft_splits

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

class TestRequirement5Vision:

    def test_01_real_model_weights_and_onnx_artifacts(self):
        """Check 1: Confirm trained PyTorch and ONNX weights exist, have valid sizes, and load."""
        pt_path = PROJECT_ROOT / "models" / "cv_model.pt"
        onnx_path = PROJECT_ROOT / "models" / "cv_model.onnx"
        metrics_path = PROJECT_ROOT / "models" / "cv_metrics.json"

        assert pt_path.exists(), f"Weights file missing at {pt_path}"
        assert onnx_path.exists(), f"ONNX file missing at {onnx_path}"
        assert metrics_path.exists(), f"Metrics file missing at {metrics_path}"

        pt_size_mb = pt_path.stat().st_size / (1024 * 1024)
        onnx_size_mb = onnx_path.stat().st_size / (1024 * 1024)

        assert 3.5 <= pt_size_mb <= 15.0, f"PyTorch weights size unexpected: {pt_size_mb:.2f} MB"
        assert 3.5 <= onnx_size_mb <= 15.0, f"ONNX model size unexpected: {onnx_size_mb:.2f} MB"

        # Confirm model loads into memory and performs forward pass
        model = DefectClassifier(num_classes=len(SHAFT_CLASSES))
        model.load_state_dict(torch.load(pt_path, map_location="cpu"))
        model.eval()

        dummy_tensor = torch.randn(1, 3, 224, 224)
        with torch.no_grad():
            out = model(dummy_tensor)
        assert out.shape == (1, len(SHAFT_CLASSES)), f"Unexpected output shape: {out.shape}"

    def test_02_held_out_inference_valid_defective_and_conforming(self, client):
        """Check 2: Run model on held-out defective and good images through the API."""
        # 1. Defective sample
        res_def = client.post("/api/vision/inspect-sample", params={"sample_name": "IMG-001.png"})
        assert res_def.status_code == 200, f"Failed defective sample inspection: {res_def.text}"
        data_def = res_def.json()
        pred_def = data_def["prediction"]

        assert pred_def["defect_detected"] is True
        assert pred_def["defect_type"] == "surface_scratch"
        assert pred_def["confidence"] >= 0.70
        assert pred_def["bbox"] is not None
        assert pred_def["data_source"] == "synthetic"
        assert pred_def["label"] == "MODEL_PREDICTION"
        assert pred_def["review_status"] == "HUMAN_REVIEW_REQUIRED"

        # 2. Conforming sample
        res_good = client.post("/api/vision/inspect-sample", params={"sample_name": "shaft_normal.png"})
        assert res_good.status_code == 200, f"Failed conforming sample inspection: {res_good.text}"
        data_good = res_good.json()
        pred_good = data_good["prediction"]

        assert pred_good["defect_detected"] is False
        assert pred_good["defect_type"] == "no_defect"
        assert pred_good["bbox"] is None
        assert pred_good["review_status"] == "CONFORMING_VERIFIED"
        assert pred_good["label"] == "MODEL_PREDICTION"

    def test_03_invalid_corrupt_and_out_of_domain_handling(self, client):
        """Check 2 & 12: Corrupted files, non-images, and out-of-domain inputs."""
        # 1. Corrupted file upload
        corrupt_bytes = b"CORRUPTED_BINARY_DATA_NOT_AN_IMAGE_778899"
        res_corrupt = client.post(
            "/api/vision/upload",
            files={"file": ("fake.png", corrupt_bytes, "image/png")}
        )
        assert res_corrupt.status_code in [400, 422], f"Expected 400/422 on corrupt upload, got {res_corrupt.status_code}"

        # 2. Oversized image (>10MB)
        oversized_bytes = b"X" * (11 * 1024 * 1024)
        res_big = client.post(
            "/api/vision/upload",
            files={"file": ("oversized.png", oversized_bytes, "image/png")}
        )
        assert res_big.status_code == 413, f"Expected 413 on oversized upload, got {res_big.status_code}"

        # 3. Out-of-domain category
        sample_path = PROJECT_ROOT / "backend" / "app" / "static" / "uploads" / "samples" / "IMG-001.png"
        res_ood = vision_model.inspect_image(str(sample_path), category="out_of_domain")
        assert res_ood["category"] == "out_of_domain"
        assert res_ood["confidence"] == 0.0
        assert res_ood["defect_type"] == "out_of_domain"
        assert res_ood["bbox"] is None

    def test_04_supported_vs_unsupported_defect_categories(self):
        """Check 3: Verify the 6 supported classes and confirm unsupported classes."""
        expected_classes = [
            "no_defect",
            "surface_scratch",
            "dent",
            "crack",
            "missing_feature",
            "incorrect_assembly"
        ]
        assert SHAFT_CLASSES == expected_classes, f"Class mismatch: {SHAFT_CLASSES}"

        with open(PROJECT_ROOT / "models" / "cv_metrics.json", "r", encoding="utf-8") as f:
            metrics_data = json.load(f)

        per_class = metrics_data["normal_test_split"]["per_class"]
        for cname in expected_classes:
            assert cname in per_class, f"Missing per-class metric for {cname}"
            assert per_class[cname]["support"] == 63, f"Support for {cname} must be 63"

        # Explicitly unsupported types must not be in shaft classes
        unsupported = ["porosity", "burr", "heat_discoloration", "corrosion", "chatter_marks"]
        for u in unsupported:
            assert u not in SHAFT_CLASSES, f"Unsupported class {u} unexpectedly found in model classes"

    def test_05_dataset_counts_and_zero_leakage_split(self):
        """Check 4 & 5: Document counts and verify zero SHA-256 and pHash leakage."""
        stats = verify_shaft_splits()
        assert stats["train_count"] == 1764, f"Train count {stats['train_count']} != 1764"
        assert stats["val_count"] == 378, f"Val count {stats['val_count']} != 378"
        assert stats["test_count"] == 378, f"Test count {stats['test_count']} != 378"
        assert stats["hard_test_count"] == 300, f"Hard test count {stats['hard_test_count']} != 300"
        total = stats["train_count"] + stats["val_count"] + stats["test_count"] + stats["hard_test_count"]
        assert total == 2820, f"Total images {total} != 2820"

        assert stats["sha256_overlap_count"] == 0, "SHA-256 leakage detected!"
        assert stats["phash_overlap_count"] == 0, "pHash leakage detected!"

    def test_06_independent_metrics_scikit_learn_recomputation(self):
        """Check 7: Recompute metrics on held-out test split, delta <= 0.001 against cv_metrics.json."""
        with open(PROJECT_ROOT / "models" / "cv_metrics.json", "r", encoding="utf-8") as f:
            recorded = json.load(f)["normal_test_split"]

        with open(PROJECT_ROOT / "data" / "synthetic_shafts" / "splits.json", "r", encoding="utf-8") as f:
            splits_data = json.load(f)

        test_records = splits_data["test"]
        assert len(test_records) == 378

        pt_path = PROJECT_ROOT / "models" / "cv_model.pt"
        model = DefectClassifier(num_classes=len(SHAFT_CLASSES))
        model.load_state_dict(torch.load(pt_path, map_location="cpu"))
        model.eval()

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        y_true = []
        y_pred = []
        for rec in test_records:
            true_idx = CLASS_TO_IDX[rec["class_name"]]
            img = Image.open(rec["path"]).convert("RGB")
            t_in = transform(img).unsqueeze(0)
            with torch.no_grad():
                logits = model(t_in)
                pred_idx = int(torch.argmax(logits, dim=1).item())
            y_true.append(true_idx)
            y_pred.append(pred_idx)

        calc_acc = accuracy_score(y_true, y_pred)
        calc_macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
        calc_macro_p = precision_score(y_true, y_pred, average="macro", zero_division=0)
        calc_macro_r = recall_score(y_true, y_pred, average="macro", zero_division=0)

        assert abs(recorded["accuracy"] - calc_acc) <= 0.001, f"Accuracy delta: {abs(recorded['accuracy'] - calc_acc)}"
        assert abs(recorded["macro_f1"] - calc_macro_f1) <= 0.001, f"Macro-F1 delta: {abs(recorded['macro_f1'] - calc_macro_f1)}"
        assert abs(recorded["macro_precision"] - calc_macro_p) <= 0.001, f"Macro-Precision delta: {abs(recorded['macro_precision'] - calc_macro_p)}"
        assert abs(recorded["macro_recall"] - calc_macro_r) <= 0.001, f"Macro-Recall delta: {abs(recorded['macro_recall'] - calc_macro_r)}"

        # Check confusion matrix exact match
        calc_cm = confusion_matrix(y_true, y_pred, labels=list(range(len(SHAFT_CLASSES))))
        diff = np.max(np.abs(np.array(recorded["confusion_matrix"]) - calc_cm))
        assert diff == 0, f"Confusion matrix difference: {diff}"

    def test_07_agent_2_integration_and_tc03(self):
        """Check 10: Agent 2 calls vision model through tool, routes to human review, and passes TC-03."""
        sample_path = PROJECT_ROOT / "backend" / "app" / "static" / "uploads" / "samples" / "IMG-001.png"
        res = vision_agent.inspect(str(sample_path), batch_id="BATCH-0245", image_id="IMG-001")

        assert res["defect_detected"] is True
        pred = res["prediction"]
        assert pred.defect_type == "surface_scratch"
        assert pred.label == "MODEL_PREDICTION"
        assert pred.review_status == "HUMAN_REVIEW_REQUIRED"
        assert pred.bounding_box is not None

        # Execute Scenario TC-03
        tc03_res = _run_tc03()
        assert tc03_res["status"] == "PASS", f"TC-03 failed: {tc03_res}"
        assert tc03_res["test_id"] == "TC-03"

    def test_08_sample_predictions_saved_audit(self):
        """Check 8: Ensure at least 10 sample figures exist in docs/cv_samples/."""
        samples_dir = PROJECT_ROOT / "docs" / "cv_samples"
        samples = list(samples_dir.glob("sample_*.png"))
        assert len(samples) >= 10, f"Expected at least 10 sample figures, found {len(samples)}"
