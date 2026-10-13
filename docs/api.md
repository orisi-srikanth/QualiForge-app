# QualityMind REST API Specification

## 1. System Health & Open Architecture
- `GET /health`: Platform health check and governance mode. All endpoints operate without login requirements or Bearer tokens.

---

## 2. Executive Dashboard
- `GET /api/dashboard/summary`: Executive KPIs (acceptance rate, rejection rate, active incidents, open CAPAs, machine status, Pareto defect distribution, and SPC centering status).

---

## 3. Product & Specification Management
- `GET /api/products`: Retrieve all registered products and inspection parameters.
- `GET /api/products/{id}/characteristics`: Retrieve dimensional tolerances, nominal values, and auto-computed LSL/USL limits.
- `GET /api/machines`: Retrieve list of factory floor machine cells (`CNC-01` to `CNC-04`).

---

## 4. Production Batches & Operations
- `GET /api/batches`: Retrieve all production batches with associated part numbers, shifts, quantities, and quality hold statuses.
- `POST /api/batches`: Ingest new batch record with material lot and process parameters.

---

## 5. Inspection & Dimensional Compliance
- `POST /api/inspection/evaluate`: 100% deterministic evaluation of sample measurements against engineering limits. Returns conformance status, nominal deviations, and limit deviations.
- `POST /api/inspection/upload-csv`: Multi-format CSV/Excel intake with automatic unit normalization (microns/inches to mm) and schema validation.
- `GET /api/inspection/{batch_id}/spec-check`: Return total inspected, accepted count, nonconforming count, rejection %, and histogram data bins.

---

## 6. Computer Vision Defect Inspection
- `POST /api/vision/inspect-sample`: Inspect pre-loaded test images (`sample_scratch.jpg`) using PyTorch `MobileNetV3`. Returns defect type, confidence, Grad-CAM heatmap, and bounding box.
- `POST /api/vision/upload`: Multipart upload of high-resolution part images for real-time defect localization.
- `GET /api/vision/findings`: List all visual inspection records and engineer confirmation statuses.

---

## 7. Machine Telemetry & Anomaly Detection
- `GET /api/process/telemetry?batch_id={id}`: Retrieve machine sensor readings (spindle speed, feed rate, coolant temperature, vibration, tool cycles, motor current, cycle time).
- `GET /api/process/anomalies`: List flagged statistical anomalies (Isolation Forest outliers, CUSUM drift, threshold trips).

---

## 8. Statistical Process Control (SPC)
- `GET /api/spc/analyze?batch_id={id}`: Generate auto-selected control chart (I-MR or X-bar/R), center line, UCL, LCL, Nelson rule violations, and Cp/Cpk metrics with guardrail warnings.
- `GET /api/spc/capability`: Calculate process capability indices with sample size adequacy checks.

---

## 9. Quality Incidents & Root Cause Analysis (RCA)
- `GET /api/incidents`: List all active and closed Quality Non-Conformance Reports (NCR).
- `GET /api/rca/analyze`: Execute 6M Ishikawa fishbone analysis, 5-Whys causal chains, and evidence weighting across candidate root causes.
- `GET /api/rca/rag-search?q={query}`: Vector semantic search across ChromaDB technical knowledge base and historical NCR archives (e.g. retrieving `NCR-019`).

---

## 10. Corrective & Preventive Action (CAPA)
- `GET /api/capa/plan`: Generate 3-tiered CAPA recommendations (Containment, Corrective, Preventive) under `status=PROPOSED`.
- `GET /api/effectiveness/{capa_id}`: Two-proportion z-test evaluation comparing pre- and post-intervention rejection rates with association disclaimer.

---

## 11. Multi-Agent Orchestration & Human Gate
- `POST /api/orchestrator/run?batch_id={id}`: Execute full 8-agent LangGraph pipeline end-to-end.
- `POST /api/review/sign-off`: Human-in-the-Loop decision gate. Authenticated Quality Engineer assigns final batch disposition and elevates confirmed root cause to `CONFIRMED_ROOT_CAUSE`.

---

## 12. Quality Audit Dossier PDF & Testing
- `GET /api/reports/pdf?batch_id={id}`: Download comprehensive 13-section ISO 9001 / IATF 16949 compliant Audit Report PDF with embedded Matplotlib charts.
- `GET /api/scenarios/all`: Run all 8 mandated test scenarios (TC-01 through TC-08) and return structured test evidence.
- `GET /api/scenarios/{id}`: Execute individual evaluation scenario.
