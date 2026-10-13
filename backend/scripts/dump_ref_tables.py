import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "quality_system.db"))
conn = sqlite3.connect(db_path)
cur = conn.cursor()

def dump_table(t):
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = [col[1] for col in cur.fetchall()]
    cur.execute(f'SELECT * FROM "{t}"')
    rows = cur.fetchall()
    print(f"\n=== {t} ({len(rows)} rows) ===")
    for r in rows:
        print(dict(zip(cols, r)))

dump_table("users")
dump_table("products")
dump_table("machines")
dump_table("inspection_characteristics")
dump_table("maintenance_records")
dump_table("historical_incidents")
dump_table("kb_documents")
dump_table("capa_sequences")
dump_table("reports")

conn.close()
