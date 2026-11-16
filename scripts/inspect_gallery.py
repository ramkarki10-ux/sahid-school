import sqlite3
import os

print("--- Checking SQLite Database for Gallery Tables ---")
for db_name in ['school.db', 'api/school.db']:
    if os.path.exists(db_name):
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"[{db_name}] Tables containing gall/media:", [t for t in tables if 'gall' in t or 'media' in t])
        
        # Check all menus
        cur.execute("SELECT id, parent_id, title_ne, title_en, url, order_index FROM header_menus WHERE title_ne LIKE '%ग्यालेरी%' OR url LIKE '%gall%' OR parent_id IN (SELECT id FROM header_menus WHERE title_ne LIKE '%ग्यालेरी%')")
        print(f"[{db_name}] Gallery Menus:", cur.fetchall())
        conn.close()
