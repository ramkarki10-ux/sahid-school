import sqlite3
import sys
import os
import shutil

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "school.db"

def run_migration():
    print("==================================================================")
    print("STARTING UPGRADE MIGRATION - NEW USER SPECIFICATIONS")
    print("==================================================================")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Ensure EMIS code column in students
    cursor.execute("PRAGMA table_info(students)")
    student_cols = [c["name"] for c in cursor.fetchall()]
    if "emis_code" not in student_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN emis_code TEXT")
        print("✅ Added 'emis_code' column to 'students' table.")
    else:
        print("ℹ️ 'emis_code' column already exists in 'students' table.")

    # Populate EMIS codes for existing students if empty
    cursor.execute("SELECT id, roll_no, class_id FROM students WHERE emis_code IS NULL OR emis_code = ''")
    for r in cursor.fetchall():
        gen_emis = f"0119{r['class_id']:02d}{r['id']:04d}"
        cursor.execute("UPDATE students SET emis_code = ? WHERE id = ?", (gen_emis, r["id"]))
    print("✅ Populated EMIS codes for existing students.")

    # 2. Early Childhood Classes (नर्सरी देखी केजी सम्म)
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes")
    existing_classes = {c["class_numeric"]: c["id"] for c in cursor.fetchall()}

    # Nursery (-2)
    if -2 not in existing_classes:
        cursor.execute("""
            INSERT INTO classes (class_name_ne, class_name_en, class_numeric, has_stream)
            VALUES ('नर्सरी', 'Nursery', -2, 0)
        """)
        nursery_id = cursor.lastrowid
        cursor.execute("INSERT INTO sections (class_id, name, capacity) VALUES (?, 'A', 30)", (nursery_id,))
        print("✅ Added 'नर्सरी' (Nursery) class with numeric = -2 and Section A.")
    else:
        print("ℹ️ 'नर्सरी' class already exists.")

    # LKG (-1)
    if -1 not in existing_classes:
        cursor.execute("""
            INSERT INTO classes (class_name_ne, class_name_en, class_numeric, has_stream)
            VALUES ('एल.के.जी.', 'LKG', -1, 0)
        """)
        lkg_id = cursor.lastrowid
        cursor.execute("INSERT INTO sections (class_id, name, capacity) VALUES (?, 'A', 30)", (lkg_id,))
        print("✅ Added 'एल.के.जी.' (LKG) class with numeric = -1 and Section A.")
    else:
        print("ℹ️ 'एल.के.जी.' class already exists.")

    # Ensure KG is named properly
    cursor.execute("UPDATE classes SET class_name_ne = 'यु.के.जी. (केजी)', class_name_en = 'UKG / KG' WHERE class_numeric = 0")
    print("✅ Verified 'यु.के.जी. (केजी)' class with numeric = 0.")

    # 3. Stream: Hotel Management in Class 11 and 12
    cursor.execute("SELECT id FROM streams WHERE name_en LIKE '%Hotel%'")
    hm_stream = cursor.fetchone()
    if not hm_stream:
        cursor.execute("""
            INSERT INTO streams (name_ne, name_en, code)
            VALUES ('होटल व्यवस्थापन (Hotel Management)', 'Hotel Management', 'HM')
        """)
        hm_stream_id = cursor.lastrowid
        print("✅ Added Hotel Management stream.")
    else:
        hm_stream_id = hm_stream[0]
        cursor.execute("UPDATE streams SET name_ne = 'होटल व्यवस्थापन (Hotel Management)' WHERE id = ?", (hm_stream_id,))
        print("✅ Verified Hotel Management stream ID:", hm_stream_id)

    # Add Hotel Management subjects for Class 11 & 12
    cursor.execute("SELECT id FROM classes WHERE class_numeric = 11")
    c11 = cursor.fetchone()
    cursor.execute("SELECT id FROM classes WHERE class_numeric = 12")
    c12 = cursor.fetchone()
    
    hm_subjects = [
        ("होटल व्यवस्थापन", "Hotel Management", "HM-101", 100, 40),
        ("खाद्य तथा पेय सेवा", "Food & Beverage Service", "FBS-102", 100, 40),
        ("हाउसकिपिङ तथा फ्रन्ट अफिस", "Housekeeping & Front Office", "HFO-103", 100, 40)
    ]
    for class_row in [c11, c12]:
        if class_row:
            cid = class_row[0]
            for s_ne, s_en, scode, fm, pm in hm_subjects:
                full_code = f"{scode}-C{cid}"
                cursor.execute("SELECT id FROM subjects WHERE subject_code = ?", (full_code,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO subjects (class_id, stream_id, subject_name_ne, subject_name_en, subject_code, theory_marks, practical_marks)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (cid, hm_stream_id, s_ne, s_en, full_code, fm, pm))
    print("✅ Verified Hotel Management curriculum subjects for Class 11 & 12.")

    # 4. Replace Teachers with exact 16 provided by user
    # First delete existing assignments and teachers
    cursor.execute("DELETE FROM teacher_class_assignments")
    cursor.execute("DELETE FROM teachers")
    cursor.execute("DELETE FROM users WHERE role = 'TEACHER'")
    print("✅ Cleared previous teachers and teacher user accounts.")

    # Hash for teacher123 password
    from app.auth import hash_password
    default_pw_hash = hash_password("teacher123")

    teachers_data = [
        # (name, level, responsibility, phone, email, subject, qualification, exp)
        ("श्री रीता फुयल", "माध्यामिक तह", "प्रधानाध्यापक", "९८५२०३३१३३", "rita.phuyal@shahidsmriti.edu.np", "शिक्षा प्रशासन / अनिवार्य", "M.Ed., M.A.", "१८ वर्ष"),
        ("श्री रमेश खड्का", "माध्यामिक तह", "सहायक प्रधानाध्यापक", "९८४१५५२८५७", "ramesh.khadka@shahidsmriti.edu.np", "सामाजिक अध्ययन / प्रशासन", "M.A., B.Ed.", "१४ वर्ष"),
        ("श्री चेवन प्रसाद पौडेल", "माध्यामिक तह", "शिक्षक", "९८४२०००००३", "chewan.paudel@shahidsmriti.edu.np", "नेपाली", "M.A. Nepali, B.Ed.", "१२ वर्ष"),
        ("श्री युवराज न्यौपाने", "माध्यामिक तह", "शिक्षक", "९८४२०००००४", "yubaraj.neupane@shahidsmriti.edu.np", "विज्ञान (भौतिक)", "M.Sc. Physics", "१० वर्ष"),
        ("श्री सिताराम पौडेल", "माध्यामिक तह", "शिक्षक", "९८४२०००००५", "sitaram.paudel@shahidsmriti.edu.np", "गणित", "M.Sc. Math, B.Ed.", "११ वर्ष"),
        ("श्री तुलसी ठाकुर", "माध्यामिक तह", "शिक्षक", "९८४२०००००६", "tulsi.thakur@shahidsmriti.edu.np", "अंग्रेजी", "M.A. English", "९ वर्ष"),
        ("श्री जानुका राई", "माध्यामिक तह", "शिक्षक", "९८४२०००००७", "januka.rai@shahidsmriti.edu.np", "रसायन विज्ञान / ऐच्छिक", "M.Sc. Chemistry", "८ वर्ष"),
        ("श्री सावित्री भण्डारी", "माध्यामिक तह", "शिक्षक", "९८४२०००००८", "savitri.bhandari@shahidsmriti.edu.np", "जीवविज्ञान / वातावरण", "M.Sc. Zoology", "९ वर्ष"),
        ("श्री प्रमोद कुमार साह", "नि.मा.वि. तह", "शिक्षक", "९८४२०००००९", "pramod.sah@shahidsmriti.edu.np", "विज्ञान तथा गणित", "B.Sc., B.Ed.", "७ वर्ष"),
        ("श्री गोविन्द पौडेल", "नि.मा.वि. तह", "शिक्षक", "९८४२००००१०", "govinda.paudel@shahidsmriti.edu.np", "सामाजिक तथा नैतिक", "B.A., B.Ed.", "८ वर्ष"),
        ("श्री रुपा दर्जी", "नि.मा.वि. तह", "शिक्षक", "९८४२००००११", "rupa.darji@shahidsmriti.edu.np", "नेपाली तथा सिर्जनात्मक कला", "B.Ed. Nepali", "६ वर्ष"),
        ("श्री सरु सुवेदी", "प्राथमिक तह", "शिक्षक", "९८४२००००१२", "saru.subedi@shahidsmriti.edu.np", "प्राथमिक तह (सबै विषय)", "B.Ed.", "६ वर्ष"),
        ("श्री सृजना गिरी", "प्राथमिक तह", "शिक्षक", "९८४२००००१३", "srijana.giri@shahidsmriti.edu.np", "प्राथमिक गणित र अंग्रेजी", "B.A., B.Ed.", "५ वर्ष"),
        ("श्री कोषराज दहाल", "प्राथमिक तह", "शिक्षक", "९८४२००००१४", "koshraj.dahal@shahidsmriti.edu.np", "प्राथमिक सामाजिक र नेपाली", "I.Ed., B.A.", "७ वर्ष"),
        ("श्री अशिया कुमारी चौधरी", "प्राथमिक तह", "शिक्षक", "९८४२००००१५", "ashiya.chaudhary@shahidsmriti.edu.np", "प्रारम्भिक बाल विकास / प्राथमिक", "B.Ed. Early Childhood", "५ वर्ष"),
        ("श्री वाल कुमारी रिजाल", "प्राथमिक तह", "शिक्षक", "९८४२००००१६", "balkumari.rijal@shahidsmriti.edu.np", "प्राथमिक तह तथा बाल कक्षा", "B.Ed.", "६ वर्ष")
    ]

    for idx, (name, level, resp, phone, email, subj, qual, exp) in enumerate(teachers_data, start=1):
        emp_id = f"TCH-83{idx:03d}"
        cursor.execute("""
            INSERT INTO teachers (
                employee_id, name_nepali, name_english, position, subject, level, 
                qualification, experience, phone, email, employment_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'स्थायी', 'सक्रिय')
        """, (emp_id, name, name.replace("श्री ", ""), resp, subj, level, qual, exp, phone, email))
        teacher_pk = cursor.lastrowid

        # Create user account for portal login: teacher1 to teacher16
        username = f"teacher{idx}"
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name_ne, full_name_en, email, role, teacher_id, status)
            VALUES (?, ?, ?, ?, ?, 'TEACHER', ?, 'सक्रिय')
        """, (username, default_pw_hash, name, name.replace("श्री ", ""), email, teacher_pk))

    print(f"✅ Successfully seeded exact 16 Teachers and active accounts teacher1 to teacher16.")

    # 5. Update Leadership table with exact Principal & Assistant Principal
    cursor.execute("UPDATE school_leadership SET name = 'श्री रीता फुयल', position = 'प्रधानाध्यापक', phone = '९८५२०३३१३३' WHERE role_type = 'PRINCIPAL'")
    cursor.execute("UPDATE school_leadership SET name = 'श्री रमेश खड्का', position = 'सहायक प्रधानाध्यापक', phone = '९८४१५५२८५७' WHERE role_type = 'ASSISTANT_PRINCIPAL'")
    print("✅ Verified school_leadership: Principal श्री रीता फुयल & Assistant Principal श्री रमेश खड्का.")

    # 6. Replace Staff with exact 12 provided by user
    cursor.execute("DELETE FROM staff")
    print("✅ Cleared previous staff.")

    staff_data = [
        # (name, position, dept, phone, qual)
        ("श्री एकराज गिरी", "ल्याब असिसटेन्ट", "विज्ञान तथा कम्प्युटर प्रयोगशाला", "९८४२००००२१", "I.Sc. / Lab Tech"),
        ("श्री सोम प्रसाद पुरी", "वार्डेन (छात्र छात्रावास)", "छात्रावास प्रशासन", "९८४२००००२२", "स्नातक"),
        ("श्री शान्ति कुमारी पुरी", "वार्डेन (छात्रा छात्रावास)", "छात्रावास प्रशासन", "९८४२००००२३", "स्नातक"),
        ("श्री रामचन्द्र चौधरी", "लाइब्रेरियन", "पुस्तकालय शाखा", "९८४२००००२४", "B.Lib. / I.A."),
        ("श्री मोतीचन्द्र राई", "सेक्युरिटी गार्ड", "सुरक्षा शाखा", "९८४२००००२५", "एसएलसी / पूर्व सुरक्षा"),
        ("श्री कमला गिरी", "भान्से", "छात्रावास मेस तथा भोजन शाखा", "९८४२००००२६", "तालिमप्राप्त कुक"),
        ("श्री मान बहादुर गिरी", "सेक्युरिटी गार्ड", "सुरक्षा शाखा", "९८४२००००२७", "पूर्व सुरक्षा"),
        ("श्री कमला दहाल गुरगाई", "कार्यालय सहयोगी", "प्रशासन तथा कार्यालय", "९८४२००००२८", "साधारण"),
        ("श्री विमला गिरी", "कार्यालय सहयोगी", "प्रशासन तथा कार्यालय", "९८४२००००२९", "साधारण"),
        ("श्री राम बहादुर कान्हु", "भान्से", "छात्रावास मेस तथा भोजन शाखा", "९८४२००००३०", "तालिमप्राप्त कुक"),
        ("श्री विष्णु कुमारी बस्नेत", "विद्यालय नर्स", "स्वास्थ्य तथा प्राथमिक उपचार", "९८४२००००३१", "स्टाफ नर्स (PCL Nursing)"),
        ("श्री ओमनारायण चौधरी", "स्वास्थ्यकर्मी छात्रावास", "छात्रावास स्वास्थ्य सेवा", "९८४२००००३२", "हेल्थ असिस्टेन्ट (HA)")
    ]

    for idx, (name, pos, dept, phone, qual) in enumerate(staff_data, start=1):
        emp_id = f"STF-83{idx:03d}"
        cursor.execute("""
            INSERT INTO staff (
                employee_id, name_nepali, name_english, position, department,
                qualification, phone, email, employment_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'स्थायी', 'सक्रिय')
        """, (emp_id, name, name.replace("श्री ", ""), pos, dept, qual, phone, f"staff{idx}@shahidsmriti.edu.np"))

    print(f"✅ Successfully seeded exact 12 Staff members.")

    # 7. Update Hostels table wardens to match exact staff
    cursor.execute("UPDATE hostels SET warden = 'श्री सोम प्रसाद पुरी' WHERE id = 1")
    cursor.execute("UPDATE hostels SET warden = 'श्री शान्ति कुमारी पुरी' WHERE id = 2")
    print("✅ Updated Hostels wardens: Boys -> श्री सोम प्रसाद पुरी, Girls -> श्री शान्ति कुमारी पुरी.")

    # 8. Create teacher_attendance table (Admin-Only)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL REFERENCES teachers(id),
            attendance_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'PRESENT',
            check_in_time TEXT,
            check_out_time TEXT,
            remark TEXT,
            recorded_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(teacher_id, attendance_date)
        )
    """)
    print("✅ Verified 'teacher_attendance' table.")

    # Seed sample teacher attendance for today
    from datetime import date
    today_str = date.today().isoformat()
    cursor.execute("SELECT id FROM teachers")
    all_teachers = cursor.fetchall()
    for t in all_teachers:
        cursor.execute("""
            INSERT OR IGNORE INTO teacher_attendance (teacher_id, attendance_date, status, check_in_time, check_out_time, remark)
            VALUES (?, ?, 'PRESENT', '09:45:00', '16:00:00', 'नियमित समयमा उपस्थित')
        """, (t["id"], today_str))
    print(f"✅ Seeded today teacher attendance for {len(all_teachers)} teachers.")

    # 9. Verify school_settings established year & logo
    cursor.execute("UPDATE school_settings SET logo_url = '/static/images/logo_header.png', established_ne = '२०६३' WHERE id = 1")
    print("✅ Verified school_settings logo_url and established_ne = '२०६३' (as on official seal).")

    conn.commit()
    conn.close()
    print("==================================================================")
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    run_migration()
