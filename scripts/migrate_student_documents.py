import sqlite3
import os

def migrate_db(db_path):
    print(f"Migrating student_documents in {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        admission_id INTEGER,
        student_class TEXT DEFAULT '',
        class_numeric INTEGER DEFAULT 0,
        student_age INTEGER DEFAULT 0,
        requirement_group TEXT DEFAULT 'nursery_to_10',
        document_type TEXT NOT NULL,
        document_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        mime_type TEXT DEFAULT 'application/pdf',
        file_data TEXT DEFAULT '',
        verification_status TEXT DEFAULT 'जाँच हुन बाँकी',
        verification_note TEXT DEFAULT '',
        verified_by INTEGER,
        verified_by_name TEXT DEFAULT '',
        verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check and add columns if table existed previously
    cur.execute("PRAGMA table_info(student_documents)")
    existing_cols = [c[1] for c in cur.fetchall()]

    col_defs = [
        ("student_class", "TEXT DEFAULT ''"),
        ("class_numeric", "INTEGER DEFAULT 0"),
        ("student_age", "INTEGER DEFAULT 0"),
        ("requirement_group", "TEXT DEFAULT 'nursery_to_10'"),
        ("file_data", "TEXT DEFAULT ''"),
        ("verified_by_name", "TEXT DEFAULT ''"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    for col_name, col_type in col_defs:
        if col_name not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE student_documents ADD COLUMN {col_name} {col_type}")
                print(f"  Added column {col_name}")
            except Exception as e:
                print(f"  Error adding {col_name}: {e}")

    # Seed sample records if empty
    cur.execute("SELECT count(*) FROM student_documents")
    count = cur.fetchone()[0]
    print(f"  Current student_documents count: {count}")

    if count == 0:
        seed_data = [
            # 1. Rohit Karki (Class 8, age 14) -> Nursery to 10 group (Birth Cert + Guardian Citizenship)
            (
                1, None, 'कक्षा ८', 8, 14, 'nursery_to_10',
                'विद्यार्थीको जन्मदर्ता (Birth Certificate)', 'रोहित कार्की - जन्मदर्ता प्रमाणपत्र',
                '/static/uploads/documents/sample_birth_cert_1.pdf', 345000, 'application/pdf',
                'प्रमाणित', 'कागजात पूर्ण रूपमा प्रमाणीकरण गरियो।', 1, 'प्रशासक (Super Admin)', '2026-11-10 10:30:00'
            ),
            (
                1, None, 'कक्षा ८', 8, 14, 'nursery_to_10',
                'अभिभावकको नागरिकता (Guardian Citizenship)', 'राम बहादुर कार्की - नागरिकता प्रमाणपत्र',
                '/static/uploads/documents/sample_citizenship_1.jpg', 210000, 'image/jpeg',
                'प्रमाणित', 'सहिद परिवार परिचयपत्र तथा नागरिकता प्रमाणित।', 1, 'प्रशासक (Super Admin)', '2026-11-10 10:32:00'
            ),

            # 2. Anita Chaudhary (Class 8, age 14) -> Nursery to 10 group
            (
                2, None, 'कक्षा ८', 8, 14, 'nursery_to_10',
                'विद्यार्थीको जन्मदर्ता (Birth Certificate)', 'अनिता चौधरी - जन्मदर्ता प्रमाणपत्र',
                '/static/uploads/documents/sample_birth_cert_2.pdf', 312000, 'application/pdf',
                'जाँच हुन बाँकी', '', None, '', None
            ),
            (
                2, None, 'कक्षा ८', 8, 14, 'nursery_to_10',
                'अभिभावकको नागरिकता (Guardian Citizenship)', 'सुरेश चौधरी - नागरिकता प्रमाणपत्र',
                '/static/uploads/documents/sample_citizenship_2.jpg', 185000, 'image/jpeg',
                'सुधार आवश्यक', 'नागरिकताको पछाडिको भाग अस्पष्ट भएकोले पुनः स्क्यान गरी अपलोड गर्नुहोस्।', 1, 'प्रशासक (Super Admin)', '2026-11-12 14:15:00'
            ),

            # 3. Puja Shrestha (Class 10, age 15) -> Nursery to 10 group
            (
                6, None, 'कक्षा १०', 10, 15, 'nursery_to_10',
                'विद्यार्थीको जन्मदर्ता (Birth Certificate)', 'पुजा श्रेष्ठ - जन्मदर्ता प्रमाणपत्र',
                '/static/uploads/documents/sample_birth_cert_3.pdf', 420000, 'application/pdf',
                'प्रमाणित', 'सदर गरिएको।', 1, 'प्रशासक (Super Admin)', '2026-11-14 09:20:00'
            ),
            (
                6, None, 'कक्षा १०', 10, 15, 'nursery_to_10',
                'अभिभावकको नागरिकता (Guardian Citizenship)', 'गोपाल श्रेष्ठ - अभिभावक नागरिकता',
                '/static/uploads/documents/sample_citizenship_3.jpg', 240000, 'image/jpeg',
                'प्रमाणित', 'सदर गरिएको।', 1, 'प्रशासक (Super Admin)', '2026-11-14 09:22:00'
            ),

            # 4. Bhawana Rai (Class 12 - Management, age 17) -> Class 11 and 12 group
            # Requires: 1. Citizenship/BirthCert, 2. Marksheet, 3. Character Certificate, 4. TC
            (
                8, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'विद्यार्थीको नागरिकता वा जन्मदर्ता (Citizenship / Birth Certificate)', 'भावना राई - नागरिकता प्रमाणपत्र',
                '/static/uploads/documents/sample_citizenship_4.jpg', 265000, 'image/jpeg',
                'प्रमाणित', 'नागरिकता नं. ०६-०१-७५-०२३४५ प्रमाणित।', 1, 'प्रशासक (Super Admin)', '2026-11-15 11:00:00'
            ),
            (
                8, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'लब्धांक पत्र / मार्कसिट (Marksheet)', 'भावना राई - SEE लब्धांक पत्र २०८०',
                '/static/uploads/documents/sample_marksheet_1.pdf', 520000, 'application/pdf',
                'प्रमाणित', 'GPA 3.65 - राष्ट्रिय परीक्षा बोर्ड प्रमाणीकरण सफल।', 1, 'प्रशासक (Super Admin)', '2026-11-15 11:05:00'
            ),
            (
                8, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'चारित्रिक प्रमाणपत्र (Character Certificate)', 'भावना राई - पूर्व विद्यालय चारित्रिक प्रमाणपत्र',
                '/static/uploads/documents/sample_char_1.pdf', 380000, 'application/pdf',
                'प्रमाणित', 'चारित्रिक प्रमाणपत्र रुजु गरियो।', 1, 'प्रशासक (Super Admin)', '2026-11-15 11:07:00'
            ),
            (
                8, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'स्थानान्तरण प्रमाणपत्र / TC (Transfer Certificate)', 'भावना राई - विद्यालय स्थानान्तरण प्रमाणपत्र (TC)',
                '/static/uploads/documents/sample_tc_1.pdf', 410000, 'application/pdf',
                'प्रमाणित', 'मूल TC सुरक्षित राखियो।', 1, 'प्रशासक (Super Admin)', '2026-11-15 11:10:00'
            ),

            # 5. Kiran Adhikari (Class 12 - Management, age 17) -> Class 11 and 12 group
            (
                9, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'विद्यार्थीको नागरिकता वा जन्मदर्ता (Citizenship / Birth Certificate)', 'किरण अधिकारी - जन्मदर्ता प्रमाणपत्र',
                '/static/uploads/documents/sample_birth_cert_4.pdf', 290000, 'application/pdf',
                'प्रमाणित', 'जन्मदर्ता रुजु भयो।', 1, 'प्रशासक (Super Admin)', '2026-11-15 12:30:00'
            ),
            (
                9, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'लब्धांक पत्र / मार्कसिट (Marksheet)', 'किरण अधिकारी - कक्षा १० मार्कसिट',
                '/static/uploads/documents/sample_marksheet_2.pdf', 480000, 'application/pdf',
                'जाँच हुन बाँकी', '', None, '', None
            ),
            (
                9, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'चारित्रिक प्रमाणपत्र (Character Certificate)', 'किरण अधिकारी - चारित्रिक प्रमाणपत्र',
                '/static/uploads/documents/sample_char_2.pdf', 340000, 'application/pdf',
                'सुधार आवश्यक', 'विद्यालयको आधिकारिक छाप नबुझिने भएकाले स्पष्ट प्रतिलिपि पेश गर्नुहोस्।', 1, 'प्रशासक (Super Admin)', '2026-11-15 12:35:00'
            ),
            (
                9, None, 'कक्षा १२ - म्यानेजमेन्ट', 12, 17, 'class_11_12',
                'स्थानान्तरण प्रमाणपत्र / TC (Transfer Certificate)', 'किरण अधिकारी - TC कागजात',
                '/static/uploads/documents/sample_tc_2.pdf', 295000, 'application/pdf',
                'अस्वीकृत', 'अपूरो र अन्य विद्यालयको नाम नखुलेको TC अमान्य ठहरियो।', 1, 'प्रशासक (Super Admin)', '2026-11-15 12:38:00'
            ),

            # 6. Manish Poudel (Class 1, age 7) -> Nursery to 10 group
            (
                10, None, 'कक्षा १', 1, 7, 'nursery_to_10',
                'विद्यार्थीको जन्मदर्ता (Birth Certificate)', 'मनिष पौडेल - जन्मदर्ता प्रमाणपत्र',
                '/static/uploads/documents/sample_birth_cert_5.pdf', 310000, 'application/pdf',
                'जाँच हुन बाँकी', '', None, '', None
            ),
            (
                10, None, 'कक्षा १', 1, 7, 'nursery_to_10',
                'अभिभावकको नागरिकता (Guardian Citizenship)', 'हेमराज पौडेल - अभिभावक नागरिकता',
                '/static/uploads/documents/sample_citizenship_5.jpg', 225000, 'image/jpeg',
                'जाँच हुन बाँकी', '', None, '', None
            )
        ]

        cur.executemany("""
            INSERT INTO student_documents (
                student_id, admission_id, student_class, class_numeric, student_age, requirement_group,
                document_type, document_name, file_path, file_size, mime_type,
                verification_status, verification_note, verified_by, verified_by_name, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        print(f"  Inserted {len(seed_data)} seed documents.")

    conn.commit()
    conn.close()
    print(f"✓ Migration complete for {db_path}")

if __name__ == "__main__":
    for db in ['school.db', 'api/school.db']:
        if os.path.exists(db):
            migrate_db(db)
