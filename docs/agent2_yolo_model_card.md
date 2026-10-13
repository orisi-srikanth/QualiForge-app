# QualiForge Agent 2: YOLO Surface Defect Inspection Model Card

## 1. Overview & Purpose
This document specifies the integration, architecture, execution contract, and operational guardrails for the trained YOLO defect detection model integrated into **Agent 2 (Visual Quality Inspection Agent)** of the **QualiForge AI-Powered Manufacturing Quality Intelligence** system.

Agent 2 performs real-time visual inspection on manufactured cylindrical components (precision ground shafts and machined aerospace hardware), localizing surface non-conformances with pixel-coordinate bounding boxes and confidence scores before handing off findings to downstream root cause analysis and quality engineering review.

---

## 2. Model Specifications & Artifacts

| Parameter | Specification |
| :--- | :--- |
| **Model Name** | `qualiforge-agent2-yolo` |
| **Model Version** | `trained-best-pt` |
| **Framework** | Ultralytics YOLOv8 / YOLO Detection Engine |
| **Weights Artifact** | `backend/models/agent2/best.pt` (~5.44 MB) |
| **Trained Defect Classes (3)** | `scratch`, `crack`, `dent` |
| **Input Format** | High-resolution RGB / Grayscale Part Inspection Images (PNG, JPEG, WebP) |
| **Inference Latency** | ~25–50 ms on CPU |
| **Bounding Box Format** | Pixel coordinates relative to original image: `{"x1": float, "y1": float, "x2": float, "y2": float}` |
| **Epistemic Classification** | `[MODEL_PREDICTION]` (ISO 9001 & IATF 16949 decision-support) |

> [!IMPORTANT]
> **Strict Class Boundary Notice**: The trained model detects exclusively `scratch`, `crack`, and `dent`. It does NOT classify missing features, incorrect assembly, or dimensional deviations (which are handled deterministically by Agent 1 and Agent 3).

---

## 3. Environment & Dependencies

Add the following to `backend/requirements.txt`:
```txt
ultralytics>=8.1.0
torch>=2.2.0
torchvision>=0.17.0
opencv-python-headless>=4.9.0.80
pillow>=10.0.0
```

To install without dependency locking conflicts:
```bash
python -m pip install "ultralytics>=8.1.0"
```

---

## 4. Configuration & Deployment

### 4.1 Configuration Settings
Configurable via environment variables or `.env`:
```env
# Agent 2 YOLO Model Configuration
YOLO_MODEL_PATH="./backend/models/agent2/best.pt"
YOLO_CONF_THRESHOLD=0.25
YOLO_MODEL_NAME="qualiforge-agent2-yolo"
YOLO_MODEL_VERSION="trained-best-pt"
```

In `backend/app/core/config.py`:
```python
YOLO_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "agent2", "best.pt")
YOLO_CONF_THRESHOLD: float = 0.25
YOLO_MODEL_NAME: str = "qualiforge-agent2-yolo"
YOLO_MODEL_VERSION: str = "trained-best-pt"
```

### 4.2 Large Binary Packaging & External Cloud Storage
If deploying to serverless or container registries where committing `.pt` binaries to Git is restricted:
1. Store `best.pt` in private cloud object storage (e.g. AWS S3, Google Cloud Storage, or Azure Blob).
2. Configure a startup bootstrap script or container entrypoint to download the weights if not present:
   ```bash
   # Example deployment hook
   if [ ! -f "backend/models/agent2/best.pt" ]; then
       python scripts/download_model_weights.py --output backend/models/agent2/best.pt
   fi
   ```
3. The `YoloDefectDetector` service fails fast with `FileNotFoundError` if weights are absent, strictly forbidding silent fallbacks to unauthorized pretrained generic weights.

---

## 5. API Endpoint & Request/Response Contract

### 5.1 Inspection Upload Endpoint
- **Method:** `POST`
- **Path:** `/api/vision/upload`
- **Content-Type:** `multipart/form-data`

#### Request Parameters:
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | Binary File | **Yes** | Image file (PNG, JPG) up to 10 MB |
| `batch_id` | String | No | Target production batch (e.g. `BATCH-2026-001`). If omitted, associates with latest registered batch. |
| `component_id` | String | No | Component / serial identifier (e.g. `COMP-P001`) |
| `conf_threshold` | Float | No | Custom confidence cutoff between 0.0 and 1.0 (defaults to 0.25) |

### 5.2 Response Schema (Phase 4 Contract)
```json
{
  "batch_id": "BATCH-2026-001",
  "image_reference": "/uploads/inspection/a1b2c3d4_part.png",
  "model": {
    "name": "qualiforge-agent2-yolo",
    "version": "trained-best-pt",
    "classes": ["scratch", "crack", "dent"]
  },
  "detections": [
    {
      "defect_class": "crack",
      "confidence": 0.92,
      "bounding_box": {
        "x1": 310.0,
        "y1": 182.0,
        "x2": 420.0,
        "y2": 236.0
      }
    }
  ],
  "review_status": "pending_human_review",
  "finding_id": "VF-4A1B2C3D",
  "defect_detected": true,
  "annotated_image_url": "/uploads/annotated/yolo_annotated_a1b2c3d4_part.png",
  "product_mismatch": false,
  "mismatch_warning": null,
  "prediction": {
    "image_id": "IMG-8E7D6C5B",
    "batch_id": "BATCH-2026-001",
    "defect_detected": true,
    "defect_type": "crack",
    "confidence": 0.92,
    "review_status": "HUMAN_REVIEW_REQUIRED",
    "model_version": "trained-best-pt",
    "bbox": {
      "x1": 310.0,
      "y1": 182.0,
      "x2": 420.0,
      "y2": 236.0
    },
    "image_url": "/uploads/inspection/a1b2c3d4_part.png",
    "annotated_image_url": "/uploads/annotated/yolo_annotated_a1b2c3d4_part.png",
    "label": "MODEL_PREDICTION"
  },
  "metrics": {
    "model_name": "qualiforge-agent2-yolo",
    "version": "trained-best-pt",
    "classes": ["scratch", "crack", "dent"],
    "detections_count": 1,
    "evaluation_notice": "Trained YOLO model evaluated on synthetic benchmark data; real-world industrial validation recommended."
  }
}
```

> [!NOTE]
> For conforming parts with no detections, `detections` is an empty list `[]` and `defect_detected` is `false`.

---

## 6. How to Start the Backend
From the workspace root (`d:\Projects Local\QualiForge app`):
```powershell
python run.py
```
Or directly using Uvicorn:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

---

## 7. How to Run Automated Verification Tests
Run the dedicated Agent 2 YOLO integration test suite:
```powershell
python -m pytest backend/tests/test_agent2_yolo_integration.py -v
```

Run alongside vision regression and clean startup verification:
```powershell
python -m pytest backend/tests/test_agent2_yolo_integration.py backend/tests/test_clean_startup.py backend/tests/test_requirement_5_vision.py -v
```

---

## 8. Epistemic Governance & Human Review Gate

In strict adherence to **IATF 16949 Section 8.5.2** and **ISO 9001 Section 8.6**:
1. **Decision Support Exclusivity**: YOLO predictions NEVER automatically accept, reject, scrap, or release a production batch.
2. **Review Status**: All uploaded images enter with `review_status = "pending_human_review"`.
3. **Authorized Human Review**: Only an authenticated Quality Engineer or Admin can confirm or reject findings via `POST /api/vision/predictions/{id}/review`.
4. **Audit Trail**: Every disposition decision is immutably recorded in the `human_decisions` table with timestamp and engineering justification.

---

## 9. Operational Limitations

1. **Synthetic Evaluation Boundary**: The model was trained and evaluated on synthetic manufacturing datasets with controlled lighting, surface texture, and simulated artifact morphology. Real-world optical variations (oil film, ambient plant glare, camera lens distortion) require physical calibration.
2. **Class Scope**: Unsupported defect classes (porosity, discoloration, dimension out-of-roundness) must not be inferred by this model.
