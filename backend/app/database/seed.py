"""
Database Seeding Script for QualityMind Platform
Creates demo users, machines, products, tolerances, baselines, and historical knowledge base.
"""
import os
import json
from datetime import datetime, timezone
from backend.app.db.session import engine, SessionLocal, Base
from backend.app.db.models import (
    User, Product, Machine, InspectionCharacteristic, ProcessBaseline,
    ProcessReading, HistoricalIncident, MaintenanceRecord,
    Batch, Measurement, QualityIncident, RCAHypothesis, CAPAAction
)
from backend.app.core.security import hash_password, UserRole

def seed_database():
    """Initializes tables and seeds initial data if not already present."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Users
        if db.query(User).count() == 0:
            users = [
                User(
                    id="usr-admin-01",
                    name="Alex Administrator",
                    email="admin@precisionaero.com",
                    password_hash=hash_password("Admin123!"),
                    role=UserRole.ADMIN.value
                ),
                User(
                    id="usr-qe-01",
                    name="Sarah Chen, Lead Quality Engineer",
                    email="engineer@precisionaero.com",
                    password_hash=hash_password("Engineer123!"),
                    role=UserRole.QUALITY_ENGINEER.value
                ),
                User(
                    id="usr-op-01",
                    name="Dave Miller, CNC Operator",
                    email="operator@precisionaero.com",
                    password_hash=hash_password("Operator123!"),
                    role=UserRole.OPERATOR.value
                ),
            ]
            db.add_all(users)

        # 2. Seed Machines
        if db.query(Machine).count() == 0:
            machines = [
                Machine(id="mach-01", code="CNC-01", type="Haas VF-2 3-Axis Mill", location="Cell A - Roughing"),
                Machine(id="mach-02", code="CNC-02", type="Mori Seiki NLX-2500 CNC Lathe", location="Cell A - Turning"),
                Machine(id="mach-03", code="CNC-03", type="Mazak Quick Turn 250MSY", location="Cell B - Finishing"),
                Machine(id="mach-04", code="CNC-04", type="Okuma LB3000-EX II CNC Lathe", location="Cell B - Turning & Grinding"),
            ]
            db.add_all(machines)

        # 3. Seed Products
        if db.query(Product).count() == 0:
            products = [
                Product(
                    id="prod-ps-101",
                    name="Precision Ground Shaft",
                    part_number="PS-2026-101",
                    process="CNC Lathe Turning & Cylindrical Grinding",
                    material="Carbon Steel AISI 1045",
                    family="Precision Shafts",
                    machine_id="mach-04"
                ),
                Product(
                    id="prod-bh-202",
                    name="Bearing Housing",
                    part_number="BH-2026-202",
                    process="CNC Milling & Boring",
                    material="Ductile Cast Iron 65-45-12",
                    family="Bearings",
                    machine_id="mach-02"
                ),
                Product(
                    id="prod-fb-303",
                    name="Flanged Bushing",
                    part_number="FB-2026-303",
                    process="CNC Turning & Facing",
                    material="Phosphor Bronze C54400",
                    family="Bushings",
                    machine_id="mach-03"
                ),
            ]
            db.add_all(products)
            db.commit()

        # 4. Seed Inspection Characteristics
        if db.query(InspectionCharacteristic).count() == 0:
            chars = [
                InspectionCharacteristic(
                    id="char-ps-01",
                    product_id="prod-ps-101",
                    name="shaft_diameter",
                    unit="mm",
                    nominal=50.00,
                    tol_plus=0.05,
                    tol_minus=0.05,
                    lsl=49.95,
                    usl=50.05,
                    inspection_frequency="100% Critical Feature",
                    sample_size=5
                ),
                InspectionCharacteristic(
                    id="char-bh-01",
                    product_id="prod-bh-202",
                    name="bore_inner_diameter",
                    unit="mm",
                    nominal=85.00,
                    tol_plus=0.03,
                    tol_minus=0.03,
                    lsl=84.97,
                    usl=85.03,
                    inspection_frequency="Subgroup n=5 per hour",
                    sample_size=5
                ),
                InspectionCharacteristic(
                    id="char-fb-01",
                    product_id="prod-fb-303",
                    name="flange_thickness",
                    unit="mm",
                    nominal=12.50,
                    tol_plus=0.08,
                    tol_minus=0.08,
                    lsl=12.42,
                    usl=12.58,
                    inspection_frequency="100%",
                    sample_size=5
                ),
            ]
            db.add_all(chars)
            db.commit()

        # 4.5 Seed Production Batches from batches.csv
        if db.query(Batch).count() < 25:
            batches_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "production", "batches.csv"))
            if os.path.exists(batches_csv):
                import pandas as pd
                df_b = pd.read_csv(batches_csv)
                batches_to_add = []
                for _, r in df_b.iterrows():
                    b_num = str(r["batch_number"]).strip()
                    existing_b = db.query(Batch).filter_by(batch_number=b_num).first()
                    if existing_b:
                        if not existing_b.scenario_label and pd.notna(r.get("scenario_label")):
                            existing_b.scenario_label = str(r.get("scenario_label"))
                            db.commit()
                        continue
                    try:
                        s_time = datetime.strptime(str(r["start_time"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    except Exception:
                        s_time = datetime.now(timezone.utc)
                    try:
                        e_time = datetime.strptime(str(r["end_time"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    except Exception:
                        e_time = datetime.now(timezone.utc)
                    
                    b_id_val = "batch-0245" if b_num == "BATCH-0245" else f"batch-{b_num.lower()}"
                    batches_to_add.append(
                        Batch(
                            id=b_id_val,
                            batch_number=b_num,
                            product_id=str(r["product_id"]),
                            machine_id=str(r["machine_id"]),
                            shift=str(r.get("shift", "Day Shift")),
                            quantity=int(r.get("quantity", 500)),
                            material_lot=str(r.get("material_lot", "LOT-RAW")),
                            operator_ref=str(r.get("operator_ref", "OP-01")),
                            start_time=s_time,
                            end_time=e_time,
                            status=str(r.get("status", "CONFORMING")),
                            scenario_label=str(r.get("scenario_label", "NORMAL_PRODUCTION")) if pd.notna(r.get("scenario_label")) else None
                        )
                    )
                if batches_to_add:
                    db.add_all(batches_to_add)
                    db.commit()

        # 4.6 Seed Measurements from measurements.csv
        if db.query(Measurement).count() == 0:
            meas_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "inspection", "measurements.csv"))
            if os.path.exists(meas_csv):
                import pandas as pd
                df_m = pd.read_csv(meas_csv)
                batch_obj_map = {b.batch_number: b.id for b in db.query(Batch).all()}
                batch_obj_map.update({b.id: b.id for b in db.query(Batch).all()})
                meas_to_add = []
                for _, r in df_m.iterrows():
                    target_b = batch_obj_map.get(str(r["batch_id"]).strip())
                    if target_b:
                        try:
                            m_time = datetime.strptime(str(r["measured_at"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        except Exception:
                            m_time = datetime.now(timezone.utc)
                        meas_to_add.append(
                            Measurement(
                                batch_id=target_b,
                                characteristic_id=str(r["characteristic_id"]),
                                component_id=str(r["component_id"]),
                                value=float(r["value"]),
                                unit=str(r.get("unit", "mm")),
                                measured_at=m_time,
                                subgroup=int(r.get("subgroup", 1)),
                                status=str(r.get("status", "conforming")),
                                deviation_from_limit=float(r.get("deviation_from_limit", 0.0))
                            )
                        )
                if meas_to_add:
                    db.bulk_save_objects(meas_to_add)
                    db.commit()
        if db.query(ProcessBaseline).count() < 32:
            baselines = []
            for m_id in ["mach-01", "mach-02", "mach-03", "mach-04"]:
                if db.query(ProcessBaseline).filter_by(machine_id=m_id).count() == 0:
                    baselines.extend([
                        ProcessBaseline(id=f"base-{m_id}-01", machine_id=m_id, parameter="spindle_speed", mean=1200.0, std=5.0, p01=1185.0, p99=1215.0, lower_threshold=1150.0, upper_threshold=1250.0, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-02", machine_id=m_id, parameter="feed_rate", mean=0.20, std=0.005, p01=0.185, p99=0.215, lower_threshold=0.17, upper_threshold=0.23, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-03", machine_id=m_id, parameter="coolant_temp", mean=24.0, std=0.8, p01=22.0, p99=26.0, lower_threshold=18.0, upper_threshold=28.0, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-04", machine_id=m_id, parameter="vibration", mean=2.1, std=0.2, p01=1.6, p99=2.6, lower_threshold=1.0, upper_threshold=3.5, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-05", machine_id=m_id, parameter="tool_usage_cycles", mean=450.0, std=120.0, p01=50.0, p99=800.0, lower_threshold=0.0, upper_threshold=1000.0, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-06", machine_id=m_id, parameter="motor_current", mean=14.5, std=0.5, p01=13.0, p99=16.0, lower_threshold=10.0, upper_threshold=18.0, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-07", machine_id=m_id, parameter="cycle_time", mean=45.0, std=1.2, p01=42.0, p99=48.0, lower_threshold=38.0, upper_threshold=52.0, computed_from="Certified Baseline 10-Day Run"),
                        ProcessBaseline(id=f"base-{m_id}-08", machine_id=m_id, parameter="pressure", mean=5.5, std=0.2, p01=5.0, p99=6.0, lower_threshold=4.5, upper_threshold=6.5, computed_from="Certified Baseline 10-Day Run"),
                    ])
            if baselines:
                db.add_all(baselines)
                db.commit()

        # Seed ProcessReadings from process_readings.csv if count < 780
        if db.query(ProcessReading).count() < 780:
            csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "process", "process_readings.csv"))
            if os.path.exists(csv_path):
                import pandas as pd
                df_proc = pd.read_csv(csv_path)
                batch_map = {b.batch_number: b.id for b in db.query(Batch).all()}
                batch_map.update({b.id: b.id for b in db.query(Batch).all()})
                readings = []
                for _, r in df_proc.iterrows():
                    b_id = batch_map.get(r["batch_id"])
                    if b_id:
                        ts_val = r["ts"]
                        if isinstance(ts_val, str):
                            ts_dt = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S")
                        else:
                            ts_dt = ts_val
                        readings.append(
                            ProcessReading(
                                machine_id=r["machine_id"],
                                batch_id=b_id,
                                ts=ts_dt,
                                spindle_speed=float(r["spindle_speed"]),
                                feed_rate=float(r["feed_rate"]),
                                coolant_temp=float(r["coolant_temp"]),
                                vibration=float(r["vibration"]),
                                tool_usage_cycles=int(r["tool_usage_cycles"]),
                                motor_current=float(r["motor_current"]),
                                cycle_time=float(r["cycle_time"]),
                                pressure=float(r.get("pressure", 5.5))
                            )
                        )
                if readings:
                    db.query(ProcessReading).delete()
                    db.bulk_save_objects(readings)
                    db.commit()


        # 6. Seed Historical Incidents for RAG
        if db.query(HistoricalIncident).count() == 0:
            incidents = [
                HistoricalIncident(
                    id="hist-01",
                    ncr_id="NCR-019",
                    title="Dimensional increase associated with confirmed tool wear",
                    defect_type="Oversized shaft diameter",
                    part_number="PS-2026-101",
                    machine="CNC-02",
                    description="Shaft outer diameter drifted positive toward and past USL (50.05 mm) during latter half of high-volume night shift batch. Machine telemetry showed tool cycle counter exceeded recommended threshold of 600 cycles, reaching 1,180 cycles before detection.",
                    confirmed_root_cause="Progressive tool flank wear (VB > 0.35 mm) on carbide finish turning insert due to tool usage exceeding the scheduled preventive replacement threshold.",
                    resolution="Replaced indexable carbide insert with coated grade Kennametal CNMG432-RP. Recalibrated tool setter offset register Z and X. Updated SOP-044 to mandate tool change alarm at 650 cycles.",
                    date="2026-03-14"
                ),
                HistoricalIncident(
                    id="hist-02",
                    ncr_id="NCR-024",
                    title="Bore dimension undersized due to thermal contraction",
                    defect_type="Undersized bore diameter",
                    part_number="BH-2026-202",
                    machine="CNC-01",
                    description="Bearing housing bore was measured immediately after heavy roughing cut while workpiece temperature was 48°C. Part contracted by 0.04 mm upon cooling to room temperature (20°C).",
                    confirmed_root_cause="Measurement error: failure to allow workpiece thermal stabilization prior to final inspection micrometer verification.",
                    resolution="Implemented mandatory 15-minute thermal soaking rack before final dimensional check.",
                    date="2026-04-02"
                ),
                HistoricalIncident(
                    id="hist-03",
                    ncr_id="NCR-031",
                    title="Chatter marks and surface roughness out of specification",
                    defect_type="Surface chatter / finish waviness",
                    part_number="PS-2026-101",
                    machine="CNC-04",
                    description="High-frequency surface marks observed on precision shaft finish. Vibration sensor recorded peak 4.2 mm/s in radial direction.",
                    confirmed_root_cause="Loose clamping collet sleeve and worn tailstock live center bearing causing harmonic vibration.",
                    resolution="Replaced tailstock live center and adjusted hydraulic chuck pressure to 28 bar.",
                    date="2026-05-19"
                ),
            ]
            db.add_all(incidents)

        # 7. Seed Maintenance Records for CNC-04
        if db.query(MaintenanceRecord).count() == 0:
            records = [
                MaintenanceRecord(
                    id="maint-01",
                    machine_id="mach-04",
                    date="2026-10-01",
                    type="preventive",
                    description="Monthly spindle lubrication, hydraulic fluid top-up, and axis backlash laser check. All parameters within specification.",
                    tool_change_flag=False
                ),
                MaintenanceRecord(
                    id="maint-02",
                    machine_id="mach-04",
                    date="2026-10-05",
                    type="tool_change",
                    description="Replaced roughing tool station T01 insert. Finish turning tool T03 inspected with 200 cycles logged.",
                    tool_change_flag=True
                )
            ]
            db.add_all(records)

        # 8. Seed Quality Incidents & RCA Hypotheses
        b245 = db.query(Batch).filter_by(batch_number="BATCH-0245").first()
        b_id = b245.id if b245 else "batch-0245"
        b_map = {b.batch_number: b.id for b in db.query(Batch).all()}

        if db.query(QualityIncident).count() < 20:
            # Clear previous partial incidents if needed
            db.query(RCAHypothesis).delete()
            db.query(QualityIncident).delete()
            db.commit()

            incident_specs = [
                # ID, Batch Number, Defect Type, Rejection Reason, Severity, Created At, Confirmed Root Cause Title
                ("inc-ncr-019", "BATCH-0245", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-ncr-011", "BATCH-0245", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 22, 14, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-ncr-012", "BATCH-0245", "Surface scratch / score", "Surface Finish Defect", "MEDIUM", datetime(2026, 8, 24, 9, 30, tzinfo=timezone.utc), "Spindle Bearing Harmonic Vibration"),
                ("inc-ncr-014", "BATCH-0245", "Machine vibration chatter", "Vibration Chatter Pattern", "HIGH", datetime(2026, 9, 1, 11, 15, tzinfo=timezone.utc), "Spindle Bearing Harmonic Vibration"),
                ("inc-005", "BATCH-0003", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 16, 16, 20, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-006", "BATCH-0006", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc), "Incorrect Tool Offset Preset"),
                ("inc-007", "BATCH-0009", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-008", "BATCH-0012", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 9, 3, 8, 45, tzinfo=timezone.utc), "Thermal Expansion of Workpiece"),
                ("inc-009", "BATCH-0003", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-010", "BATCH-0001", "Undersized bore diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 12, 15, 30, tzinfo=timezone.utc), "Thermal Expansion of Workpiece"),
                ("inc-011", "BATCH-0005", "Surface scratch / score", "Surface Finish Defect", "MEDIUM", datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc), "Coolant Chip Recirculation"),
                ("inc-012", "BATCH-0007", "Undersized bore diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 8, 24, 17, 0, tzinfo=timezone.utc), "Thermal Expansion of Workpiece"),
                ("inc-013", "BATCH-0010", "Surface scratch / score", "Surface Finish Defect", "MEDIUM", datetime(2026, 8, 30, 14, 15, tzinfo=timezone.utc), "Coolant Chip Recirculation"),
                ("inc-014", "BATCH-0002", "Flange thickness deviation", "Geometric Runout", "MEDIUM", datetime(2026, 8, 14, 11, 0, tzinfo=timezone.utc), "Loose Collet Fixturing"),
                ("inc-015", "BATCH-0005", "Surface scratch / score", "Surface Finish Defect", "MEDIUM", datetime(2026, 8, 20, 13, 45, tzinfo=timezone.utc), "Coolant Chip Recirculation"),
                ("inc-016", "BATCH-0008", "Flange thickness deviation", "Geometric Runout", "MEDIUM", datetime(2026, 8, 26, 16, 30, tzinfo=timezone.utc), "Loose Collet Fixturing"),
                ("inc-017", "BATCH-0011", "Machine vibration chatter", "Vibration Chatter Pattern", "HIGH", datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc), "Spindle Bearing Harmonic Vibration"),
                ("inc-018", "BATCH-0009", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-019", "BATCH-0245", "Oversized shaft diameter", "Dimensional Out of Tolerance", "HIGH", datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc), "Progressive Tool Flank Wear"),
                ("inc-020", "BATCH-0001", "Surface scratch / score", "Surface Finish Defect", "MEDIUM", datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc), "Coolant Chip Recirculation")
            ]

            incidents_to_add = []
            hypotheses_to_add = []

            for inc_id, b_num, def_type, rej_reason, sev, c_at, confirmed_cause in incident_specs:
                target_b_id = b_map.get(b_num, b_id)
                if not db.query(Batch).filter_by(id=target_b_id).first():
                    target_b_id = b_id
                incidents_to_add.append(
                    QualityIncident(
                        id=inc_id,
                        batch_id=target_b_id,
                        title=f"{inc_id.upper()}: {def_type}",
                        defect_type=def_type,
                        rejection_reason=rej_reason,
                        severity=sev,
                        status="closed",
                        created_at=c_at
                    )
                )
                hypotheses_to_add.append(
                    RCAHypothesis(
                        id=f"hyp-conf-{inc_id}",
                        incident_id=inc_id,
                        rank=1,
                        category="Machine" if "Machine" in confirmed_cause or "Tool" in confirmed_cause or "Spindle" in confirmed_cause else "Method",
                        title=confirmed_cause,
                        label="CONFIRMED_ROOT_CAUSE",
                        status="confirmed",
                        reviewer_id="usr-qe-01",
                        evidence_score=0.92,
                        comment="Confirmed by Lead Quality Engineer (Sarah Chen) with physical toolmakers inspection."
                    )
                )

            # Also seed unconfirmed hypotheses: 3 proposed, 2 rejected (to verify root cause filter excludes them)
            hypotheses_to_add.extend([
                RCAHypothesis(
                    id="hyp-prop-01",
                    incident_id="inc-ncr-019",
                    rank=2,
                    category="Material",
                    title="Defective Raw Bar Stock Alloy",
                    label="HYPOTHESIS",
                    status="proposed",
                    evidence_score=0.45,
                    confidence_text="Requires metallurgy lab mill cert verification"
                ),
                RCAHypothesis(
                    id="hyp-prop-02",
                    incident_id="inc-ncr-011",
                    rank=2,
                    category="Method",
                    title="Operator Feed Override Error",
                    label="HYPOTHESIS",
                    status="proposed",
                    evidence_score=0.38,
                    confidence_text="Requires CNC G-code override history log analysis"
                ),
                RCAHypothesis(
                    id="hyp-prop-03",
                    incident_id="inc-ncr-012",
                    rank=2,
                    category="Machine",
                    title="Coolant Delivery Pressure Fluctuation",
                    label="HYPOTHESIS",
                    status="proposed",
                    evidence_score=0.41,
                    confidence_text="Requires manifold pressure transducer trace verification"
                ),
                RCAHypothesis(
                    id="hyp-rej-01",
                    incident_id="inc-ncr-019",
                    rank=3,
                    category="Environment",
                    title="Electrical Supply Phase Imbalance",
                    label="HYPOTHESIS",
                    status="rejected",
                    reviewer_id="usr-qe-01",
                    evidence_score=0.12,
                    comment="Power quality monitoring confirmed steady 480V ±1.2% line voltage across shift."
                ),
                RCAHypothesis(
                    id="hyp-rej-02",
                    incident_id="inc-ncr-014",
                    rank=3,
                    category="Environment",
                    title="Ambient Factory Temperature Shift",
                    label="HYPOTHESIS",
                    status="rejected",
                    reviewer_id="usr-qe-01",
                    evidence_score=0.10,
                    comment="Climate control logs indicate shop floor temperature remained steady at 20.2°C."
                )
            ])

            db.add_all(incidents_to_add)
            db.commit()
            db.add_all(hypotheses_to_add)
            db.commit()

        if db.query(CAPAAction).count() == 0:
            capa_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "capa_records.json")
            if os.path.exists(capa_file):
                with open(capa_file, "r", encoding="utf-8") as f:
                    capa_items = json.load(f)
                
                # Fetch a valid incident ID
                inc_default = db.query(QualityIncident).first()
                inc_id = inc_default.id if inc_default else "inc-ncr-011"
                
                capas_to_add = []
                for item in capa_items:
                    capas_to_add.append(
                        CAPAAction(
                            incident_id=inc_id,
                            action_code=item["action_code"],
                            type=item["type"],
                            description=item["description"],
                            responsible_role=item.get("responsible_role", "Lead Quality Engineer"),
                            due_date=item.get("due_date", "2026-11-15"),
                            status=item.get("status", "completed"),
                            completion_date=item.get("completion_date", "2026-10-01"),
                            effectiveness_result=item.get("effectiveness_result", "Statistically confirmed defect reduction.")
                        )
                    )
                db.add_all(capas_to_add)
                db.commit()

        # 9. Seed Pre- and Post-Intervention Batches for Two-Proportion Effectiveness Verification
        b_pre = db.query(Batch).filter_by(batch_number="BATCH-PRE-01").first()
        if not b_pre:
            b_pre = Batch(
                id="batch-pre-capa-01",
                batch_number="BATCH-PRE-01",
                product_id="prod-ps-101",
                machine_id="mach-04",
                shift="Night Shift",
                quantity=1000,
                material_lot="LOT-PRE-881",
                operator_ref="OP-44",
                start_time=datetime(2026, 9, 20, 2, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc),
                status="QUALITY_HOLD",
                scenario_label="PRE_CORRECTIVE_BASELINE"
            )
            db.add(b_pre)
            db.commit()

            # Add 1000 measurements: exactly 82 nonconforming (8.2%)
            meas_pre = []
            for i in range(1000):
                is_defect = (i < 82)
                meas_pre.append(
                    Measurement(
                        batch_id=b_pre.id,
                        characteristic_id="char-ps-01",
                        component_id=f"P-PRE-{i+1:04d}",
                        value=50.07 if is_defect else 50.01,
                        unit="mm",
                        measured_at=datetime(2026, 9, 20, 3, 0, tzinfo=timezone.utc),
                        subgroup=(i // 5) + 1,
                        status="nonconforming" if is_defect else "conforming",
                        deviation_from_limit=0.02 if is_defect else 0.0
                    )
                )
            db.bulk_save_objects(meas_pre)
            db.commit()

        b_post = db.query(Batch).filter_by(batch_number="BATCH-POST-01").first()
        if not b_post:
            b_post = Batch(
                id="batch-post-capa-01",
                batch_number="BATCH-POST-01",
                product_id="prod-ps-101",
                machine_id="mach-04",
                shift="Night Shift",
                quantity=1000,
                material_lot="LOT-POST-882",
                operator_ref="OP-44",
                start_time=datetime(2026, 10, 5, 2, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc),
                status="CONFORMING",
                scenario_label="POST_CORRECTIVE_VERIFIED"
            )
            db.add(b_post)
            db.commit()

            # Add 1000 measurements: exactly 11 nonconforming (1.1%, p-bar=0.0465, z=7.540)
            meas_post = []
            for i in range(1000):
                is_defect = (i < 11)
                meas_post.append(
                    Measurement(
                        batch_id=b_post.id,
                        characteristic_id="char-ps-01",
                        component_id=f"P-POST-{i+1:04d}",
                        value=50.06 if is_defect else 50.01,
                        unit="mm",
                        measured_at=datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc),
                        subgroup=(i // 5) + 1,
                        status="nonconforming" if is_defect else "conforming",
                        deviation_from_limit=0.01 if is_defect else 0.0
                    )
                )
            db.bulk_save_objects(meas_post)
            db.commit()

        b_recur = db.query(Batch).filter_by(batch_number="BATCH-RECUR-01").first()
        if not b_recur:
            b_recur = Batch(
                id="batch-recur-capa-01",
                batch_number="BATCH-RECUR-01",
                product_id="prod-ps-101",
                machine_id="mach-04",
                shift="Night Shift",
                quantity=1000,
                material_lot="LOT-POST-883",
                operator_ref="OP-44",
                start_time=datetime(2026, 10, 10, 2, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc),
                status="QUALITY_HOLD",
                scenario_label="POST_CORRECTIVE_RECURRENCE"
            )
            db.add(b_recur)
            db.commit()

            meas_recur = []
            for i in range(100):
                is_defect = (i < 15)  # 15% defect recurrence
                meas_recur.append(
                    Measurement(
                        batch_id=b_recur.id,
                        characteristic_id="char-ps-01",
                        component_id=f"P-RECUR-{i+1:04d}",
                        value=50.08 if is_defect else 50.01,
                        unit="mm",
                        measured_at=datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc),
                        subgroup=(i // 5) + 1,
                        status="nonconforming" if is_defect else "conforming",
                        deviation_from_limit=0.03 if is_defect else 0.0
                    )
                )
            db.bulk_save_objects(meas_recur)
            db.commit()

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
    print("Database seeding completed successfully.")
