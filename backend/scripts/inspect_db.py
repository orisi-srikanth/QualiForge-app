import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "quality_system.db"))
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in cur.fetchall()]

for table in sorted(tables):
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [f"{col[1]} ({col[2]})" for col in cur.fetchall()]
    cur.execute(f'SELECT count(*) FROM "{table}"')
    count = cur.fetchone()[0]
    print(f"\nTABLE: {table} ({count} rows)")
    print("  Columns: " + ", ".join(cols))
    if count > 0:
        cur.execute(f'SELECT * FROM "{table}" LIMIT 2;')
        rows = cur.fetchall()
        for r in rows:
            print("  Sample row:", r[:8])

conn.close()
