import os
import io
import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.services.yolo_detector import YoloDefectDetector, yolo_defect_detector, EXPECTED_YOLO_CLASSES
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Product, Machine, InspectionImage, VisualFinding, HumanDecision
from backend.app.core.security import create_access_token, UserRole
from backend.app.orchestrator.engine import workflow_engine

client = TestClient(app)
qe_token = create_access_token({"sub": "quality_engineer@precisionaero.com", "role": UserRole.QUALITY_ENGINEER.value})
qe_headers = {"Authorization": f"Bearer {qe_token}"}

@pytest.fixture(scope="module")
def sample_batch():
    db: Session = SessionLocal()
    try:
        prod = db.query(Product).filter(Product.name.like("%Shaft%")).first() or db.query(Product).first()
        mach = db.query(Machine).filter(Machine.code == "CNC-01").first() or db.query(Machine).first()

        b = db.query(Batch).filter(Batch.batch_number == "BATCH-YOLO-TEST").first()
        if not b:
            from datetime import datetime, timezone
            b = Batch(
                id="batch-yolo-test-uuid",
                batch_number="BATCH-YOLO-TEST",
                product_id=prod.id,
                machine_id=mach.id,
                shift="1",
                quantity=50,
                material_lot="LOT-2026-A1",
                operator_ref="OP-44",
                start_time=datetime.now(timezone.utc),
                status="IN_PROGRESS"
            )
            db.add(b)
            db.commit()
            db.refresh(b)
        batch_num = b.batch_number
    finally:
        db.close()

    yield batch_num

    db = SessionLocal()
    try:
        b_rec = db.query(Batch).filter(Batch.batch_number == "BATCH-YOLO-TEST").first()
        if b_rec:
            imgs = db.query(InspectionImage).filter(InspectionImage.batch_id == b_rec.id).all()
            img_ids = [img.id for img in imgs]
            if img_ids:
                db.query(VisualFinding).filter(VisualFinding.image_id.in_(img_ids)).delete(synchronize_session=False)
                db.query(InspectionImage).filter(InspectionImage.batch_id == b_rec.id).delete(synchronize_session=False)
            db.query(Batch).filter(Batch.id == b_rec.id).delete(synchronize_session=False)
            db.commit()
    finally:
        db.close()

class TestAgent2YoloIntegration:

    def test_01_yolo_service_loads_best_pt_and_validates_classes(self):
        detector = YoloDefectDetector(auto_load=True)
        assert detector.is_loaded is True
        assert os.path.exists(detector.model_path), f"Weights file missing: {detector.model_path}"
        assert detector.model is not None
        assert detector.expected_classes == ["scratch", "crack", "dent"]

        model_classes = list(detector.model.names.values())
        assert set(model_classes) == set(EXPECTED_YOLO_CLASSES)

    def test_02_missing_weights_raises_operational_error_without_fallback(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            YoloDefectDetector(model_path="non_existent_weights_agent2.pt", auto_load=True)
        assert "not found" in str(exc_info.value).lower()
        assert "fallback" in str(exc_info.value).lower()

    def test_03_class_mismatch_raises_validation_error(self):
        detector = YoloDefectDetector(auto_load=False)
        detector.expected_classes = ["unauthorized_class_a", "unauthorized_class_b"]
        with pytest.raises(ValueError) as exc_info:
            detector.load_model()
        assert "class mismatch" in str(exc_info.value).lower()

    def test_04_conf_threshold_bounds_validation(self):
        detector = YoloDefectDetector(auto_load=False)
        with pytest.raises(ValueError):
            detector.validate_conf_threshold(-0.1)
        with pytest.raises(ValueError):
            detector.validate_conf_threshold(1.5)
        detector.validate_conf_threshold(0.0)
        detector.validate_conf_threshold(0.25)
        detector.validate_conf_threshold(1.0)

    def test_05_valid_defective_image_returns_detections_and_bounding_boxes(self):
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "shaft_dent.png")
        )
        assert os.path.exists(sample_path), f"Sample image missing at {sample_path}"

        res = yolo_defect_detector.detect(sample_path)
        assert res["defect_detected"] is True
        assert len(res["detections"]) > 0

        assert res["model"]["name"] == "qualiforge-agent2-yolo"
        assert res["model"]["version"] == "trained-best-pt"
        assert res["model"]["classes"] == ["scratch", "crack", "dent"]

        det = res["detections"][0]
        assert det["defect_class"] in ["scratch", "crack", "dent"]
        assert 0.0 <= det["confidence"] <= 1.0

        bbox = det["bounding_box"]
        assert "x1" in bbox and "y1" in bbox and "x2" in bbox and "y2" in bbox
        assert isinstance(bbox["x1"], (int, float))
        assert isinstance(bbox["y1"], (int, float))
        assert isinstance(bbox["x2"], (int, float))
        assert isinstance(bbox["y2"], (int, float))
        assert bbox["x1"] <= bbox["x2"], "x1 must be top-left x, x2 must be bottom-right x"
        assert bbox["y1"] <= bbox["y2"], "y1 must be top-left y, y2 must be bottom-right y"

    def test_06_conforming_image_returns_empty_detections(self):
        normal_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "shaft_normal.png")
        )
        assert os.path.exists(normal_path), f"Normal sample missing at {normal_path}"

        res = yolo_defect_detector.detect(normal_path)
        assert res["defect_detected"] is False
        assert res["detections"] == [], "Empty detections array expected for conforming part"
        assert res["primary_defect"] == "no_defect"
        assert res["max_confidence"] == 0.0

    def test_07_invalid_and_corrupt_images_rejected(self):
        corrupt_bytes = b"NOT_A_VALID_JPEG_OR_PNG_HEADER_DATA"
        res = client.post(
            "/api/vision/upload",
            files={"file": ("corrupt.png", corrupt_bytes, "image/png")}
        )
        assert res.status_code in [400, 422]

    def test_08_unknown_batch_rejected(self):
        buf = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="white")
        img.save(buf, format="PNG")
        buf.seek(0)

        res = client.post(
            "/api/vision/upload",
            files={"file": ("part.png", buf.getvalue(), "image/png")},
            data={"batch_id": "NON_EXISTENT_BATCH_9999"}
        )
        assert res.status_code == 404
        assert "not found" in res.json().get("detail", "").lower()

    def test_09_full_upload_endpoint_returns_phase4_contract(self, sample_batch):
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "shaft_scratch.png")
        )
        with open(sample_path, "rb") as f:
            file_bytes = f.read()

        res = client.post(
            "/api/vision/upload",
            files={"file": ("shaft_scratch.png", file_bytes, "image/png")},
            data={"batch_id": sample_batch}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["batch_id"] == sample_batch
        assert data["image_reference"].startswith("/uploads/inspection/")
        assert "C:\\" not in data["image_reference"], "Filesystem paths must never be exposed"
        assert data["model"]["name"] == "qualiforge-agent2-yolo"
        assert data["model"]["version"] == "trained-best-pt"
        assert data["model"]["classes"] == ["scratch", "crack", "dent"]
        assert isinstance(data["detections"], list)
        assert data["review_status"] == "pending_human_review"

        db: Session = SessionLocal()
        try:
            finding = db.query(VisualFinding).filter(VisualFinding.id == data["finding_id"]).first()
            assert finding is not None
            assert finding.human_status == "pending"
            assert finding.image is not None
            assert finding.image.batch.batch_number == sample_batch
        finally:
            db.close()

    def test_10_product_batch_mismatch_quarantines_finding(self, sample_batch):
        screw_sample = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "screw_normal.png")
        )
        if not os.path.exists(screw_sample):
            pytest.skip("screw_normal.png not present in samples")

        with open(screw_sample, "rb") as f:
            file_bytes = f.read()

        res = client.post(
            "/api/vision/upload",
            files={"file": ("screw_part.png", file_bytes, "image/png")},
            data={"batch_id": sample_batch, "component_id": "screw-sample-01"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data.get("product_mismatch") is True
        assert "PRODUCT MISMATCH DETECTED" in data.get("mismatch_warning", "")

    def test_11_human_review_status_lifecycle(self, sample_batch):
        sample_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads", "samples", "shaft_dent.png")
        )
        with open(sample_path, "rb") as f:
            file_bytes = f.read()

        res_upload = client.post(
            "/api/vision/upload",
            files={"file": ("shaft_dent.png", file_bytes, "image/png")},
            data={"batch_id": sample_batch}
        )
        assert res_upload.status_code == 200
        finding_id = res_upload.json()["finding_id"]

        res_invalid = client.post(
            f"/api/vision/predictions/{finding_id}/review",
            headers=qe_headers,
            json={"decision": "MAYBE", "comment": "Undecided"}
        )
        assert res_invalid.status_code == 422

        res_no_comment = client.post(
            f"/api/vision/predictions/{finding_id}/review",
            headers=qe_headers,
            json={"decision": "REJECT", "comment": ""}
        )
        assert res_no_comment.status_code == 422

        res_qe = client.post(
            f"/api/vision/predictions/{finding_id}/review",
            headers=qe_headers,
            json={"decision": "CONFIRM", "comment": "Lead QE verified surface dent pattern"}
        )
        assert res_qe.status_code == 200
        assert res_qe.json()["status"] == "CONFIRMED"

        res_reconfirm = client.post(
            f"/api/vision/predictions/{finding_id}/review",
            headers=qe_headers,
            json={"decision": "CONFIRM", "comment": "Duplicate confirmation"}
        )
        assert res_reconfirm.status_code == 400

        db: Session = SessionLocal()
        try:
            finding = db.query(VisualFinding).filter(VisualFinding.id == finding_id).first()
            assert finding.human_status == "confirmed"
            decision_log = db.query(HumanDecision).filter(HumanDecision.entity_id == finding_id).first()
            assert decision_log is not None
            assert decision_log.decision == "CONFIRM"
        finally:
            db.close()

    def test_12_batch_status_is_not_modified_by_yolo_alone(self, sample_batch):
        db: Session = SessionLocal()
        try:
            b = db.query(Batch).filter(Batch.batch_number == sample_batch).first()
            assert b.status in ["IN_PROGRESS", "PENDING_REVIEW"], f"Unexpected batch status: {b.status}"
            assert b.status not in ["ACCEPTED", "REJECTED", "SCRAPPED"]
        finally:
            db.close()
