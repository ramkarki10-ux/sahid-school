import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, date

# Reconfigure stdout for UTF-8 in Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(__file__).resolve().parent / "school.db"

# Hash password helper using PBKDF2
import hashlib
import secrets

def hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def run_migration():
    print("Beginning migration on:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Update School Settings
    print("Step 1: Updating school contact info and Facebook URL...")
    cursor.execute("""
        UPDATE school_settings
        SET phone = '९८५२०३३१३३, ९८४१५५२८५७',
            notice_board_phone = '९८४१५५२८५७',
            facebook_url = 'https://www.facebook.com/profile.php?id=100092258731456',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)

    # 2. Global removal of 'श्रीमती' -> 'श्री'
    print("Step 2: Enforcing 'श्री' universally across all tables...")
    
    # In school_leadership
    cursor.execute("SELECT id, name, position, biography, message_ne FROM school_leadership")
    for row in cursor.fetchall():
        new_name = row["name"].replace("श्रीमती", "श्री")
        new_bio = (row["biography"] or "").replace("श्रीमती", "श्री")
        new_msg = (row["message_ne"] or "").replace("श्रीमती", "श्री")
        cursor.execute("""
            UPDATE school_leadership 
            SET name = ?, biography = ?, message_ne = ?
            WHERE id = ?
        """, (new_name, new_bio, new_msg, row["id"]))

    # Specifically update Principal contact
    cursor.execute("""
        UPDATE school_leadership
        SET name = 'श्री रीता फुयल',
            phone = '९८५२०३३१३३'
        WHERE role_type = 'PRINCIPAL'
    """)

    # In school_management_committee
    # Remove any existing rows and replace with the official SMC list
    print("Step 3: Setting official School Management Committee...")
    cursor.execute("DELETE FROM school_management_committee")
    smc_members = [
        ('श्री राम बहादुर कार्की', 'अध्यक्ष', '९८५२०२८२४०', 1),
        ('श्री राम कुमारी चौधरी', 'सदस्य', '९८४२०००००२', 2),
        ('श्री सन्तोष खतिवडा', 'सदस्य', '९८४२०००००३', 3),
        ('श्री सूर्य बहादुर थापा', 'सदस्य', '९८४२०००००४', 4),
        ('श्री तीर्थ कुमारी वन', 'सदस्य', '९८४२०००००५', 5),
        ('श्री पूजा खनाल', 'सदस्य', '९८४२०००००६', 6),
        ('श्री कृष्ण गोपाल घिमिरे', 'सदस्य', '९८४२०००००७', 7),
        ('श्री राजकुमार आचार्य', 'सदस्य', '९८४२०००००८', 8),
        ('श्री जमुना भण्डारी', 'सदस्य', None, 9),
    ]
    for name, pos, phone, order in smc_members:
        cursor.execute("""
            INSERT INTO school_management_committee (name, position, phone, term, order_index, status)
            VALUES (?, ?, ?, '२०८०-२०८३', ?, 'सक्रिय')
        """, (name, pos, phone, order))

    # In trustee_committee
    cursor.execute("SELECT id, name FROM trustee_committee")
    for row in cursor.fetchall():
        new_name = row["name"].replace("श्रीमती", "श्री")
        cursor.execute("UPDATE trustee_committee SET name = ? WHERE id = ?", (new_name, row["id"]))

    # In teachers
    cursor.execute("SELECT id, name_nepali FROM teachers")
    for row in cursor.fetchall():
        new_name = row["name_nepali"].replace("श्रीमती", "श्री")
        cursor.execute("UPDATE teachers SET name_nepali = ? WHERE id = ?", (new_name, row["id"]))

    # In staff
    cursor.execute("SELECT id, name_nepali FROM staff")
    for row in cursor.fetchall():
        new_name = row["name_nepali"].replace("श्रीमती", "श्री")
        cursor.execute("UPDATE staff SET name_nepali = ? WHERE id = ?", (new_name, row["id"]))

    # In users
    cursor.execute("SELECT id, full_name_ne FROM users")
    for row in cursor.fetchall():
        if row["full_name_ne"]:
            new_name = row["full_name_ne"].replace("श्रीमती", "श्री")
            cursor.execute("UPDATE users SET full_name_ne = ? WHERE id = ?", (new_name, row["id"]))

    # 4. Add Class KG (केजी)
    print("Step 4: Ensuring KG class exists in classes table...")
    cursor.execute("SELECT id FROM classes WHERE class_numeric = 0")
    kg_row = cursor.fetchone()
    if not kg_row:
        cursor.execute("""
            INSERT INTO classes (class_name_ne, class_name_en, class_numeric, has_stream)
            VALUES ('केजी', 'KG', 0, 0)
        """)
        kg_id = cursor.lastrowid
        cursor.execute("INSERT INTO sections (class_id, name, capacity) VALUES (?, 'A', 30)", (kg_id,))
        print("  KG class created with ID:", kg_id)
    else:
        kg_id = kg_row[0]
        print("  KG class already exists with ID:", kg_id)

    # 5. Create New Tables
    print("Step 5: Creating new tables...")

    # 5.1 student_documents
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        admission_id INTEGER,
        document_type TEXT NOT NULL,
        document_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        mime_type TEXT,
        verification_status TEXT DEFAULT 'जाँच हुन बाँकी' CHECK(verification_status IN ('जाँच हुन बाँकी', 'प्रमाणित', 'सुधार आवश्यक', 'अस्वीकृत')),
        verification_note TEXT,
        verified_by INTEGER,
        verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (admission_id) REFERENCES admission_applications(id) ON DELETE CASCADE
    );
    """)

    # 5.2 homework
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        academic_year_id INTEGER NOT NULL DEFAULT 1,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        subject_id INTEGER,
        subject_name TEXT NOT NULL,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        assigned_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        attachment TEXT,
        status TEXT DEFAULT 'सक्रिय',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    );
    """)

    # 5.3 attendance_notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        attendance_event TEXT NOT NULL CHECK(attendance_event IN ('FIRST_PERIOD', 'FINAL_ATTENDANCE')),
        notification_type TEXT NOT NULL DEFAULT 'ABSENCE_SMS',
        recipient_phone TEXT NOT NULL,
        message_content TEXT NOT NULL,
        status TEXT DEFAULT 'SENT' CHECK(status IN ('SENT', 'FAILED', 'PENDING', 'SIMULATED')),
        gateway_response TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, attendance_date, attendance_event, notification_type),
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    """)

    # 5.4 sms_gateway_settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sms_gateway_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name TEXT NOT NULL DEFAULT 'Sparrow SMS',
        api_url TEXT NOT NULL DEFAULT 'https://api.sparrowsms.com/v2/sms/',
        api_key TEXT DEFAULT 'sparrow_sec_live_key_9841',
        sender_id TEXT DEFAULT 'ShahidSmriti',
        username TEXT DEFAULT 'shahidsmriti',
        password TEXT DEFAULT '••••••••',
        balance INTEGER DEFAULT 2480,
        is_enabled INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Insert default SMS settings if not exists
    cursor.execute("SELECT id FROM sms_gateway_settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO sms_gateway_settings (id, provider_name, api_url, api_key, sender_id, username, balance, is_enabled)
            VALUES (1, 'Sparrow SMS (नेपाल)', 'https://api.sparrowsms.com/v2/sms/', 'sparrow_token_live_demo', 'ShahidSmriti', 'shahidsmriti', 2480, 1)
        """)

    # 5.5 parent_accounts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parent_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        pin_hash TEXT NOT NULL,
        guardian_name TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5.6 parent_messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parent_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        guardian_phone TEXT NOT NULL,
        sender_type TEXT NOT NULL CHECK(sender_type IN ('TEACHER', 'PARENT', 'ADMIN')),
        sender_name TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    """)

    # 5.7 leave_applications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        student_name TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        roll_no INTEGER,
        applicant_name TEXT NOT NULL,
        applicant_phone TEXT NOT NULL,
        reason TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_days INTEGER DEFAULT 1,
        status TEXT DEFAULT 'विचाराधीन' CHECK(status IN ('विचाराधीन', 'स्वीकृत', 'अस्वीकृत')),
        review_remarks TEXT,
        reviewed_by INTEGER,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5.8 school_calendar_events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_type TEXT NOT NULL DEFAULT 'बिदा' CHECK(event_type IN ('बिदा', 'पर्व', 'परीक्षा', 'खेलकुद', 'वार्षिकोत्सव', 'बैठक', 'अन्य')),
        start_date TEXT NOT NULL,
        end_date TEXT,
        description TEXT,
        is_holiday INTEGER DEFAULT 0,
        color TEXT DEFAULT '#1e3a8a',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Seed Subjects if empty
    print("Step 6: Seeding curriculum subjects...")
    cursor.execute("SELECT COUNT(*) FROM subjects")
    if cursor.fetchone()[0] == 0:
        subjects_data = [
            # Basic level (1-8)
            ("नेपाली", "Nepali", "NEP-101", 75, 25),
            ("अंग्रेजी", "English", "ENG-102", 75, 25),
            ("गणित", "Mathematics", "MTH-103", 75, 25),
            ("विज्ञान तथा प्रविधि", "Science & Technology", "SCI-104", 75, 25),
            ("सामाजिक अध्ययन", "Social Studies", "SOC-105", 75, 25),
            ("स्वास्थ्य, शारीरिक तथा सिर्जनात्मक कला", "Health & Physical", "HPE-106", 50, 50),
            ("कम्प्युटर शिक्षा", "Computer Science", "CMP-107", 50, 50),
            ("नैतिक शिक्षा", "Moral Science", "MOR-108", 100, 0),
            # Secondary (9-10)
            ("अनिवार्य नेपाली", "Compulsory Nepali", "NEP-201", 75, 25),
            ("अनिवार्य अंग्रेजी", "Compulsory English", "ENG-202", 75, 25),
            ("अनिवार्य गणित", "Compulsory Mathematics", "MTH-203", 75, 25),
            ("विज्ञान", "Science", "SCI-204", 75, 25),
            ("सामाजिक अध्ययन तथा जीवनोपयोगी शिक्षा", "Social & Life Skills", "SOC-205", 75, 25),
            ("ऐच्छिक गणित", "Optional Mathematics", "OPT-MTH", 75, 25),
            ("अर्थशास्त्र", "Economics", "OPT-ECO", 75, 25),
            ("लेखाशास्त्र", "Accountancy", "OPT-ACC", 75, 25),
        ]
        # Assign subjects across classes
        cursor.execute("SELECT id FROM classes")
        all_classes = [c[0] for c in cursor.fetchall()]
        for cid in all_classes:
            for sname_ne, sname_en, scode, th, pr in subjects_data[:7]:
                cursor.execute("""
                    INSERT INTO subjects (class_id, subject_name_ne, subject_name_en, subject_code, theory_marks, practical_marks)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cid, sname_ne, sname_en, f"{scode}-{cid}", th, pr))
        print("  Curriculum subjects seeded successfully.")

    # 7. Seed up to 40 Teachers and user accounts
    print("Step 7: Seeding realistic teachers up to 40 with accounts...")
    cursor.execute("SELECT COUNT(*) FROM teachers")
    existing_teacher_count = cursor.fetchone()[0]
    
    # 40 realistic Nepali teacher profiles
    teacher_catalog = [
        ("श्री खगेन्द्र खतिवडा", "Khagendra Khatiwada", "मावि शिक्षक", "गणित", "माध्यमिक", "एम.एस्सी. (गणित)", "९८४२०१०००१"),
        ("श्री सीता अधिकारी", "Sita Adhikari", "मावि शिक्षक", "विज्ञान", "माध्यमिक", "एम.एस्सी. (भौतिकशास्त्र)", "९८४२०१०००२"),
        ("श्री भुपाल कार्की", "Bhupal Karki", "मावि शिक्षक", "अंग्रेजी", "माध्यमिक", "एम.ए. (अंग्रेजी)", "९८४२०१०००३"),
        ("श्री इन्दिरा दाहाल", "Indira Dahal", "मावि शिक्षक", "नेपाली", "माध्यमिक", "एम.ए. (नेपाली)", "९८४२०१०००४"),
        ("श्री टेक बहादुर गुरुङ", "Tek Bahadur Gurung", "मावि शिक्षक", "सामाजिक", "माध्यमिक", "एम.एड. (सामाजिक)", "९८४२०१०००५"),
        ("श्री विप्लव आचार्य", "Biplav Acharya", "मावि शिक्षक", "कम्प्युटर विज्ञान", "माध्यमिक", "बि.ई. कम्प्युटर", "९८४२०१०००६"),
        ("श्री मन्जु भण्डारी", "Manju Bhandari", "निमावि शिक्षक", "विज्ञान", "आधारभूत", "बि.एस्सी., बि.एड.", "९८४२०१०००७"),
        ("श्री सन्दिप श्रेष्ठ", "Sandip Shrestha", "निमावि शिक्षक", "गणित", "आधारभूत", "बि.एस्सी., बि.एड.", "९८४२०१०००८"),
        ("श्री प्रमिला थापा", "Pramila Thapa", "निमावि शिक्षक", "अंग्रेजी", "आधारभूत", "बि.ए. (अंग्रेजी)", "९८४२०१०००९"),
        ("श्री दिपक खनाल", "Deepak Khanal", "निमावि शिक्षक", "सामाजिक", "आधारभूत", "बि.एड. (सामाजिक)", "९८४२०१००१०"),
        ("श्री लक्ष्मी पोखरेल", "Laxmi Pokharel", "निमावि शिक्षक", "नेपाली", "आधारभूत", "बि.एड. (नेपाली)", "९८४२०१००११"),
        ("श्री योगेश लुइँटेल", "Yogesh Luintel", "प्रावि शिक्षक", "आधारभूत सबै विषय", "आधारभूत", "१२ कक्षा उत्तीर्ण, शिक्षक तालिम", "९८४२०१००१२"),
        ("श्री अन्जु तिम्सिना", "Anju Timsina", "प्रावि शिक्षक", "आधारभूत सबै विषय", "आधारभूत", "बि.एड.", "९८४२०१००१३"),
        ("श्री सुजन भट्टराई", "Sujan Bhattarai", "प्रावि शिक्षक", "गणित तथा अंग्रेजी", "आधारभूत", "बि.एड.", "९८४२०१००१४"),
        ("श्री कविता बास्तोला", "Kabita Bastola", "प्रावि शिक्षक", "नेपाली तथा सिर्जनात्मक कला", "आधारभूत", "बि.ए.", "९८४२०१००१५"),
        ("श्री रोशन कोइराला", "Roshan Koirala", "प्रावि शिक्षक", "विज्ञान तथा वातावरण", "आधारभूत", "बि.एस्सी.", "९८४२०१००१६"),
        ("श्री रीता बस्नेत", "Rita Basnet", "पूर्व-प्रावि / केजी शिक्षक", "बालविकास तथा मन्तेस्वरी", "पूर्व-प्राथमिक", "ECD तालिम प्राप्त, १२ कक्षा", "९८४२०१००१७"),
        ("श्री सावित्रा सुवेदी", "Sabitra Subedi", "पूर्व-प्रावि / केजी शिक्षक", "बालविकास तथा मन्तेस्वरी", "पूर्व-प्राथमिक", "ECD तालिम प्राप्त", "९८४२०१००१८"),
        ("श्री रमेश खड्का", "Ramesh Khadka", "सहायक प्र.अ. तथा मावि शिक्षक", "गणित", "माध्यमिक", "एम.एस्सी., बि.एड.", "९८४२०५५६६७"),
        ("श्री रीता फुयल", "Rita Phuyal", "प्रधानाध्यापक", "शैक्षिक नेतृत्व", "प्रशासन", "एम.एड.", "९८५२०३३१३३"),
        ("श्री हेमन्त बराल", "Hemanta Baral", "मावि शिक्षक (+२)", "भौतिक विज्ञान (Physics)", "उच्च माध्यमिक", "एम.एस्सी. भौतिक", "९८४२०१००२१"),
        ("श्री सुष्मा नेपाल", "Sushma Nepal", "मावि शिक्षक (+२)", "रसायन विज्ञान (Chemistry)", "उच्च माध्यमिक", "एम.एस्सी. रसायन", "९८४२०१००२२"),
        ("श्री नकुल कार्की", "Nakul Karki", "मावि शिक्षक (+२)", "जीव विज्ञान (Biology)", "उच्च माध्यमिक", "एम.एस्सी. वनस्पति", "९८४२०१००२३"),
        ("श्री प्रकाश ढकाल", "Prakash Dhakal", "मावि शिक्षक (+२)", "लेखाविधि (Accountancy)", "उच्च माध्यमिक", "एम.बी.एस.", "९८४२०१००२४"),
        ("श्री विनिता रिजाल", "Binita Rijal", "मावि शिक्षक (+२)", "अर्थशास्त्र (Economics)", "उच्च माध्यमिक", "एम.ए. अर्थशास्त्र", "९८४२०१००२५"),
        ("श्री अर्जुन तामाङ", "Arjun Tamang", "मावि शिक्षक (+२)", "होटल व्यवस्थापन", "उच्च माध्यमिक", "BHM, MHM", "९८४२०१००२६"),
        ("श्री मनिषा घिमिरे", "Manisha Ghimire", "मावि शिक्षक (+२)", "कम्प्युटर विज्ञान", "उच्च माध्यमिक", "MCA", "९८४२०१००२७"),
        ("श्री चिरञ्जीवी निरौला", "Chiranjibi Niraula", "शिक्षक", "ऐच्छिक गणित", "माध्यमिक", "एम.एस्सी. गणित", "९८४२०१००२८"),
        ("श्री संगीता सुवेदी", "Sangita Subedi", "शिक्षक", "स्वास्थ्य तथा शारीरिक", "आधारभूत", "B.P.Ed", "९८४२०१००२९"),
        ("श्री सुरज श्रेष्ठ", "Suraj Shrestha", "शिक्षक", "चित्रकला तथा सिर्जनात्मक कला", "आधारभूत", "ललितकला स्नातक", "९८४२०१००३०"),
        ("श्री बिन्दु शर्मा", "Bindu Sharma", "शिक्षक", "संगीत तथा नृत्य", "आधारभूत", "संगीत विशारद", "९८४२०१००३१"),
        ("श्री तारानाथ निरौला", "Taranath Niraula", "शिक्षक", "संस्कृत तथा नैतिक", "आधारभूत", "शास्त्री (संस्कृत)", "९८४२०१००३२"),
        ("श्री नारायण अधिकारी", "Narayan Adhikari", "शिक्षक", "सामान्य ज्ञान तथा अतिरिक्त", "आधारभूत", "बि.एड.", "९८४२०१००३३"),
        ("श्री गंगा पराजुली", "Ganga Parajuli", "शिक्षक", "पुस्तकालय तथा अध्ययन", "आधारभूत", "B.Lib", "९८४२०१००३४"),
        ("श्री कमल पौडेल", "Kamal Poudel", "शिक्षक", "विज्ञान प्रयोगशाला संयोजक", "माध्यमिक", "बि.एस्सी.", "९८४२०१००३५"),
        ("श्री पुष्पा कार्की", "Pushpa Karki", "शिक्षक", "अंग्रेजी भाषा सुधार", "माध्यमिक", "एम.ए. अंग्रेजी", "९८४२०१००३६"),
        ("श्री दिनेश राजवंशी", "Dinesh Rajbanshi", "शिक्षक", "खेलकुद प्रशिक्षक", "सबै तह", "NIS खेलकुद डिप्लोमा", "९८४२०१००३७"),
        ("श्री जानुका कटुवाल", "Januka Katuwal", "शिक्षक", "प्राथमिक तह", "आधारभूत", "१२ कक्षा, तालिम", "९८४२०१००३८"),
        ("श्री राजेन्द्र सुवेदी", "Rajendra Subedi", "शिक्षक", "सामाजिक शिक्षा", "माध्यमिक", "एम.ए.", "९८४२०१००३९"),
        ("श्री शारदा खतिवडा", "Sharada Khatiwada", "शिक्षक", "प्राथमिक तह", "आधारभूत", "बि.ए.", "९८४२०१००४०"),
    ]

    # Insert missing teachers
    teacher_ids = []
    for idx, t in enumerate(teacher_catalog):
        emp_id = f"T-{101 + idx}"
        name_ne, name_en, pos, subj, lvl, qual, phone = t
        cursor.execute("SELECT id FROM teachers WHERE employee_id = ?", (emp_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO teachers (employee_id, name_nepali, name_english, position, subject, level, qualification, experience, phone, employment_type, status)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'स्थायी', 'सक्रिय')
            """, (emp_id, name_ne, name_en, pos, subj, lvl, phone))
            t_id = cursor.lastrowid
        else:
            t_id = existing[0]
            cursor.execute("""
                UPDATE teachers 
                SET name_nepali = ?, name_english = ?, position = ?, subject = ?, level = ?, qualification = NULL, experience = NULL, phone = ?
                WHERE id = ?
            """, (name_ne, name_en, pos, subj, lvl, phone, t_id))
        teacher_ids.append((idx + 1, t_id, name_ne, name_en, phone))

    print(f"  Total teachers ready: {len(teacher_ids)}")

    # Seed User accounts: teacher1 to teacher40 with password teacher123
    print("Step 8: Seeding login credentials teacher1 to teacher40 (password: teacher123)...")
    p_hash = hash_password("teacher123")
    for idx, t_id, name_ne, name_en, phone in teacher_ids:
        uname = f"teacher{idx}"
        cursor.execute("SELECT id FROM users WHERE username = ?", (uname,))
        u_row = cursor.fetchone()
        if not u_row:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name_ne, full_name_en, phone, role, teacher_id, status)
                VALUES (?, ?, ?, ?, ?, ?, 'TEACHER', ?, 'ACTIVE')
            """, (uname, f"teacher{idx}@shahidsmriti.edu.np", p_hash, name_ne, name_en, phone, t_id))
        else:
            cursor.execute("""
                UPDATE users 
                SET full_name_ne = ?, full_name_en = ?, teacher_id = ?, password_hash = ?
                WHERE id = ?
            """, (name_ne, name_en, t_id, p_hash, u_row[0]))

    # Assign teachers to classes so that each teacher can view and manage their class
    print("Step 9: Ensuring teacher class assignments exist for all teachers...")
    cursor.execute("SELECT id FROM classes ORDER BY class_numeric ASC")
    classes = [c[0] for c in cursor.fetchall()]
    for idx, t_id, _, _, _ in teacher_ids:
        assigned_class = classes[(idx - 1) % len(classes)]
        cursor.execute("""
            SELECT id FROM teacher_class_assignments WHERE teacher_id = ? AND class_id = ?
        """, (t_id, assigned_class))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO teacher_class_assignments (teacher_id, academic_year_id, class_id, is_class_teacher)
                VALUES (?, 1, ?, ?)
            """, (t_id, assigned_class, 1 if idx <= len(classes) else 0))

    # 10. Seed Demo KG Students if none exist
    print("Step 10: Ensuring KG has students...")
    cursor.execute("SELECT COUNT(*) FROM students WHERE class_id = ?", (kg_id,))
    if cursor.fetchone()[0] == 0:
        kg_students = [
            ("STU-KG001", "ADM-83KG1", "आरभ कार्की", "Aarav Karki", "छात्र", "२०७८-०२-१५", 1, "इटहरी-१९, सुनसरी", "राम बहादुर कार्की", "९८५२०३३१३३"),
            ("STU-KG002", "ADM-83KG2", "आर्या थापा", "Aarya Thapa", "छात्रा", "२०७८-०४-१०", 2, "इटहरी-१९, भवानीपुर", "सूर्य बहादुर थापा", "९८४२०००००४"),
            ("STU-KG003", "ADM-83KG3", "प्रणिश चौधरी", "Pranish Chaudhary", "छात्र", "२०७८-०५-२२", 3, "इटहरी-१९, सुनसरी", "सुरेश चौधरी", "९८४२००००१०"),
            ("STU-KG004", "ADM-83KG4", "कृतिका दाहाल", "Kritika Dahal", "छात्रा", "२०७८-०६-०५", 4, "इटहरी-१९, सुनसरी", "हरि दाहाल", "९८४२००००११"),
        ]
        cursor.execute("SELECT id FROM sections WHERE class_id = ? LIMIT 1", (kg_id,))
        kg_sec_row = cursor.fetchone()
        sec_id = kg_sec_row[0] if kg_sec_row else None
        for stu_id, adm_no, n_ne, n_en, gnd, dob, rno, addr, gname, gphone in kg_students:
            cursor.execute("""
                INSERT INTO students (
                    student_id, admission_no, name_nepali, name_english, gender,
                    date_of_birth, class_id, section_id, roll_no, address,
                    guardian_name, guardian_relation, guardian_phone, academic_year_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'अभिभावक', ?, 1, 'सक्रिय')
            """, (stu_id, adm_no, n_ne, n_en, gnd, dob, kg_id, sec_id, rno, addr, gname, gphone))
        print("  KG sample students seeded.")

    # 11. Seed Parent Accounts
    print("Step 11: Seeding parent accounts with PIN '1234'...")
    cursor.execute("SELECT DISTINCT guardian_phone, guardian_name FROM students WHERE guardian_phone IS NOT NULL")
    guardians = cursor.fetchall()
    parent_pin_hash = hash_password("1234")
    for gphone, gname in guardians:
        clean_phone = gphone.strip()
        cursor.execute("SELECT id FROM parent_accounts WHERE phone = ?", (clean_phone,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO parent_accounts (phone, pin_hash, guardian_name)
                VALUES (?, ?, ?)
            """, (clean_phone, parent_pin_hash, gname))

    # 12. Seed Demo Calendar Events
    print("Step 12: Seeding school calendar events...")
    cursor.execute("SELECT COUNT(*) FROM school_calendar_events")
    if cursor.fetchone()[0] == 0:
        events = [
            ("शैक्षिक सत्र २०८३ प्रारम्भ तथा पुस्तक वितरण", "अन्य", "२०८३-०१-०२", "२०८३-०१-०५", "नयाँ शैक्षिक सत्रको कक्षा सञ्चालन प्रारम्भ", 0, "#2563eb"),
            ("प्रथम त्रैमासिक परीक्षा", "परीक्षा", "२०८३-०३-१५", "२०८३-०३-२४", "कक्षा १ देखि १२ सम्मको प्रथम त्रैमासिक परीक्षा", 0, "#d97706"),
            ("बर्खे बिदा (Summer Vacation)", "बिदा", "२०८३-०३-२६", "२०८३-०४-०८", "गर्मी तथा वर्षाको विदा", 1, "#dc2626"),
            ("श्रीकृष्ण जन्माष्टमी तथा सांस्कृतिक कार्यक्रम", "पर्व", "२०८३-०५-१०", None, "सांस्कृतिक भजन तथा झाँकी प्रदर्शन", 1, "#7c3aed"),
            ("अन्तर-सदन खेलकुद सप्ताह", "खेलकुद", "२०८३-०५-२२", "२०८३-०५-२८", "फुटबल, भलिबल, एथलेटिक्स तथा बुद्धिचाल प्रतियोगिता", 0, "#059669"),
            ("बडा दशैं बिदा", "बिदा", "२०८३-०६-१२", "२०८३-०६-२८", "विजया दशमी तथा घटस्थापना बिदा", 1, "#dc2626"),
            ("शुभ दीपावली तथा छठ पर्व बिदा", "पर्व", "२०८३-०७-१४", "२०८३-०७-२२", "तिहार तथा छठ पर्वको सार्वजनिक बिदा", 1, "#dc2626"),
            ("द्वितीय त्रैमासिक परीक्षा", "परीक्षा", "२०८३-०८-२०", "२०८३-०८-२९", "अर्धवार्षिक मूल्याङ्कन परीक्षा", 0, "#d97706"),
            ("वार्षिकोत्सव तथा अभिभावक दिवस २०८३", "वार्षिकोत्सव", "२०८३-०९-१५", None, "सहिद स्मृति विद्यालयको भव्य वार्षिक उत्सव समारोह", 0, "#b45309"),
            ("विद्यालय व्यवस्थापन समिति बैठक", "बैठक", "२०८३-१०-०५", None, "त्रैमासिक समीक्षा तथा भौतिक पूर्वाधार सम्बन्धी बैठक", 0, "#4338ca"),
        ]
        for title, etype, sdate, edate, desc, is_hol, col in events:
            cursor.execute("""
                INSERT INTO school_calendar_events (title, event_type, start_date, end_date, description, is_holiday, color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, etype, sdate, edate, desc, is_hol, col))
        print("  School calendar events seeded.")

    # 13. Seed Demo Homework items
    print("Step 13: Seeding sample homework items...")
    cursor.execute("SELECT COUNT(*) FROM homework")
    if cursor.fetchone()[0] == 0:
        today_str = date.today().isoformat()
        sample_hw = [
            (8, "नेपाली", 1, "पाठ ४ 'माटोको माया' अभ्यास १ देखि ५ सम्म गर्नुहोस्", "पाठ्यपुस्तकको पृष्ठ ३२ मा रहेका शब्दार्थ तथा प्रश्नोत्तर सफा अक्षरमा गृहकार्य कापीमा लेखेर ल्याउनुहोस्।", today_str, today_str),
            (8, "गणित", 2, "अभ्यास २.३: समूह (Sets) का भेनचित्र समस्याहरू", "प्रश्न १ देखि १० सम्मका सबै गणितीय समस्याहरू समाधान गर्नुहोस्।", today_str, today_str),
            (8, "विज्ञान", 3, "बल र गति (Force & Motion) को नियमहरू र उदाहरण", "न्युटनका गतिका तीनै नियमहरू लेखी दैनिक जीवनका दुई-दुई उदाहरण प्रस्तुत गर्नुहोस्।", today_str, today_str),
            (kg_id, "बालविकास", 17, "वर्णमाला (क देखि ङ) र रङ भर्ने अभ्यास", "कार्यपुस्तिका पृष्ठ ८ मा दिइएका चित्रहरूमा मनपर्ने रङ भरी अक्षर चिन्नुहोस्।", today_str, today_str),
        ]
        for cid, subj, tid, title, desc, adate, ddate in sample_hw:
            cursor.execute("""
                INSERT INTO homework (class_id, subject_name, teacher_id, title, description, assigned_date, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cid, subj, tid, title, desc, adate, ddate))
        print("  Sample homework seeded.")

    # 14. Seed Demo Leave Application
    print("Step 14: Seeding sample leave application...")
    cursor.execute("SELECT COUNT(*) FROM leave_applications")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO leave_applications (
                student_id, student_name, class_id, roll_no, applicant_name, applicant_phone,
                reason, start_date, end_date, total_days, status, review_remarks
            ) VALUES (
                1, 'रोहित कार्की', 8, 1, 'राम बहादुर कार्की', '९८५२०३३१३३',
                'घरायसी विशेष कामले गर्दा २ दिन उपस्थित हुन असमर्थ भएकोले बिदा पाउँ।',
                '२०८३-०५-०१', '२०८३-०५-०२', 2, 'स्वीकृत', 'बिदा स्वीकृत गरियो।'
            )
        """)
        print("  Sample leave application seeded.")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
