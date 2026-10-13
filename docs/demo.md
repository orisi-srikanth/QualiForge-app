# QualityMind End-to-End Demonstration Walkthrough

This script provides a step-by-step walkthrough of the QualityMind platform using the anchor manufacturing scenario: **Precision Shaft PS-2026-101 (Batch BATCH-0245)** on machine **CNC-04**.

---

## Step 1: Open the Executive Dashboard
1. Navigate to `http://localhost:5173` (or deployed Vercel URL).
2. Note the persistent top banner: *"Decision-support only. Final product disposition is a human decision."*
3. Observe the active hold banner for **Batch BATCH-0245**.
4. Click the prominent blue **"Load Demo Scenario"** button.
5. Watch the 8-agent orchestration pipeline execute live across all stages.

---

## Step 2: Dimensional Inspection Review
1. In the sidebar, click **"Inspection Center"**.
2. Inspect the 5-point hourly sample for Batch BATCH-0245:
   - P001: `50.01 mm` (Conforming)
   - P002: `50.03 mm` (Conforming)
   - P003: `50.06 mm` (Nonconforming, +0.01 mm beyond USL)
   - P004: `50.08 mm` (Nonconforming, +0.03 mm beyond USL)
   - P005: `50.07 mm` (Nonconforming, +0.02 mm beyond USL)
3. Note the sample nonconformance rate: `60.0% (3/5)` tagged as `[OBSERVED FACT]`.

---

## Step 3: Computer Vision Defect Localization
1. Click **"Visual Inspection"** in the sidebar.
2. View the PyTorch MobileNetV3 inference on `sample_scratch.jpg`:
   - Defect Class: `surface_scratch`
   - Confidence: `94.0%`
   - Epistemic Label: `[MODEL PREDICTION]`
3. Inspect the high-contrast bounding box and Grad-CAM explainability heatmap overlay.

---

## Step 4: Machine Telemetry & Anomaly Detection
1. Click **"Process Monitoring"**.
2. Examine the 8-parameter telemetry charts:
   - **Vibration:** Spiked from `2.1 mm/s` to `3.8 mm/s` (tripped critical 3.5 mm/s threshold).
   - **Tool Usage:** `1,150 cycles` vs baseline `600 cycles` (+91% overdue replacement).
   - **Spindle Speed & Feed Rate:** Perfectly unchanged at `1,200 RPM` and `0.20 mm/rev` (Neutral/Contradicting evidence against speed error).

---

## Step 5: Statistical Process Control & Nelson Drift
1. Click **"SPC Dashboard"**.
2. Examine the auto-selected I-MR control chart:
   - Upper Control Limit (UCL): `50.082 mm`
   - Upper Spec Limit (USL): `50.050 mm`
   - Notice that UCL and USL are visually separated and explained in the legend.
3. Observe the guardrail warning: *"Sample size n=5 is below threshold (n>=30) for reliable capability"*.

---

## Step 6: Root Cause Analysis & Historical RAG
1. Click **"Root Cause (RCA)"**.
2. Review the 5 evidence-ranked hypotheses:
   1. *Progressive Tool Flank Wear (88% confidence score)*
   2. *Spindle Harmonic Vibration (62% confidence score)*
   3. *Tool Offset Register Error (45% confidence score)*
   4. *Fixture Chuck Instability (25% confidence score)*
   5. *Gauge Calibration Drift (15% confidence score)*
3. View the retrieved historical incident **`NCR-019`** with cosine similarity `0.912` and context-only notice.

---

## Step 7: CAPA Framework & Human-in-the-Loop Sign-Off
1. Click **"AI Review & HITL"**.
2. Review Agent 8 Critic validation report:
   - Calculations audited: `PASS`
   - Spec references verified: `PASS`
   - Causal claims filtered: `PASS`
3. Enter authorized Quality Engineer sign-off:
   - Select disposition: `QUARANTINE_BATCH`
   - Review confirmed root cause: `Progressive Cutting Tool Flank Wear`
   - Click **"Accept Findings & Authorize Disposition"**.
4. The epistemic label elevates to `[CONFIRMED ROOT CAUSE]`.

---

## Step 8: Download Quality Audit PDF
1. Click **"Download Audit PDF"** in the top navigation header.
2. Open the downloaded 13-section ISO 9001 / IATF 16949 compliant PDF.
3. Verify that all 13 sections appear in exact order with embedded Matplotlib histogram and SPC control chart.
