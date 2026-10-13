# QualityMind Interactive Swagger Walkthrough Guide

This walkthrough provides a curated script of the **10 best endpoints to demonstrate live** during a technical audit or engineering demo.

**Swagger UI URL:** [http://localhost:8000/docs](http://localhost:8000/docs)  
**ReDoc URL:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 1. System Health & Open API Architecture
- **Endpoint:** `GET /health` (Tag: `System`)
- **What to Click:** Click **Try it out** -> **Execute**.
- **What to Expect:** 
  - Status `200 OK`.
  - JSON body containing `status: "HEALTHY"`, `agents_active: 8`, and governance mode.
  - Zero authentication overhead: all endpoints are publicly and immediately executable without login tokens or authorization modal.

---

## 2. Production Batches Registry & Anchor Batch
- **Endpoint:** `GET /api/batches` (Tag: `Batches`)
- **What to Click:** Click **Try it out** -> **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Production batch inventory including the golden anchor batch `BATCH-0245`:
    - Part Number: `PS-2026-101` (Precision Shaft)
    - Machine: `CNC-04`
    - Material Lot: `LOT-CS-9842`
    - Shift: `Night Shift`
    - Quantity: `500`
    - Status: `QUALITY_HOLD`
    - Rejection Rate: `8.2%` (3 nonconforming parts).

---

## 3. Dimensional Compliance & Spec Boundary Verification
- **Endpoint:** `GET /api/inspection/{batch_id}/spec-check` (Tag: `Inspection`)
- **What to Click:** Click **Try it out**, enter `batch_id: BATCH-0245`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Deterministic evaluation of the 5 inspection samples against USL (`50.05 mm`) and LSL (`49.95 mm`):
    - `total_inspected`: 5
    - `accepted_count`: 2 (`P001`: 50.01 mm, `P002`: 50.03 mm)
    - `nonconforming_count`: 3 (`P003`: 50.06 mm [+0.01 mm over USL], `P004`: 50.08 mm [+0.03 mm over USL], `P005`: 50.07 mm [+0.02 mm over USL])
    - `rejection_rate_percent`: 60.0%
    - Epistemic tag: `[OBSERVED FACT]`.

---

## 4. Real Computer Vision Defect Localization (MVTec AD)
- **Endpoint:** `POST /api/vision/inspect-sample` (Tag: `Vision`)
- **What to Click:** Click **Try it out**, leave default `sample_name: metal_nut_scratch.png`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Two-stage PatchCore ResNet-18 + MobileNetV3 inference output:
    - `category`: `"metal_nut"`
    - `predicted_defect`: `"scratch"`
    - `confidence`: `0.94`
    - `bounding_box`: `{"x": 131, "y": 428, "width": 168, "height": 140}`
    - `label`: `"[MODEL PREDICTION]"`
    - `model_version`: `"mvtec-two-stage-v1.0"`
    - Academic citation & proxy part notice: MVTec AD benchmark dataset (Bergmann et al., CVPR 2019).

---

## 5. Machine Telemetry Sensor Anomalies (CNC-04)
- **Endpoint:** `GET /api/process/anomalies` (Tag: `Process Monitoring`)
- **What to Click:** Click **Try it out**, enter `batch_id: BATCH-0245`, `machine: CNC-04`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Multi-sensor anomaly detection:
    - Vibration Anomaly: `observed_value: 3.84 mm/s` vs `baseline_mean: 2.10 mm/s` (Trip limit: `3.50 mm/s`), severity: `CRITICAL`.
    - Tool Cycle Gate: `observed_value: 1150 cycles` vs `threshold_limit: 800 cycles` (+91% overdue replacement), severity: `HIGH`.
    - Spindle Speed (`1200 RPM`) and Feed Rate (`0.20 mm/rev`) remain normal, acting as neutral evidence eliminating operator setup error.

---

## 6. Statistical Process Control (SPC) & Capability Guardrails
- **Endpoint:** `GET /api/spc/capability` (Tag: `SPC & Capability`)
- **What to Click:** Click **Try it out**, enter `batch_id: BATCH-0245`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Capability calculations with mandatory statistical guardrails:
    - `sample_size`: 5
    - `adequate_sample_size`: `false`
    - `guardrail_warning`: `"Caution: Sample size n=5 is below recommended n>=30 for stable capability index estimation."`
    - `cpk`: `-0.18` (Negative Cpk indicates process mean has drifted past the specification limit).
    - `interpretation`: `"Process Incapable: Mean shifted toward Upper Specification Limit (USL). 100% sorting recommended."`

---

## 7. Vector Knowledge Retrieval (ChromaDB RAG)
- **Endpoint:** `GET /api/rca/rag-search` (Tag: `Root Cause Analysis`)
- **What to Click:** Click **Try it out**, query `q: Oversized shaft diameter tool wear`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - Top semantic matches retrieved in-process from ChromaDB:
    - Top match: `historical_ncrs.json::NCR-019` (Distance: ~0.32).
    - Match title: `"Dimensional increase associated with confirmed tool wear"`.
    - Part: `PS-2026-101`, Machine: `CNC-04`.
    - Resolution text: `"Cutting tool insert flank wear exceeded 0.3mm; replaced insert and re-zeroed offset."`

---

## 8. Multi-Agent Pipeline & Execution Trace
- **Endpoint:** `POST /api/orchestrator/run` (Tag: `Workflows (Agents)`)
- **What to Click:** Click **Try it out**, enter `batch_id: BATCH-0245`, click **Execute**.
- **What to Expect:**
  - Status `200 OK`.
  - The 8-agent workflow runs across Agent 1 (Intake) -> Agent 2 (Vision) -> Agent 3 (Compliance) -> Agent 4 (Telemetry) -> Agent 5 (SPC) -> Agent 6 (RCA) -> Agent 7 (CAPA) -> Agent 8 (Critic).
  - Flags: `has_defects: true`, `has_anomalies: true`, `has_spc_violations: true`.
  - Pipeline pauses safely with `status: "PENDING_HUMAN_APPROVAL"`.
  - Execution trace contains step timestamps and inputs/outputs for all agents.

---

## 9. Human-in-the-Loop Sign-Off & RBAC Gate
- **Endpoint:** `POST /api/review/sign-off` (Tag: `Workflows (Agents)`)
- **What to Click:** Click **Try it out**, paste the payload:
  ```json
  {
    "approved_by": "Sarah Chen, Lead Quality Engineer",
    "decision": "ACCEPT_FINDINGS",
    "engineering_comments": "Physical inspection on CNC-04 verified flank wear > 0.35mm on turning insert #4.",
    "confirmed_root_cause": "Progressive Cutting Tool Flank Wear (CONFIRMED_ROOT_CAUSE)",
    "approved_capa_ids": ["CAPA-2026-088-01", "CAPA-2026-088-02"],
    "disposition": "QUARANTINE_BATCH"
  }
  ```
  Click **Execute**.
- **What to Expect:**
  - Status `200 OK` (when authenticated as `quality_engineer` or `admin`).
  - Returns `status: "DISPOSITION_RECORDED"`, `certainty: "Confirmed Root Cause"`.
- **RBAC Demonstration:** If authorized with an operator token (`operator@precisionaero.com`), this endpoint returns `HTTP 403 Forbidden` (`"Action requires one of roles ['quality_engineer', 'admin'], but user has 'operator'"`), demonstrating strict industrial access governance.

---

## 10. ISO 9001 / IATF 16949 Audit Dossier PDF Generation
- **Endpoint:** `GET /api/reports/pdf` (Tag: `Reports`)
- **What to Click:** Click **Try it out**, enter `batch_id: BATCH-0245`, click **Execute**, then click **Download file**.
- **What to Expect:**
  - Status `200 OK`, `content-type: application/pdf`.
  - Generates a ~105 KB formal 12-section Quality Audit Dossier.
  - Includes embedded Matplotlib I-MR chart, histogram with USL/LSL limits, 6M Ishikawa fishbone breakdown, 3-tiered CAPA table, epistemic labeling legend, and engineering sign-off signatures.
