# Dataset Inventory & Provenance Mapping

This document inventories all manufacturing datasets required by the QualityMind engineering specifications.
Per project engineering decision, **Synthetic Machined Shaft Images** serve as the primary computer vision dataset,
while synthetic manufacturing process/quality datasets remain active, and MVTec AD is retained as an external benchmark.

| PDF Requirement Item | File Path(s) | Row / Image Count | Data Type (Synthetic / Real) | Operational Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Normal Production** | `backend/data/production/batches.csv; inspection/measurements.csv; process/process_readings.csv` | 14 batches, 325 conforming measurements, 780 telemetry readings | **Synthetic** | Baseline conforming production runs (batches BATCH-001..025), dimensional checks within +/-0.050mm, stable telemetry. |
| **Dimensional Defects** | `backend/data/inspection/measurements.csv; production/batches.csv` | 40 nonconforming measurements across 11 hold batches | **Synthetic** | Oversized and undersized journal diameters exceeding USL (50.050mm) or LSL (49.950mm). |
| **Visual Defects (Primary Dataset)** | `data/synthetic_shafts/ (images/, masks/, labels/, annotations.json)` | 2,820 images (2,520 standard 70/15/15 + 300 hard test; 470 per class) | **Synthetic** | Primary vision dataset: 6 classes (no_defect, surface_scratch, dent, crack, missing_feature, incorrect_assembly) with YOLO/COCO annotations and PNG masks. |
| **Visual Defects (External Benchmark)** | `data/mvtec_manifest.csv` | 1502 real industrial proxy images | **Real (Benchmark)** | Read-only external benchmark across metal_nut, screw, transistor, and cable proxy categories. |
| **Machine Anomalies** | `backend/data/process/process_readings.csv` | 70 telemetry records with vibration >= 3.5 mm/s trip limit | **Synthetic** | CNC turning spindle vibration spikes reaching 3.8 mm/s during BATCH-0245 tool degradation. |
| **Process Drift** | `backend/data/inspection/measurements.csv; production/batches.csv` | 30 measurements across GRADUAL_DRIFT batches | **Synthetic** | Progressive diametrical growth (+0.005 mm per subgroup) modeling thermal expansion and gradual insert flank wear. |
| **Tool Wear** | `backend/data/process/process_readings.csv` | 780 telemetry rows with cycle count >= 600 (up to 1,180 cycles) | **Synthetic** | Indexable carbide turning insert cycle counters tracking wear past 600 cycle nominal life. |
| **Historical Incidents** | `backend/data/historical_ncrs.json; backend/data/historical_ncrs.csv` | 40 Nonconformance Reports (NCRs) | **Synthetic** | Comprehensive incident repository spanning dimensional drift, tool wear, visual scratches, cracks, dents, missing features, incorrect assembly, and decoys. |
| **CAPA Records** | `backend/data/capa_records.json` | 15 8D CAPA records | **Synthetic** | Corrective and Preventive Action plans with containment, 5-Why root cause analysis, and permanent verification. |
| **Maintenance Records** | `backend/data/maintenance_records.csv; data/maintenance_records.csv` | 10 machine maintenance logs | **Synthetic** | Preventive lubrication, spindle bearing rebuilds, turret alignments, and gauge recalibrations for CNC-01..05. |
| **KB Documents** | `backend/data/kb/ (*.md); backend/data/knowledge_docs/` | 48 technical documents (42 KB + 6 manuals/PDFs) | **Synthetic & Real Public Reference** | Engineering specifications (SPEC-PS-101), machine vibration limits (Okuma LB3000), SOPs, and public NIST SPC reference handbook. |

## Summary Verification
- **Missing Items**: **0** (All 10 required items verified with existing files and populated records).
- **Primary Vision Dataset**: Synthetic Steel Shaft Images (rendered with OpenCV/NumPy/PIL with exact masks and bounding boxes).
- **External Benchmark**: MVTec AD (1,502 real industrial proxy images retained as read-only benchmark).
- **Reproducibility**: All synthetic files generated via fixed deterministic seeds (`SEED=42`).
