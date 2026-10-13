# QualityMind Data Dictionary & Provenance Specification

This document details the data schema, generation methodology, random seeds, sample counts, and provenance for all datasets in QualityMind.

---

## 1. Primary Vision Dataset: Synthetic Machined Shafts

- **Directory:** `data/synthetic_shafts/`
- **Generator Script:** `data/generate_shaft_images.py`
- **Primary Generator Seeds:**
  - Standard Splits (`train`, `val`, `test`): `SEED = 42`
  - Hard Test Split (`hard_test`): `HARD_TEST_SEED = 9999`
- **Total Images:** **2,820 images** (100% synthetically generated, 0 missing)
- **Image Resolution:** 512 x 512 pixels, 3-channel RGB (PNG format)
- **Annotation Formats:**
  - YOLO bounding box text files: `labels/*.txt` (`<class_id> <x_center> <y_center> <width> <height>`)
  - Ground truth pixel segmentation masks: `masks/*.png` (binary 8-bit, 255 = defect)
  - COCO JSON metadata: `data/synthetic_shafts/annotations.json`

### 1.1 Class Taxonomy & Sample Counts

| Class Index | Class Name | Defect Severity | Standard Count (70/15/15) | Hard Test Count | Total Count |
|:---:|:---|:---:|:---:|:---:|:---:|
| 0 | `no_defect` | Conforming | 420 | 50 | 470 |
| 1 | `surface_scratch` | Critical | 420 | 50 | 470 |
| 2 | `dent` | Critical | 420 | 50 | 470 |
| 3 | `crack` | Critical | 420 | 50 | 470 |
| 4 | `missing_feature` | Minor / Rework | 420 | 50 | 470 |
| 5 | `incorrect_assembly`| Major | 420 | 50 | 470 |
| **Total** | — | — | **2,520** | **300** | **2,820** |

### 1.2 Procedural Rendering Pipeline
Rendered procedurally with OpenCV, NumPy, and PIL:
- **Geometry:** Cylindrical turned steel shaft in horizontal side profile, with chamfered lead-in/lead-out ends and optional collars/shoulders.
- **Surface Texture:** Directional brushed lathe/grinding finish along the primary cylindrical axis using 1D Gaussian noise stretched horizontally.
- **Lighting & Specular Highlights:** Multi-light model featuring a continuous vertical specular reflection gradient across the cylinder curvature.
- **Machined Features:** Keyway slots and retention snap-ring grooves rendered at parametric coordinates.
- **Defect Synthesis:**
  - `surface_scratch`: Randomized curved Bezier gouges with specular highlights and dark shadow edges.
  - `dent`: Elliptical impact impressions with radial gradient shading and displaced metal highlights.
  - `crack`: High-frequency fractal branching fissures with micro-shadowing.
  - `missing_feature`: Procedural omission of keyways or snap-ring retention grooves.
  - `incorrect_assembly`: Misplaced collar or wrong-diameter collar stepped onto the shaft.
- **Backgrounds:** Variable non-uniform textures (dark granite inspection table, brushed stainless workbench, industrial rubber mat).
- **Hard Test Split Distortions:** Unseen extreme illumination angles, low-contrast shadows, severe Gaussian blur ($\sigma \in [2.5, 4.0]$), and multiplicative shot noise.

### 1.3 Split Strategy & Leakage Verification
- **Split Proportions:** 70% Train (1,764 images), 15% Validation (378 images), 15% Normal Test (378 images), + 300 Hard Test images.
- **Group Splitting:** Images partitioned by generation cluster (`group_id = f"grp_{class_idx}_{batch_idx}"`) containing 6 image variants each. All variants of a shaft geometry remain strictly within one partition.
- **Leakage Auditing:**
  - SHA-256 Exact Hash Collisions across splits: **0 collisions**
  - 256-bit DCT Perceptual Hash (pHash) Collisions across splits: **0 collisions**

---

## 2. Process Telemetry Dataset

- **File Path:** `backend/data/process/process_readings.csv`
- **Generator Script:** `data/generate_manufacturing_data.py` (Fixed Seed: `42`)
- **Total Records:** 780 rows across 26 production batches (BATCH-001 to BATCH-025, and nonconforming BATCH-0245)
- **Columns & Data Types:**
  - `timestamp` (ISO 8601 string): Machine sensor sample time.
  - `batch_id` (string): Production lot identifier.
  - `machine_id` (string): CNC turning center identifier (`CNC-01` through `CNC-05`).
  - `spindle_speed_rpm` (float): Spindle speed (nominal 1,200 RPM ± 15 RPM).
  - `feed_rate_mmrev` (float): Axis feed rate (nominal 0.20 mm/rev).
  - `motor_current_a` (float): Main spindle drive motor current (nominal 14.5 A; elevates to 16.8 A under severe tool wear).
  - `machine_vibration_mms` (float): Spindle RMS vibration in mm/s (nominal 2.1 mm/s; trips alarm threshold at ≥ 3.5 mm/s, peaking at 3.8 mm/s in BATCH-0245).
  - `coolant_temperature_c` (float): Flood coolant sump temperature (nominal 24.0°C ± 1.5°C).
  - `tool_usage_cycles` (integer): Cumulative parts cut on the active indexable insert (recommended wear limit: 600 cycles; BATCH-0245 reached 1,150–1,180 cycles).
  - `cycle_time_s` (float): Part machining cycle time (nominal 45.0 s).

---

## 3. Dimensional Metrology & Quality Inspection Dataset

- **File Path:** `backend/data/inspection/measurements.csv`
- **Generator Script:** `data/generate_manufacturing_data.py` (Fixed Seed: `42`)
- **Total Records:** 365 dimensional inspection records
- **Nominal Specifications (Shaft Outer Diameter):**
  - Nominal: $50.000\text{ mm}$
  - Upper Specification Limit (USL): $50.050\text{ mm}$ ($+0.050\text{ mm}$)
  - Lower Specification Limit (LSL): $49.950\text{ mm}$ ($-0.050\text{ mm}$)
- **Columns & Data Types:**
  - `sample_id` (string): Unique part identifier (e.g., `P001`, `P004`).
  - `batch_id` (string): Production batch identifier.
  - `timestamp` (ISO 8601 string): Measurement timestamp.
  - `nominal_mm` (float): Nominal target diameter ($50.000$).
  - `measured_diameter_mm` (float): Contact coordinate measurement / micrometer reading.
  - `usl_mm` (float): $50.050$.
  - `lsl_mm` (float): $49.950$.
  - `is_conforming` (boolean): `True` if $LSL \le \text{measured} \le USL$, else `False`.
  - `deviation_mm` (float): Arithmetic difference $(\text{measured} - \text{nominal})$.

---

## 4. Production Batch Registry

- **File Path:** `backend/data/production/batches.csv`
- **Total Records:** 14 batch master records
- **Key Fields:** `batch_id`, `machine_id`, `operator_id`, `start_time`, `end_time`, `planned_quantity`, `actual_quantity`, `defect_count`, `batch_status` (`CONFORMING`, `REJECTED`, `QUARANTINED`).

---

## 5. Historical Incidents & CAPA Records

### 5.1 Nonconformance Reports (NCRs)
- **File Paths:** `backend/data/historical_ncrs.json`, `backend/data/historical_ncrs.csv`
- **Total Records:** **40 historical NCR records** (NCR-001 through NCR-158)
- **Provenance:** Synthesized manufacturing quality incident logs conforming to IATF 16949 nonconformance reporting schemas.
- **Coverage:** Spans dimensional drift, excessive insert wear, spindle bearing play, thermal growth, and visual defects (scratches, dents, cracks, missing keyways, misplaced collars).

### 5.2 Corrective and Preventive Actions (CAPA)
- **File Path:** `backend/data/capa_records.json`
- **Total Records:** 15 comprehensive 8D CAPA documents
- **Coverage:** Detailed 8D problem solving workflows (Containment D3, Root Cause 5-Why D4, Permanent Corrective Actions D5, Verification D6, Prevent Recurrence D7).

---

## 6. Machine Maintenance History

- **File Path:** `backend/data/maintenance_records.csv`
- **Total Records:** 10 machine maintenance event logs
- **Coverage:** Scheduled preventive maintenance, spindle dynamic balancing, coolant filter flushes, tool turret alignment, and micrometer recalibration for turning machines CNC-01 through CNC-05.

---

## 7. Knowledge Base & Engineering Specifications

- **Directory:** `backend/data/kb/`
- **Total Documents:** 48 markdown engineering procedures and reference manuals
- **Key Standards Included:**
  - `SPEC-PS-101_Precision_Ground_Shaft_Specification.md`: Engineering drawing limits and tolerances.
  - `SOP-055_Visual_Inspection_Procedure.md`: Standard inspection procedure for machined shaft visual defects.
  - `SOP-012_Tool_Wear_Monitoring_and_Replacement.md`: CNC insert life protocols.
  - `MAN-CNC-04_Okuma_LB3000_Maintenance_Manual.md`: Machine vibration trip limit specifications.
  - `NIST_Engineering_Statistics_Handbook_SPC.md`: Public domain reference for Nelson rules and Shewhart control charts.

---

## 8. External Benchmark: MVTec Anomaly Detection (Optional)

- **Manifest:** `data/mvtec_manifest.csv`
- **Images:** 1,502 real industrial proxy images (`metal_nut`, `screw`, `transistor`, `cable`)
- **License:** CC BY-NC-SA 4.0 (Non-Commercial, ShareAlike)
- **Status:** Read-only external benchmark for domain-transfer experiments; not utilized as primary training data for the shaft inspection pipeline.
