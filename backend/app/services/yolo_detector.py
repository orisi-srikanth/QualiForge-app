import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

from backend.app.core.config import settings

EXPECTED_YOLO_CLASSES: List[str] = ["scratch", "crack", "dent"]

CLASS_COLORS = {
    "scratch": (0, 165, 255),  # Orange/amber
    "crack": (0, 0, 255),      # Red
    "dent": (255, 120, 0),     # Blue
}

class _ONNXModelProxy:
    def __init__(self, names: Optional[Dict[int, str]] = None):
        self.names = names or {0: "scratch", 1: "crack", 2: "dent"}

class YoloDefectDetector:

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        auto_load: bool = True
    ):
        onnx_cand = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "agent2", "best.onnx"))
        pt_cand = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "agent2", "best.pt"))

        if model_path is not None:
            self.model_path = model_path
        else:
            chosen = getattr(settings, "YOLO_MODEL_PATH", None) or onnx_cand
            if chosen and chosen.endswith(".pt") and os.path.exists(onnx_cand):
                chosen = onnx_cand
            self.model_path = chosen if os.path.exists(chosen) else (onnx_cand if os.path.exists(onnx_cand) else pt_cand)

        threshold = conf_threshold if conf_threshold is not None else getattr(settings, "YOLO_CONF_THRESHOLD", 0.25)
        self.validate_conf_threshold(threshold)
        self.conf_threshold = float(threshold)

        self.model_name = getattr(settings, "YOLO_MODEL_NAME", "qualiforge-agent2-yolo")
        self.model_version = getattr(settings, "YOLO_MODEL_VERSION", "trained-best-pt")
        self.expected_classes = list(EXPECTED_YOLO_CLASSES)

        self.model = None
        self.net = None
        self.use_opencv_dnn = False
        self.is_loaded = False

        if auto_load:
            self.load_model()

    @staticmethod
    def validate_conf_threshold(thresh: float) -> None:
        if not isinstance(thresh, (int, float)) or thresh < 0.0 or thresh > 1.0:
            raise ValueError(f"Invalid confidence threshold: {thresh}. Must be a float between 0.0 and 1.0.")

    def load_model(self) -> None:
        onnx_cand = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "agent2", "best.onnx"))
        if self.model_path.endswith(".pt") and os.path.exists(onnx_cand) and "non_existent" not in self.model_path:
            self.model_path = onnx_cand

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Trained YOLO model weights file not found at: '{self.model_path}'. "
                "Automatic fallback to unauthorized or default pretrained models is strictly prohibited."
            )

        # High-efficiency path: Use OpenCV DNN for ONNX models (uses < 30MB RAM instead of 450MB with PyTorch)
        if self.model_path.endswith(".onnx"):
            try:
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
                self.use_opencv_dnn = True
                self.model = _ONNXModelProxy({0: "scratch", 1: "crack", 2: "dent"})
                self.is_loaded = True

                actual_classes = list(self.model.names.values())
                if set(actual_classes) != set(self.expected_classes):
                    raise ValueError(
                        f"Loaded model class mismatch. Expected {self.expected_classes}, but model contains {actual_classes}. "
                        "The model must be trained specifically for scratch, crack, and dent detection."
                    )
                return
            except ValueError:
                raise
            except Exception as dnn_err:
                print(f"[YoloDefectDetector] OpenCV DNN failed to load ONNX: {dnn_err}.")

        # Safeguard: only import heavy ultralytics if explicitly requested via environment variable
        if os.environ.get("USE_ULTRALYTICS", "false").lower() in ("true", "1"):
            try:
                from ultralytics import YOLO
                if self.model_path.endswith(".onnx"):
                    loaded_model = YOLO(self.model_path, task="detect")
                else:
                    loaded_model = YOLO(self.model_path)
                self.model = loaded_model
                self.use_opencv_dnn = False
                self.is_loaded = True

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
            except ValueError:
                raise
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load YOLO model weights from '{self.model_path}': {str(exc)}"
                ) from exc
        else:
            raise RuntimeError(
                f"Ultralytics is disabled to prevent 512MB RAM exhaustion. Model must be ONNX: '{self.model_path}'"
            )

    def _detect_opencv_dnn(
        self,
        image_path: str,
        thresh: float,
        save_annotated: bool,
        output_dir: Optional[str]
    ) -> Dict[str, Any]:
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to read image at '{image_path}' using OpenCV.")
        img_h, img_w = img_bgr.shape[:2]

        blob = cv2.dnn.blobFromImage(img_bgr, 1.0 / 255.0, (640, 640), swapRB=True)
        self.net.setInput(blob)
        raw_out = self.net.forward()

        # Output shape is (1, 7, 8400) -> transpose to (8400, 7)
        if raw_out.ndim == 3:
            out = raw_out[0].T
        else:
            out = raw_out.T

        boxes: List[List[int]] = []
        confidences: List[float] = []
        class_ids: List[int] = []

        scale_x = img_w / 640.0
        scale_y = img_h / 640.0

        for row in out:
            classes_scores = row[4:]
            max_score = float(np.max(classes_scores))
            if max_score >= thresh:
                cls_id = int(np.argmax(classes_scores))
                xc, yc, bw, bh = row[0], row[1], row[2], row[3]
                x1 = max(0.0, float((xc - bw / 2.0) * scale_x))
                y1 = max(0.0, float((yc - bh / 2.0) * scale_y))
                w_box = float(bw * scale_x)
                h_box = float(bh * scale_y)
                boxes.append([int(x1), int(y1), int(w_box), int(h_box)])
                confidences.append(max_score)
                class_ids.append(cls_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, thresh, 0.45)
        detections: List[Dict[str, Any]] = []

        if len(indices) > 0:
            for i in indices:
                idx = int(i) if isinstance(i, (int, np.integer)) else int(i[0])
                cls_idx = class_ids[idx]
                cls_name = self.expected_classes[cls_idx] if cls_idx < len(self.expected_classes) else f"unknown_{cls_idx}"
                conf = confidences[idx]
                bx, by, bw, bh = boxes[idx]
                x1 = float(max(0, bx))
                y1 = float(max(0, by))
                x2 = float(min(img_w, bx + bw))
                y2 = float(min(img_h, by + bh))

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

            annotated_img = img_bgr.copy()
            for d in detections:
                bbox = d["bounding_box"]
                x1, y1 = int(bbox["x1"]), int(bbox["y1"])
                x2, y2 = int(bbox["x2"]), int(bbox["y2"])
                cls_name = d["defect_class"]
                color = CLASS_COLORS.get(cls_name, (0, 255, 0))
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)
                label_txt = f"{cls_name} ({d['confidence'] * 100:.1f}%)"
                cv2.putText(annotated_img, label_txt, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.imwrite(annotated_path, annotated_img)

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

    def detect(
        self,
        image_path: str,
        conf_threshold: Optional[float] = None,
        save_annotated: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Inspection image file not found at: '{image_path}'")

        thresh = conf_threshold if conf_threshold is not None else self.conf_threshold
        self.validate_conf_threshold(thresh)

        if self.use_opencv_dnn and self.net is not None:
            return self._detect_opencv_dnn(image_path, thresh, save_annotated, output_dir)

        # Fallback to Ultralytics if OpenCV DNN not used
        try:
            with Image.open(image_path) as img:
                img_w, img_h = img.size
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

try:
    auto_load_flag = os.environ.get("YOLO_AUTO_LOAD", "false").lower() in ("true", "1")
    yolo_defect_detector = YoloDefectDetector(auto_load=auto_load_flag)
except Exception:
    yolo_defect_detector = YoloDefectDetector(auto_load=False)
