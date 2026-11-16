import sqlite3
import os

SAMPLE_BUS_USERS = [
    {
        "student_name": "रोहित कार्की",
        "address": "इटहरी-१९, सुनसरी",
        "guardian_name": "राम बहादुर कार्की",
        "contact_number": "९८५२०३३१३३",
        "bus_stop": "ब्रह्मपुर चोक",
        "bus_number": "बस नं. १ (को १ ख २०६६)",
        "class_name": "कक्षा १०",
        "status": "सक्रिय",
        "remarks": "बिहान र दिउँसो दुवै समय"
    },
    {
        "student_name": "अनिता चौधरी",
        "address": "इटहरी-२०, तरहरा",
        "guardian_name": "सुरेश चौधरी",
        "contact_number": "९८४२००००१०",
        "bus_stop": "तरहरा बजार",
        "bus_number": "बस नं. १ (को १ ख २०६६)",
        "class_name": "कक्षा ९",
        "status": "सक्रिय",
        "remarks": "नियमित प्रयोगकर्ता"
    },
    {
        "student_name": "सौरभ थापा",
        "address": "धरान-१५, सुनसरी",
        "guardian_name": "सूर्य बहादुर थापा",
        "contact_number": "९८४२०००००४",
        "bus_stop": "तिनकुने धरान",
        "bus_number": "बस नं. १ (को १ ख २०६६)",
        "class_name": "कक्षा १२ (विज्ञान)",
        "status": "सक्रिय",
        "remarks": ""
    },
    {
        "student_name": "सुस्मिता दाहाल",
        "address": "इटहरी-५, जनता चोक",
        "guardian_name": "हरि दाहाल",
        "contact_number": "९८४२००००११",
        "bus_stop": "जनता चोक",
        "bus_number": "बस नं. २ (को १ ख २०८०)",
        "class_name": "कक्षा ८",
        "status": "सक्रिय",
        "remarks": "बिहान ६:४५ बजे पिकअप"
    },
    {
        "student_name": "प्रदिप लिम्बु",
        "address": "इटहरी-६, मुख्य बजार",
        "guardian_name": "धन बहादुर लिम्बु",
        "contact_number": "९८४२००००१२",
        "bus_stop": "इटहरी बसपार्क गेट",
        "bus_number": "बस नं. २ (को १ ख २०८०)",
        "class_name": "कक्षा ११ (व्यवस्थापन)",
        "status": "सक्रिय",
        "remarks": ""
    },
    {
        "student_name": "पूजा खनाल",
        "address": "इटहरी-१७, पकली",
        "guardian_name": "केशव खनाल",
        "contact_number": "९८४२०००००६",
        "bus_stop": "पकली चोक",
        "bus_number": "बस नं. २ (को १ ख २०८०)",
        "class_name": "कक्षा ७",
        "status": "सक्रिय",
        "remarks": ""
    },
    {
        "student_name": "सन्तोष खतिवडा",
        "address": "इटहरी-४, गैरीगाउँ",
        "guardian_name": "गोविन्द खतिवडा",
        "contact_number": "९८४२०००००३",
        "bus_stop": "गैरीगाउँ मोड",
        "bus_number": "बस नं. १ (को १ ख २०६६)",
        "class_name": "कक्षा १०",
        "status": "सक्रिय",
        "remarks": ""
    },
    {
        "student_name": "मनिषा श्रेष्ठ",
        "address": "खनार, दुहबी रोड",
        "guardian_name": "विष्णु श्रेष्ठ",
        "contact_number": "९८४२००००१५",
        "bus_stop": "खनार बजार",
        "bus_number": "बस नं. २ (को १ ख २०८०)",
        "class_name": "कक्षा ९",
        "status": "सक्रिय",
        "remarks": "बिहान र बेलुका"
    },
    {
        "student_name": "दिपेश कुमार साह",
        "address": "इटहरी-१९, शान्ति चोक",
        "guardian_name": "रामेश्वर साह",
        "contact_number": "९८०४००००२०",
        "bus_stop": "शान्ति चोक",
        "bus_number": "बस नं. १ (को १ ख २०६६)",
        "class_name": "कक्षा ११ (विज्ञान)",
        "status": "सक्रिय",
        "remarks": ""
    },
    {
        "student_name": "अस्मिता भुजेल",
        "address": "भवानीपुर, सुनसरी",
        "guardian_name": "कुमार भुजेल",
        "contact_number": "९८१२३४००५०",
        "bus_stop": "भवानीपुर मन्दिर अगाडि",
        "bus_number": "बस नं. २ (को १ ख २०८०)",
        "class_name": "कक्षा ६",
        "status": "सक्रिय",
        "remarks": ""
    }
]

def migrate_db(db_path):
    print(f"\n--- Migrating {db_path} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create bus_users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bus_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        address TEXT NOT NULL,
        guardian_name TEXT NOT NULL,
        contact_number TEXT NOT NULL,
        bus_stop TEXT NOT NULL,
        bus_number TEXT DEFAULT 'बस नं. १ (को १ ख २०६६)',
        class_name TEXT DEFAULT '',
        status TEXT DEFAULT 'सक्रिय',
        remarks TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Check if records exist
    cur.execute("SELECT COUNT(*) FROM bus_users")
    cnt = cur.fetchone()[0]
    if cnt == 0:
        print(f"Seeding {len(SAMPLE_BUS_USERS)} sample bus users...")
        for u in SAMPLE_BUS_USERS:
            cur.execute("""
                INSERT INTO bus_users (student_name, address, guardian_name, contact_number, bus_stop, bus_number, class_name, status, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                u["student_name"],
                u["address"],
                u["guardian_name"],
                u["contact_number"],
                u["bus_stop"],
                u["bus_number"],
                u["class_name"],
                u["status"],
                u["remarks"]
            ))
        print("Bus users seeded successfully.")
    else:
        print(f"bus_users already has {cnt} rows.")

    # 3. Add 'विद्यालय bus प्रयोगकर्ता' to header_menus under 'विद्यार्थी' (parent_id = 9)
    cur.execute("SELECT id FROM header_menus WHERE url = '/bus-users'")
    existing_menu = cur.fetchone()
    if not existing_menu:
        print("Adding 'विद्यालय bus प्रयोगकर्ता' to header_menus...")
        # Find max order_index under parent_id = 9
        cur.execute("SELECT MAX(order_index) FROM header_menus WHERE parent_id = 9")
        max_order = cur.fetchone()[0] or 7
        cur.execute("""
            INSERT INTO header_menus (parent_id, title_ne, title_en, url, icon, order_index, is_active)
            VALUES (9, 'विद्यालय bus प्रयोगकर्ता', 'School Bus Users', '/bus-users', 'bus', ?, 1)
        """, (max_order + 1,))
        print(f"Menu added with order_index={max_order + 1}")
    else:
        print(f"Menu '/bus-users' already exists with ID {existing_menu[0]}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    for p in ["school.db", "api/school.db"]:
        if os.path.exists(p):
            migrate_db(p)
