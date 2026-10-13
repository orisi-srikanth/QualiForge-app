# Standard Operating Procedure: Visual Inspection and AI Decision Review
- **Document ID:** SOP-055
- **Title:** Visual Defect Review, Model Confidence Thresholds, and Disposition Protocol
- **Version:** 2.0.0
- **Effective Date:** 2026-10-11
- **Data Provenance:** synthetic_illustrative

## 1. Purpose and Scope
This procedure specifies how automated computer vision inspection predictions (PatchCore Stage A anomaly localization and MobileNetV3 Stage B unified defect classification) are evaluated, confirmed, or escalated by Quality Engineers. Applies to proxy parts (screws, nuts, transistors, wiring harnesses) and machined shaft surface inspection.

## 2. Confidence Thresholds and Operational Routing
1. **Conforming Classification (no_defect):**
   - Anomaly score strictly below category threshold (e.g. < 0.65 for metal_nut).
   - Component automatically marked conforming for visual criteria and released to downstream operations.
2. **Confident Defect Identification (>= 0.70 Confidence):**
   - Model outputs defect classification, localized bounding box ROI, and heatmap overlay.
   - Component flagged for secondary visual engineering confirmation on the inspection console.
3. **Uncertain Prediction (< 0.70 Confidence):**
   - Model flags result as `uncertain`.
   - Automatic line stop or quarantine diverter routes component to the Human-in-the-Loop Quality Station.
4. **Out-of-Domain Classification (`out_of_domain`):**
   - If optical profile matches none of the recognized categories (metal_nut, screw, transistor, cable, precision_shaft), model outputs `out_of_domain`.
   - Requires manual metrology bench verification.

## 3. Human Quality Engineer Confirmation Protocol
Quality Engineers must review the multi-panel console display (Raw Surface, Model Overlay, PatchCore Heatmap):
- **Confirm Defect:** If physical inspection verifies visible discontinuity matching model ROI, engineer clicks `Confirm Defect`, generating an electronic Nonconformance Record (NCR).
- **Reject (False Positive):** If benign surface feature (e.g. washable lint, permissible reflection gradient) triggered false alarm, engineer records rejection rationale and releases component.

## 4. Disallowed Defect Classes
Cracks are explicitly unsupported in the proxy part dataset categories. All visual quality defects must conform strictly to the seven unified classes defined in `mvtec_label_map.yaml`.
