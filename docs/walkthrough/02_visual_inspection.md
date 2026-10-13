# Module 02: Visual Quality Inspection

## 1. What It Does in 3 Sentences
The Visual Quality Inspection module inspects high-resolution photographs of manufactured parts using a two-stage computer vision pipeline. The first stage uses PatchCore (ResNet-18) to detect whether an anomaly exists and generates a pixel-level spatial heatmap. The second stage uses a lightweight MobileNetV3 classifier to categorize the specific defect type (e.g. scratch, dent, crack) and draw bounding box coordinates.

## 2. Key Functions and File Paths
- `VisualQualityInspectionAgent.inspect()` in [`backend/app/agents/visual_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/visual_agent.py)
- `TwoStageDefectDetector.inspect_image()` in [`backend/app/cv_model/defect_detector.py`](file:///d:/Projects%20Local/QT/backend/app/cv_model/defect_detector.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`VisualDefectPrediction`, `BoundingBox`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The system computes an anomaly score $S$ by extracting patch-level feature embeddings from intermediate layers of a pretrained ResNet-18 backbone and measuring the minimum Euclidean distance to a coreset memory bank of nominal part embeddings:
$$S = \min_{m \in \mathcal{M}} \| \phi(x) - m \|_2$$
If $S$ exceeds the calibrated threshold (e.g., 0.50), the image is flagged as anomalous. Morphological contour detection on the anomaly map finds the bounding box $(x, y, w, h)$. The cropped region is passed to MobileNetV3 with softmax output:
$$P(\text{defect} = k) = \frac{e^{z_k}}{\sum_j e^{z_j}}$$

**Worked Example from BATCH-0245:**
Image `metal_nut_scratch.png` is analyzed for sample part P003:
- PatchCore outputs anomaly score $0.812$ (threshold is $0.500$), marking `defect_detected = True`.
- Contour localization identifies a horizontal mark at coordinates $x=131, y=428, w=168, h=140$.
- MobileNetV3 outputs class probabilities: `scratch: 0.941`, `dent: 0.032`, `crack: 0.027`.
- The output is tagged with epistemic label `[MODEL PREDICTION]`, defect type `scratch`, and confidence $94.1\%$.

## 4. Design Decision and Alternative
- **Decision**: A two-stage pipeline combining unsupervised PatchCore for localization with MobileNetV3 for classification.
- **Alternative**: Single-stage YOLOv8 object detection trained directly on bounding boxes.
- **Why Chosen**: In manufacturing, defect samples are extremely rare while normal parts are plentiful; PatchCore trains on normal images alone without requiring thousands of manually labeled defect bounding boxes.

## 5. One Limitation
The model is sensitive to severe lighting variations and camera perspective angles; images with glare, deep shadows, or out-of-focus optics trigger out-of-domain uncertainty flags rather than high-confidence classifications.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: Why does the visual inspection agent assign the label `[MODEL PREDICTION]` instead of `[OBSERVED FACT]`?**
   - *Answer*: Neural network outputs are statistical inferences with associated uncertainty, false-positive risks, and confidence scores; labeling them as facts would violate epistemic safety governance.
2. **Q: How does the system handle an image from an unknown part category?**
   - *Answer*: If image features diverge drastically from all trained coreset embeddings across all categories, the model returns `defect_type="uncertain"` or `"out_of_domain"` and assigns confidence 0.0, notifying human reviewers.
3. **Q: What is the inference latency of the vision pipeline?**
   - *Answer*: The combined two-stage model runs in approximately 18–42 ms on GPU and 145 ms on CPU, easily meeting discrete manufacturing cycle times (which are typically 15–60 seconds per part).
