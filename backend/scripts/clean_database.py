import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "quality_system.db"))
print(f"Targeting Database: {db_path}")

if not os.path.exists(db_path):
    print("Database file does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA foreign_keys = OFF;")

tables_to_clear = [
    "effectiveness_checks",
    "capa_actions",
    "rca_hypotheses",
    "quality_incidents",
    "human_decisions",
    "reviewer_comments",
    "agent_runs",
    "workflow_state",
    "reports",
    "spc_results",
    "anomalies",
    "process_readings",
    "visual_findings",
    "inspection_images",
    "measurements",
    "batches",
    "maintenance_records",
]

print("\n--- CLEANING TRANSACTIONAL & DEMO TABLES ---")
for t in tables_to_clear:
    cur.execute(f'SELECT count(*) FROM "{t}"')
    before_cnt = cur.fetchone()[0]
    cur.execute(f'DELETE FROM "{t}"')
    print(f"Deleted {before_cnt} records from {t}")

cur.execute("DELETE FROM products WHERE id NOT IN ('prod-ps-101', 'prod-bh-202', 'prod-fb-303');")
print("Cleaned non-master products.")

cur.execute("UPDATE capa_sequences SET last_seq = 0 WHERE year = 2026;")
print("Reset capa_sequences counter to 0.")

conn.commit()
cur.execute("VACUUM;")
cur.execute("PRAGMA foreign_keys = ON;")
conn.commit()

print("\n--- POST-CLEANUP ROW COUNTS ---")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in cur.fetchall()]
for t in sorted(tables):
    cur.execute(f'SELECT count(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    print(f"{t:30}: {cnt} rows")

conn.close()
print("\nDatabase cleaned safely. Genuine accounts and schema preserved.")
