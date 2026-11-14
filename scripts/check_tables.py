import sqlite3

for db_path in ['school.db', 'api/school.db']:
    print(f"=== {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("Tables:", tables)
        for t in ['committee_members', 'management_committee', 'trustee_committee', 'teachers']:
            if t in tables:
                cnt = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                print(f"  {t}: {cnt} rows")
        conn.close()
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
