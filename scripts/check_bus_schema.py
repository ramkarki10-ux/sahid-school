import sqlite3

conn = sqlite3.connect('school.db')
conn.row_factory = sqlite3.Row
print("=== Tables matching bus/student/transport ===")
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for t in tables:
    if any(k in t.lower() for k in ['bus', 'transport', 'student']):
        print(f"\nTable: {t}")
        schema = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'").fetchone()[0]
        print(schema)
        count = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"Row count: {count}")
conn.close()
