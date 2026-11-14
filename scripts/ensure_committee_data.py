import sqlite3
from pathlib import Path

def setup_committees():
    db_paths = [
        Path(__file__).resolve().parent.parent / "school.db",
        Path(__file__).resolve().parent.parent / "api" / "school.db"
    ]

    for db_path in db_paths:
        if not db_path.exists():
            continue
        print(f"Checking database: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check SMC member count
        cur.execute("SELECT COUNT(*) as cnt FROM school_management_committee WHERE order_index = 10 OR position LIKE '%सदस्य-सचिव%'")
        if cur.fetchone()["cnt"] == 0:
            print("Adding 10th member (सदस्य-सचिव) to SMC...")
            cur.execute("""
                INSERT INTO school_management_committee 
                (name, position, phone, photo, qualification, email, address, term, order_index, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "श्री रीता फुयल",
                "सदस्य-सचिव",
                "९८५२०३३१३३",
                "/static/images/teachers/teacher_103_rita_phuyal.jpg",
                "एम.एड. (शैक्षिक नेतृत्व तथा व्यवस्थापन)",
                "principal@shahidsmriti.edu.np",
                "इटहरी-१९, सुनसरी",
                "२०८०-२०८३",
                10,
                "सक्रिय"
            ))
            conn.commit()
            print("Successfully added 10th member to SMC.")

        # Print all SMC members
        cur.execute("SELECT id, order_index, name, position, photo FROM school_management_committee ORDER BY order_index ASC, id ASC")
        smc = cur.fetchall()
        print(f"Total SMC members in {db_path.name}: {len(smc)}")
        for m in smc:
            print(f"  [{m['order_index']}] (ID {m['id']}) {m['name']} - {m['position']} | photo: {bool(m['photo'])}")

        # Print all Trustee members
        cur.execute("SELECT id, order_index, name, position, photo FROM trustee_committee ORDER BY order_index ASC, id ASC")
        trustees = cur.fetchall()
        print(f"Total Trustees in {db_path.name}: {len(trustees)}")
        for t in trustees:
            print(f"  [{t['order_index']}] (ID {t['id']}) {t['name']} - {t['position']} | photo: {bool(t['photo'])}")

        conn.close()

if __name__ == "__main__":
    setup_committees()

