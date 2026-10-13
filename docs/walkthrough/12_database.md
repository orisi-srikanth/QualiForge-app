# Module 12: Database & Data Model Architecture

## 1. What It Does in 3 Sentences
The Database module manages persistent storage for the entire quality inspection lifecycle across 24 relational tables using SQLAlchemy and SQLite. It tracks manufacturing products, machine tools, production batches, individual part measurements, computer vision inspection records, sensor telemetry snapshots, and Non-Conformance Reports (NCRs). It also records CAPA action items and tamper-evident audit logs with foreign key constraints and timestamps.

## 2. Key Functions and File Paths
- SQLAlchemy declarative models in [`backend/app/database/models.py`](file:///d:/Projects%20Local/QT/backend/app/database/models.py)
- Engine, session maker, and DB init in [`backend/app/database/connection.py`](file:///d:/Projects%20Local/QT/backend/app/database/connection.py)
- Demo data seeder in [`backend/app/database/seed.py`](file:///d:/Projects%20Local/QT/backend/app/database/seed.py)
- Backward compatibility shim in [`backend/app/database/session.py`](file:///d:/Projects%20Local/QT/backend/app/database/session.py)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The relational schema models the discrete manufacturing hierarchy:
- `Product` ($1 \to N$) `ProductionBatch` ($1 \to N$) `PartMeasurement`
- `Machine` ($1 \to N$) `TelemetryRecord`
- `ProductionBatch` ($1 \to N$) `QualityIncident` ($1 \to N$) `CAPARecord` ($1 \to N$) `CAPAActionItem`

**Worked Example from BATCH-0245:**
1. **Product Record**: `Product(product_id="PROD-PS-101", name="Precision Shaft", nominal_mm=50.00, tolerance_mm=0.05, usl=50.05, lsl=49.95)`
2. **Batch Record**: `ProductionBatch(batch_id="BATCH-0245", product_id="PROD-PS-101", machine="CNC-04", material_lot="LOT-CS-9842", quantity=500, status="QUALITY_HOLD")`
3. **Measurement Rows**: Five linked rows in `part_measurements` table:
   - `PartMeasurement(batch_id="BATCH-0245", serial="P001", value=50.01, conforming=True)`
   - `PartMeasurement(batch_id="BATCH-0245", serial="P002", value=50.03, conforming=True)`
   - `PartMeasurement(batch_id="BATCH-0245", serial="P003", value=50.06, conforming=False, dev=0.01)`
   - `PartMeasurement(batch_id="BATCH-0245", serial="P004", value=50.08, conforming=False, dev=0.03)`
   - `PartMeasurement(batch_id="BATCH-0245", serial="P005", value=50.07, conforming=False, dev=0.02)`
4. **Telemetry Row**: `TelemetryRecord(machine="CNC-04", batch_id="BATCH-0245", vibration=3.84, tool_cycles=1150, spindle_speed=1200)`
5. **Incident & CAPA**: `QualityIncident(incident_id="INC-2026-088", batch_id="BATCH-0245", primary_cause="Tool Flank Wear")` and linked `CAPAActionItem` records.

## 4. Design Decision and Alternative
- **Decision**: SQLite with SQLAlchemy ORM and Alembic migrations for zero-configuration, self-contained local evaluation.
- **Alternative**: Mandatory external PostgreSQL server requiring Docker or cloud infrastructure.
- **Why Chosen**: Allows any reviewer or evaluation harness to clone the repository and run all 83 tests and demo scenarios immediately without configuring external database services or network ports.

## 5. One Limitation
SQLite locks the database file during writes (`SQLITE_BUSY`); in high-throughput plant environments with dozens of CNC machines writing telemetry concurrently at 100 Hz, the connection string in `config.py` should be switched to PostgreSQL.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: How many relational tables are defined in the database?**
   - *Answer*: Exactly 24 tables, including `products`, `machines`, `production_batches`, `part_measurements`, `telemetry_records`, `inspection_reports`, `visual_inspections`, `quality_incidents`, `fishbone_factors`, `five_whys_steps`, `capa_records`, `capa_actions`, and `audit_logs`.
2. **Q: Are database operations required for the API test suite to pass?**
   - *Answer*: Yes. The seed script populates real rows in `backend/data/qualitymind.db`, and integration tests verify queries, Pareto aggregation, and two-proportion z-tests against these actual database records.
3. **Q: How does the schema handle audit trails?**
   - *Answer*: The `audit_logs` table records every critical event with `user_id`, `action_type`, `resource_id`, `before_state`, `after_state`, and UTC timestamp, ensuring traceability required by ISO 9001.
