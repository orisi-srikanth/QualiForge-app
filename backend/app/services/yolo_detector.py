"""
QualiForge Agent 2: YOLO Defect Detection Service
Loads trained YOLO weights (best.pt) detecting ['scratch', 'crack', 'dent'].
Provides pixel-coordinate bounding boxes, confidence scoring, model metadata, and annotation generation.
"""
import os
import cv2
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

from backend.app.core.config import settings

EXPECTED_YOLO_CLASSES: List[str] = ["scratch", "crack", "dent"]


class YoloDefectDetector:
    """
    Dedicated YOLO Defect Detection Service for Agent 2 (Visual Quality Inspection).
    Strictly detects trained surface defects: scratch, crack, dent.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        auto_load: bool = True
    ):
        self.model_path = model_path or getattr(settings, "YOLO_MODEL_PATH", None) or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "agent2", "best.pt")
        )
        threshold = conf_threshold if conf_threshold is not None else getattr(settings, "YOLO_CONF_THRESHOLD", 0.25)
        self.validate_conf_threshold(threshold)
        self.conf_threshold = float(threshold)

        self.model_name = getattr(settings, "YOLO_MODEL_NAME", "qualiforge-agent2-yolo")
        self.model_version = getattr(settings, "YOLO_MODEL_VERSION", "trained-best-pt")
        self.expected_classes = list(EXPECTED_YOLO_CLASSES)

        self.model = None
        self.is_loaded = False

        if auto_load:
            self.load_model()

    @staticmethod
    def validate_conf_threshold(thresh: float) -> None:
        """Validates that confidence threshold is within valid probability bounds [0.0, 1.0]."""
        if not isinstance(thresh, (int, float)) or thresh < 0.0 or thresh > 1.0:
            raise ValueError(f"Invalid confidence threshold: {thresh}. Must be a float between 0.0 and 1.0.")

    def load_model(self) -> None:
        """
        Loads the trained YOLO model weights once.
        Strictly validates that weights exist and match expected classes.
        Does NOT silently fall back to any other model.
        """
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Trained YOLO model weights file not found at: '{self.model_path}'. "
                "Automatic fallback to unauthorized or default pretrained models is strictly prohibited."
            )

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "Ultralytics package is required for Agent 2 YOLO defect detection. "
                "Ensure ultralytics>=8.1.0 is installed."
            ) from exc

        try:
            loaded_model = YOLO(self.model_path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load YOLO model weights from '{self.model_path}': {str(exc)}"
            ) from exc

        # Validate trained classes
        names = getattr(loaded_model, "names", None)
        if isinstance(names, dict):
            actual_classes = list(names.values())
        elif isinstance(names, list):
            actual_classes = names
        else:
            actual_classes = []

        if set(actual_classes) != set(self.expected_classes):
            raise ValueError(
                f"Loaded model class mismatch. Expected {self.expected_classes}, but model contains {actual_classes}. "
                "The model must be trained specifically for scratch, crack, and dent detection."
            )

        self.model = loaded_model
        self.is_loaded = True

    def detect(
        self,
        image_path: str,
        conf_threshold: Optional[float] = None,
        save_annotated: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes YOLO inference on a stored or staged part image.
        Returns defect classifications, confidence scores, and pixel bounding boxes.
        """
        if not self.is_loaded or self.model is None:
            self.load_model()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Inspection image file not found at: '{image_path}'")

        # Validate image decoding and retrieve dimensions
        try:
            with Image.open(image_path) as img:
                img.verify()
            with Image.open(image_path) as img:
                img_w, img_h = img.size
        except Exception as exc:
            raise ValueError(f"Invalid or corrupted image file '{image_path}': {str(exc)}") from exc

        thresh = conf_threshold if conf_threshold is not None else self.conf_threshold
        self.validate_conf_threshold(thresh)

        # Execute YOLO inference
        try:
            results = self.model.predict(source=image_path, conf=thresh, verbose=False)
            res = results[0]
        except Exception as exc:
            raise RuntimeError(f"YOLO inference failed on '{image_path}': {str(exc)}") from exc

        detections: List[Dict[str, Any]] = []
        if hasattr(res, "boxes") and res.boxes is not None and len(res.boxes) > 0:
            for box in res.boxes:
                cls_idx = int(box.cls[0])
                cls_name = self.model.names.get(cls_idx, f"unknown_{cls_idx}")
                conf = float(box.conf[0])
                xyxy = [float(coord) for coord in box.xyxy[0].tolist()]

                # Bounding box coordinates: x1, y1 top-left, x2, y2 bottom-right in pixels
                x1 = max(0.0, min(float(img_w), xyxy[0]))
                y1 = max(0.0, min(float(img_h), xyxy[1]))
                x2 = max(0.0, min(float(img_w), xyxy[2]))
                y2 = max(0.0, min(float(img_h), xyxy[3]))

                detections.append({
                    "defect_class": cls_name,
                    "confidence": round(conf, 4),
                    "bounding_box": {
                        "x1": round(x1, 2),
                        "y1": round(y1, 2),
                        "x2": round(x2, 2),
                        "y2": round(y2, 2)
                    }
                })

        annotated_filename: Optional[str] = None
        annotated_path: Optional[str] = None
        if save_annotated:
            out_dir = output_dir or os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "annotated")
            )
            os.makedirs(out_dir, exist_ok=True)
            base_name = os.path.basename(image_path)
            annotated_filename = f"yolo_annotated_{base_name}"
            annotated_path = os.path.join(out_dir, annotated_filename)

            try:
                plotted_bgr = res.plot()
                cv2.imwrite(annotated_path, plotted_bgr)
            except Exception:
                annotated_filename = None
                annotated_path = None

        return {
            "model": {
                "name": self.model_name,
                "version": self.model_version,
                "classes": self.expected_classes
            },
            "detections": detections,
            "defect_detected": len(detections) > 0,
            "primary_defect": detections[0]["defect_class"] if detections else "no_defect",
            "max_confidence": max([d["confidence"] for d in detections], default=0.0),
            "image_dimensions": {"width": img_w, "height": img_h},
            "annotated_filename": annotated_filename,
            "annotated_path": annotated_path,
            "annotated_url": f"/uploads/annotated/{annotated_filename}" if annotated_filename else None
        }


# Global singleton instance loaded once on service initialization
try:
    yolo_defect_detector = YoloDefectDetector(auto_load=True)
except Exception:
    # Allow deferred initialization if weights path is configured later or under test mock
    yolo_defect_detector = YoloDefectDetector(auto_load=False)
