# Computer Vision Model Card: Synthetic Machined Shaft Defect Inspector v1.0

## 1. Model Overview
- **Model Architecture:** MobileNetV3-Small Transfer Learning Classifier + Grad-CAM Spatial Localization
- **Primary Domain:** Precision Machined Cylindrical Steel Shafts
- **Primary Training Dataset:** Synthetic Machined Shafts Dataset (procedurally generated via `data/generate_shaft_images.py`)
- **Classes (6 Total):**
  1. `no_defect` (Conforming baseline)
  2. `surface_scratch` (Axial and circumferential surface scoring)
  3. `dent` (Radial impact gouges and impressions)
  4. `crack` (High-frequency structural fissures)
  5. `missing_feature` (Omission of machined keyway or snap-ring groove)
  6. `incorrect_assembly` (Misplaced or incorrect retaining collar)
- **Explainability & Localization:** Grad-CAM activation heatmaps extracted from the final convolutional feature extractor layer (`features[-1]`), thresholded at 50% peak activation to extract bounding box coordinates $[x, y, w, h]$ and contour overlays.
- **Inference Latency:** **7.46 ms per image** on standard CPU (Benchmarked via ONNX Runtime / PyTorch, well under the 2,000 ms constraint).
- **Export Artifacts:**
  - PyTorch Weights: `backend/models/cv_model.pt` (6.2 MB)
  - ONNX Model: `backend/models/cv_model.onnx` (6.0 MB, Opset 14)
  - Metrics & Thresholds: `backend/models/cv_metrics.json`
- **Epistemic Classification:** `[MODEL_PREDICTION]`.

---

## 2. Dataset Split & Zero-Leakage Architecture

- **Total Images:** 2,820 images (512x512 RGB)
- **Standard Split (70/15/15):**
  - **Train:** 1,764 images (294 per class)
  - **Validation:** 378 images (63 per class)
  - **Normal Test:** 378 images (63 per class)
- **Hard Test Split:** 300 images (50 per class) generated with unseen lighting angles, extreme contrast, heavy Gaussian blur ($\sigma \in [2.5, 4.0]$), and multiplicative shot noise.
- **Group-Based Stratification:** Splitting performed at the geometric cluster level (`group_id = f"grp_{class_idx}_{batch_idx}"`). All augmentations and variations of a specific shaft parameter configuration remain strictly within a single partition.
- **Zero-Leakage Verification:**
  - Exact SHA-256 Hash Collisions: **0** across Train, Val, Test, Hard Test.
  - 256-Bit Perceptual Hash (DCT pHash) Collisions: **0** across Train, Val, Test, Hard Test.

---

## 3. Evaluation Metrics: Normal Test vs. Hard Test

Evaluated via `ml/cv/evaluate.py`. No hyperparameters or weights were tuned on the test splits.

### 3.1 Normal Test Split (In-Distribution, 378 images)

| Defect Class | Precision | Recall | F1-Score | Support |
|:---|:---:|:---:|:---:|:---:|
| `no_defect` | 0.9538 | 0.9841 | 0.9688 | 63 |
| `surface_scratch` | 0.9815 | 0.8413 | 0.9060 | 63 |
| `dent` | 1.0000 | 1.0000 | 1.0000 | 63 |
| `crack` | 0.8857 | 0.9841 | 0.9323 | 63 |
| `missing_feature` | 1.0000 | 1.0000 | 1.0000 | 63 |
| `incorrect_assembly` | 1.0000 | 1.0000 | 1.0000 | 63 |
| **Macro Average** | **0.9702** | **0.9683** | **0.9678** | **378** |
| **Overall Accuracy** | — | — | **0.9683 (96.8%)** | **378** |

- **Mean Localization IoU (against generator ground truth masks):** **0.2437**
- **Boxes with IoU >= 0.5:** **16.4%**
- **mAP@0.5 (Localization):** **0.1640**

#### Normal Test Confusion Matrix
| True \ Pred | `no_defect` | `surface_scratch` | `dent` | `crack` | `missing_feature` | `incorrect_assembly` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `no_defect` | 62 | 0 | 0 | 1 | 0 | 0 |
| `surface_scratch` | 3 | 53 | 0 | 7 | 0 | 0 |
| `dent` | 0 | 0 | 63 | 0 | 0 | 0 |
| `crack` | 0 | 1 | 0 | 62 | 0 | 0 |
| `missing_feature` | 0 | 0 | 0 | 0 | 63 | 0 |
| `incorrect_assembly` | 0 | 0 | 0 | 0 | 0 | 63 |

---

### 3.2 Hard Test Split (Severe Distribution Shift, 300 images)

Evaluated under unseen environmental corruptions (heavy blur, extreme contrast, multi-source glare):

| Defect Class | Precision | Recall | F1-Score | Support |
|:---|:---:|:---:|:---:|:---:|
| `no_defect` | 0.2500 | 1.0000 | 0.4000 | 50 |
| `surface_scratch` | 1.0000 | 0.0400 | 0.0769 | 50 |
| `dent` | 1.0000 | 0.1800 | 0.3051 | 50 |
| `crack` | 0.4348 | 0.4000 | 0.4167 | 50 |
| `missing_feature` | 0.9048 | 0.3800 | 0.5352 | 50 |
| `incorrect_assembly` | 1.0000 | 0.4400 | 0.6111 | 50 |
| **Macro Average** | **0.7649** | **0.4067** | **0.3908** | **300** |
| **Overall Accuracy** | — | — | **0.4067 (40.7%)** | **300** |

- **Mean Localization IoU:** **0.2068**
- **Boxes with IoU >= 0.5:** **16.67%**
- **mAP@0.5:** **0.1667**

---

### 3.3 Performance Drop (Normal Test vs. Hard Test)

| Metric | Normal Test | Hard Test | Absolute Drop ($\Delta$) | Relative Degradation |
|:---|:---:|:---:|:---:|:---:|
| **Macro-F1** | 0.9678 | 0.3908 | **+0.5770** | **-59.6%** |
| **Accuracy** | 0.9683 | 0.4067 | **+0.5616** | **-58.0%** |
| **Localization IoU** | 0.2437 | 0.2068 | **+0.0369** | **-15.1%** |
| **mAP@0.5** | 0.1640 | 0.1667 | -0.0027 | +1.6% |

> [!WARNING]
> **Domain Shift Commentary:**
> When subjected to heavy Gaussian blur and unseen illumination angles, shallow textural defects (`surface_scratch` and `dent`) are frequently absorbed into the background cylinder model, leading to false-negative predictions (`no_defect` recall is 100%, but precision falls to 25.0%). Structural defects (`incorrect_assembly`, `missing_feature`) demonstrate greater resilience (F1: 0.53–0.61). This significant drop (+0.5770 Macro-F1 drop) demonstrates why synthetic vision performance cannot be assumed to transfer to uncontrolled factory floor conditions without calibration.

---

## 4. Qualitative Samples & Grad-CAM Visualizations

Visual inspection samples with ground truth (green) and predicted Grad-CAM bounding boxes (red) are preserved in:
- Normal Test Samples: `docs/cv_samples/sample_1.png` through `docs/cv_samples/sample_6.png`
- Hard Test Samples: `docs/cv_samples/sample_7.png` through `docs/cv_samples/sample_12.png`
- Normal Test Confusion Matrix: `docs/cv_samples/confusion_matrix_normal.png`
- Hard Test Confusion Matrix: `docs/cv_samples/confusion_matrix_hard.png`

---

## 5. External Real-Image Benchmark (MVTec AD Sanity Check)

To evaluate domain transfer to real metallic components without claiming validation on shafts, the trained model was evaluated on real held-out MVTec AD images (`metal_nut` and `screw`):

- **Benchmark Scope:** 60 held-out real test images (15 good + 15 scratch for `metal_nut`, 15 good + 15 scratch for `screw`).
- **Binary Decision:** Conforming (`no_defect`) vs Defective (`surface_scratch` or other defect).
- **Results:**
  - `metal_nut` Accuracy: **43.3%** (13/30)
  - `screw` Accuracy: **56.7%** (17/30)
  - **Overall Sanity Check Accuracy:** **50.0% (30/60)**
- **Domain-Gap Caveat:**
  Hexagonal fastener edges and screw thread ridges trigger strong edge activations in the shaft model, causing false defect classifications on conforming nuts and screws. This external check confirms that the model's representations are tuned to cylindrical turned shaft geometry and cannot be naively deployed onto unrelated fastener geometries.

---

## 6. Honest Engineering Disclosure & Governance Guardrails

1. **Synthetic Training Origin:**
   The vision model is trained strictly on synthetic shaft images generated procedurally with OpenCV/NumPy/PIL.
2. **Optimistic Metrics:**
   The in-distribution performance (Macro-F1: 0.9678) is optimistic compared to real factory environments with variable lens contamination, oil mist, ambient vibration, and lighting fluctuations.
3. **Not Validated on Real Shaft Photos:**
   The model has **not** been validated on physical factory shaft photographs and is **not production-grade**.
4. **Uncalibrated Model Confidence:**
   Softmax output scores represent uncalibrated network confidence, not calibrated Bayesian posterior probabilities.
5. **Mandatory Human Review:**
   All vision inferences carry `label: "MODEL_PREDICTION"` and `data_source: "synthetic"`. Per IATF 16949 decision-support protocols, automated disposition is prohibited; every flagged defect must be routed to a quality engineer review queue.
