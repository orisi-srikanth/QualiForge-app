"""
Database Viewer Script for QualityMind (No Container Required)
Connects directly to the active database (PostgreSQL or SQLite fallback).
Prints table inventories, record counts, and executes key demonstration queries.
"""

import sys
import os
from pathlib import Path

# Ensure root directory is in python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from backend.app.db.session import engine
from backend.app.core.config import settings

def main():
    print("=" * 80)
    print(" QUALITYMIND DATABASE INSPECTOR (NATIVE DB VIEWER)")
    print("=" * 80)

    db_url = settings.DATABASE_URL
    is_sqlite = db_url.startswith("sqlite")
    db_type = "SQLite (Local File Fallback)" if is_sqlite else "PostgreSQL (Production/Local)"
    
    # Hide sensitive credentials if PostgreSQL
    masked_url = db_url
    if "@" in masked_url:
        prefix = masked_url.split("@")[0].split(":")[0]
        host = masked_url.split("@")[-1]
        masked_url = f"{prefix}:****@{host}"

    print(f"Active Database Engine : {db_type}")
    print(f"Connection URI         : {masked_url}")
    print("-" * 80)

    tables = [
        "users", "machines", "products", "inspection_characteristics",
        "process_baselines", "batches", "measurements", "inspection_images",
        "visual_findings", "process_readings", "anomalies", "spc_results",
        "quality_incidents", "rca_hypotheses", "historical_incidents",
        "capa_actions", "maintenance_records"
    ]

    print("\n[1] TABLE INVENTORY & RECORD COUNTS:")
    print("-" * 50)
    print(f"{'Table Name':<28} | {'Record Count':<15}")
    print("-" * 50)

    with engine.connect() as conn:
        for t in tables:
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"{t:<28} | {res:<15}")
            except Exception as e:
                print(f"{t:<28} | ERROR ({e})")
        print("-" * 50)

        # Demo Query 1: Golden Anchor Batch BATCH-0245
        print("\n[2] GOLDEN ANCHOR BATCH (BATCH-0245) SUMMARY:")
        print("-" * 80)
        q_batch = text("""
            SELECT id, batch_number, product_id, machine_id, quantity, status, start_time
            FROM batches
            WHERE batch_number = 'BATCH-0245'
        """)
        batch_row = conn.execute(q_batch).fetchone()
        if batch_row:
            batch_pk = batch_row[0]
            print(f"Batch Number   : {batch_row[1]}")
            print(f"Product ID     : {batch_row[2]}")
            print(f"Machine ID     : {batch_row[3]}")
            print(f"Batch Quantity : {batch_row[4]}")
            print(f"Status         : {batch_row[5]}")

            # Demo Query 2: Anchor Measurements P001-P005
            print("\n[3] ANCHOR MEASUREMENTS (P001 - P005):")
            print("-" * 80)
            q_meas = text(f"""
                SELECT component_id, value, deviation_from_limit, status
                FROM measurements
                WHERE batch_id = '{batch_pk}'
                ORDER BY component_id ASC
            """)
            rows = conn.execute(q_meas).fetchall()
            print(f"{'Part Serial':<15} | {'Measured (mm)':<15} | {'Deviation (mm)':<15} | {'Status':<15}")
            print("-" * 65)
            for r in rows:
                print(f"{r[0]:<15} | {r[1]:<15.2f} | {r[2]:<15.2f} | {r[3]:<15}")

            # Demo Query 3: Process Telemetry Readings
            print("\n[4] CNC-04 PROCESS READINGS SUMMARY (BATCH-0245):")
            print("-" * 80)
            q_proc = text(f"""
                SELECT spindle_speed, feed_rate, coolant_temp, vibration, tool_usage_cycles
                FROM process_readings
                WHERE batch_id = '{batch_pk}'
                ORDER BY ts DESC
                LIMIT 5
            """)
            p_rows = conn.execute(q_proc).fetchall()
            if p_rows:
                print(f"{'Spindle (RPM)':<15} | {'Feed (mm/r)':<15} | {'Coolant (°C)':<15} | {'Vibration (mm/s)':<18} | {'Tool Cycles':<12}")
                print("-" * 80)
                for pr in p_rows:
                    print(f"{pr[0]:<15.1f} | {pr[1]:<15.2f} | {pr[2]:<15.1f} | {pr[3]:<18.2f} | {pr[4]:<12}")

            # Demo Query 4: Quality Incident and Root Cause
            print("\n[5] QUALITY INCIDENT & RCA HYPOTHESES:")
            print("-" * 80)
            q_inc = text(f"""
                SELECT id, title, defect_type, severity, status
                FROM quality_incidents
                WHERE batch_id = '{batch_pk}'
            """)
            inc_row = conn.execute(q_inc).fetchone()
            if inc_row:
                inc_pk = inc_row[0]
                print(f"Incident ID   : {inc_row[0]}")
                print(f"Title         : {inc_row[1]}")
                print(f"Defect Type   : {inc_row[2]}")
                print(f"Severity      : {inc_row[3]}")
                print(f"Status        : {inc_row[4]}")

                # Hypotheses
                q_hypo = text(f"""
                    SELECT rank, title, evidence_score, label
                    FROM rca_hypotheses
                    WHERE incident_id = '{inc_pk}'
                    ORDER BY rank ASC
                """)
                hypo_rows = conn.execute(q_hypo).fetchall()
                print("\n  Ranked RCA Hypotheses:")
                for hr in hypo_rows:
                    print(f"   Rank {hr[0]}: {hr[1]:<35} | Score: {hr[2]:.2f} | [{hr[3]}]")
            else:
                print("No quality incident record attached to BATCH-0245.")
        else:
            print("BATCH-0245 not found in database.")

    print("\n" + "=" * 80)
    print(" DATABASE INSPECTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
