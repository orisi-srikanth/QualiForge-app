# QualityMind Data Model & Database Schema

## Overview
QualityMind utilizes SQLAlchemy 2.x ORM models mapped to PostgreSQL (or SQLite for offline development) with Alembic migration versioning.

---

## Entity Relationship Overview

```
[products] 1 ──── ∞ [inspection_characteristics]
    │
    │ 1
    │
    ∞
 [batches] 1 ──── ∞ [measurements]
    │      1 ──── ∞ [inspection_images] 1 ──── ∞ [visual_findings]
    │      1 ──── ∞ [process_readings]
    │      1 ──── ∞ [spc_results]
    │      1 ──── ∞ [anomalies]
    │      1 ──── ∞ [quality_incidents] 1 ──── ∞ [rca_hypotheses]
    │                                   1 ──── ∞ [capa_actions] 1 ──── ∞ [effectiveness_checks]
    │
    └───── 1 ──── ∞ [agent_runs]
           1 ──── ∞ [human_decisions]
           1 ──── ∞ [reports]
```

---

## 24 Database Tables & Definitions

1. **`users`**: Identity, credentials, and RBAC roles (`operator`, `quality_engineer`, `admin`).
2. **`products`**: Part number, family, product name, manufacturing process, material specification.
3. **`machines`**: Machine ID (`CNC-01` to `CNC-04`), cell location, machine type.
4. **`inspection_characteristics`**: Inspection parameters, nominal, tol_plus, tol_minus, auto-computed LSL/USL.
5. **`batches`**: Batch ID, product, machine, shift, quantity, material lot, operator ID, time stamps, quality status.
6. **`measurements`**: Subgroup measurements, measured value, unit, conforming status, limit deviations.
7. **`inspection_images`**: High-resolution image files, camera ID, component reference.
8. **`visual_findings`**: Detected defect, class, confidence, bounding box coordinates, Grad-CAM heatmap path.
9. **`process_readings`**: High-frequency machine telemetry (spindle, feed, vibration, tool cycles, temperature, etc.).
10. **`process_baselines`**: Rolling baseline statistics (mean, std, p01, p99, trip thresholds) per parameter.
11. **`anomalies`**: Detected outliers, anomaly type, isolation forest score, z-score, baseline comparison.
12. **`spc_results`**: Selected control chart (I-MR, X-bar/R, p-chart), UCL, LCL, CL, Nelson rule violations, Cp/Cpk/Pp/Ppk.
13. **`quality_incidents`**: NCR records, defect category, severity, containment status, resolution timestamps.
14. **`rca_hypotheses`**: 6M fishbone hypotheses, confidence scores, supporting/contradicting evidence arrays.
15. **`historical_incidents`**: Archived past NCRs embedded into ChromaDB with confirmed root causes and resolutions.
16. **`capa_actions`**: Layered action items (containment, corrective, preventive), responsible role, due date, status.
17. **`effectiveness_checks`**: Pre- vs post-intervention rejection rates, two-proportion z-test p-value, association wording.
18. **`agent_runs`**: Trace logs of agent executions, tool arguments, duration ms, input/output summaries.
19. **`human_decisions`**: Official Quality Engineer sign-offs, quarantine dispositions, and confirmed root causes.
20. **`reviewer_comments`**: Critic agent audit observations, rule violations, and requested reassessments.
21. **`reports`**: Generated PDF audit dossiers, hash, timestamp, and local file storage paths.
22. **`kb_documents`**: Technical SOPs, machine operating manuals, and inspection procedure chunk records.
23. **`maintenance_records`**: Machine tool replacement logs, spindle servicing, and calibration records.
24. **`workflow_state`**: Checkpointed JSON state for LangGraph pipeline persistence and resumption.
