import os
from typing import Dict, Any, Optional
from backend.app.cv_model.defect_detector import vision_model, UNIFIED_CLASSES

CLASSES = UNIFIED_CLASSES

class VisionInferenceEngine:
    def __init__(self, weights_path: Optional[str] = None):
        self.vision_model = vision_model

    def predict(
        self,
        image_path: str,
        image_id: str = "IMG-001",
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.vision_model.inspect_image(
            image_path=image_path,
            image_id=image_id,
            output_annotated_dir=output_dir
        )

vision_engine = VisionInferenceEngine()
vision_inference = vision_engine
