import sqlite3

for db in ['school.db', 'api/school.db']:
    print(f"=== {db} ===")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, parent_id, title_ne, title_en, url, order_index, is_active FROM header_menus ORDER BY order_index, id").fetchall()
    for r in rows:
        print(f"{r['id']} | parent={r['parent_id']} | {r['title_ne']} / {r['title_en']} -> {r['url']}")
    conn.close()
