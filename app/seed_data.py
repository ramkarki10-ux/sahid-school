import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from app.database import get_db, init_db
from app.auth import hash_password

def seed_all():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. School Settings
    cursor.execute("SELECT COUNT(*) FROM school_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO school_settings (
                name_ne, name_en, tagline_ne, tagline_en,
                address_ne, address_en, established_ne, established_en,
                phone, notice_board_phone, email, facebook_url, youtube_url,
                logo_url, about_text_ne
            ) VALUES (
                'सहिद स्मृति आवासीय माध्यमिक विद्यालय',
                'Shahid Smriti Residential Secondary School',
                'सहिदका सपना, गुणस्तरीय शिक्षा र आवासीय सुविधायुक्त नमुना विद्यालय',
                'Excellence in Residential Education & Nation Building',
                'इटहरी–१९, सुनसरी, कोशी प्रदेश, नेपाल',
                'Itahari-19, Sunsari, Koshi Province, Nepal',
                '२०६६',
                '2009',
                '९८५२०३३१३३, ९८४१५५२८५७',
                '१६१८०२५–५८०१२४',
                'info@shahidsmriti.edu.np',
                'https://facebook.com',
                'https://youtube.com',
                '/static/images/logo_header.png',
                'सहिद स्मृति आवासीय माध्यमिक विद्यालय वि.सं. २०६६ सालमा सहिद परिवार, द्वन्द्वपीडित, घाइते, अपाङ्गता भएका तथा विपन्न वर्गका बालबालिकाहरूलाई सर्वसुलभ, आवासीय र आधुनिक प्रविधियुक्त गुणस्तरीय शिक्षा प्रदान गर्ने पवित्र उद्देश्यका साथ स्थापित भएको शैक्षिक धरोहर हो। इटहरी–१९ भवानीपुरमा शान्त र हरियाली वातावरणमा अवस्थित यस विद्यालयमा कक्षा १ देखि १२ सम्म विज्ञान, कम्प्युटर विज्ञान, व्यवस्थापन लगायतका संकायहरूमा उत्कृष्ट पठनपाठन सञ्चालन भइरहेको छ।'
            )
        """)
        
    # 2. Roles
    roles_data = [
        ("SUPER_ADMIN", "सुपर एडमिन", "सम्पूर्ण प्रणाली नियन्त्रण"),
        ("PRINCIPAL", "प्रधानाध्यापक", "शैक्षिक, प्रशासनिक तथा नतिजा व्यवस्थापन"),
        ("TEACHER", "शिक्षक", "कक्षा हाजिरी, विद्यार्थी तथा विषय व्यवस्थापन"),
        ("HOSTEL_WARDEN", "छात्रावास वार्डेन", "छात्रावास तथा आवासीय विद्यार्थी व्यवस्थापन"),
        ("CONTENT_EDITOR", "सूचना सम्पादक", "सूचना, समाचार, ग्यालेरी र प्रकाशन"),
        ("VIEWER", "अवलोकनकर्ता", "पढ्न मात्र अनुमति")
    ]
    for r in roles_data:
        cursor.execute("INSERT OR IGNORE INTO roles (name, display_name_ne, description) VALUES (?, ?, ?)", r)
        
    # 3. Academic Years
    academic_years = [
        ("२०८३", "2026/27", "2083-01-01", "2083-12-30", 1),
        ("२०८२", "2025/26", "2082-01-01", "2082-12-30", 0),
        ("२०८१", "2024/25", "2081-01-01", "2081-12-30", 0)
    ]
    for ay in academic_years:
        cursor.execute("""
            INSERT OR IGNORE INTO academic_years (year_ne, year_en, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, ay)
        
    cursor.execute("SELECT id FROM academic_years WHERE year_ne = '२०८३'")
    active_year_row = cursor.fetchone()
    active_year_id = active_year_row[0] if active_year_row else 1
    cursor.execute("UPDATE school_settings SET active_academic_year_id = ?", (active_year_id,))

    # 4. Classes (1 to 12)
    classes_data = [
        ("कक्षा १", "Class 1", 1, 0),
        ("कक्षा २", "Class 2", 2, 0),
        ("कक्षा ३", "Class 3", 3, 0),
        ("कक्षा ४", "Class 4", 4, 0),
        ("कक्षा ५", "Class 5", 5, 0),
        ("कक्षा ६", "Class 6", 6, 0),
        ("कक्षा ७", "Class 7", 7, 0),
        ("कक्षा ८", "Class 8", 8, 0),
        ("कक्षा ९", "Class 9", 9, 0),
        ("कक्षा १०", "Class 10", 10, 0),
        ("कक्षा ११", "Class 11", 11, 1),
        ("कक्षा १२", "Class 12", 12, 1)
    ]
    for cd in classes_data:
        cursor.execute("""
            INSERT OR IGNORE INTO classes (class_name_ne, class_name_en, class_numeric, has_stream)
            VALUES (?, ?, ?, ?)
        """, cd)

    # Sections for each class (A, B)
    cursor.execute("SELECT id FROM classes")
    all_classes = cursor.fetchall()
    for c in all_classes:
        for sname in ["A", "B"]:
            cursor.execute("INSERT OR IGNORE INTO sections (class_id, name, capacity) VALUES (?, ?, 40)", (c["id"], sname))

    # Streams for Class 11-12
    streams_data = [
        ("विज्ञान (Science)", "Science", "SCI"),
        ("कम्प्युटर विज्ञान (Computer Science)", "Computer Science", "CS"),
        ("व्यवस्थापन (Management)", "Management", "MGT"),
        ("होटेल व्यवस्थापन (Hotel Management)", "Hotel Management", "HM"),
        ("अन्य (Other)", "Other", "OTH")
    ]
    for st in streams_data:
        cursor.execute("INSERT OR IGNORE INTO streams (name_ne, name_en, code) VALUES (?, ?, ?)", st)

    # 5. School Management Committee (Seed data from Section 11 & 64)
    cursor.execute("SELECT COUNT(*) FROM school_management_committee")
    if cursor.fetchone()[0] == 0:
        smc_members = [
            ("श्री राम बहादुर कार्की", "अध्यक्ष", "९८४२०००००१", 1),
            ("श्री राम कुमारी चौधरी", "सदस्य", "९८४२०००००२", 2),
            ("श्री सन्तोष खतिवडा", "सदस्य", "९८४२०००००३", 3),
            ("श्री सूर्य बहादुर थापा", "सदस्य", "९८४२०००००४", 4),
            ("श्री तीर्थ कुमारी वन", "सदस्य", "९८४२०००००५", 5),
            ("श्री पूजा खनाल", "सदस्य", "९८४२०००००६", 6),
            ("श्री कृष्ण गोपाल घिमिरे", "सदस्य", "९८४२०००००७", 7),
            ("श्री राजकुमार आचार्य", "सदस्य", "९८४२०००००८", 8),
            ("श्री जमुना", "सदस्य", "९८४२०००००९", 9)
        ]
        for m in smc_members:
            cursor.execute("""
                INSERT INTO school_management_committee (name, position, phone, order_index)
                VALUES (?, ?, ?, ?)
            """, m)

    # 6. Trustee Committee / गुठियार समिति (Seed data from Section 12 & 64)
    cursor.execute("SELECT COUNT(*) FROM trustee_committee")
    if cursor.fetchone()[0] == 0:
        trustee_members = [
            ("धर्मशिला चापागाई", "गुठियार प्रमुख", "९८५२०००००१", 1),
            ("मणिकुमार साम्पाङ", "सदस्य", "९८५२०००००२", 2),
            ("राम बहादुर कार्की", "सदस्य", "९८५२०००००३", 3),
            ("राम कुमारी चौधरी", "सदस्य", "९८५२०००००४", 4),
            ("पूजा खनाल", "सदस्य", "९८५२०००००५", 5),
            ("कृष्ण गोपाल घिमिरे", "सदस्य", "९८५२०००००६", 6),
            ("केशर बहादुर प्रधान", "सदस्य", "९८५२०००००७", 7),
            ("मणिराम गिरी", "सदस्य", "९८५२०००००८", 8),
            ("सपना परियार", "सदस्य", "९८५२०००००९", 9)
        ]
        for t in trustee_members:
            cursor.execute("""
                INSERT INTO trustee_committee (name, position, phone, order_index)
                VALUES (?, ?, ?, ?)
            """, t)

    # 7. School Leadership (Section 13 & 64)
    cursor.execute("SELECT COUNT(*) FROM school_leadership")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO school_leadership (
                role_type, name, position, qualification, experience, phone, email, message_ne, biography
            ) VALUES (
                'PRINCIPAL',
                'श्री रीता फुयल',
                'प्रधानाध्यापक',
                'एम.एड. (शैक्षिक नेतृत्व तथा व्यवस्थापन)',
                '१५ वर्षभन्दा बढी शैक्षिक तथा प्रशासनिक अनुभव',
                '९८५२०२२३३४',
                'principal@shahidsmriti.edu.np',
                'आदरणीय अभिभावक, शिक्षक, तथा प्यारा विद्यार्थी भाइबहिनीहरू, सहिद स्मृति आवासीय माध्यमिक विद्यालय इटहरीमा तपाईंहरूलाई हार्दिक स्वागत छ। यस विद्यालयले विद्यार्थीहरूको बौद्धिक, शारीरिक, मानसिक तथा नैतिक विकासलाई उच्च प्राथमिकतामा राखी संस्कारयुक्त, व्यावहारिक र समयानुकूल शिक्षा प्रदान गर्दै आइरहेको छ। आवासीय सुविधामार्फत विद्यार्थीहरूलाई पारिवारिक वातावरणमा अनुशासन र आत्मनिर्भरताको पाठ सिकाउनु हाम्रो मुख्य लक्ष्य हो।',
                'श्री रीता फुयल विगत लामो समयदेखि शिक्षा क्षेत्रमा अनवरत क्रियाशील रहँदै आउनुभएको छ। उहाँको कुशल नेतृत्वमा विद्यालयले शैक्षिक नतिजा, अतिरिक्त क्रियाकलाप र आवासीय व्यवस्थापनमा उल्लेखनीय फड्को मारेको छ।'
            )
        """)
        cursor.execute("""
            INSERT INTO school_leadership (
                role_type, name, position, qualification, experience, phone, email, message_ne, biography
            ) VALUES (
                'ASSISTANT_PRINCIPAL',
                'श्री रमेश खड्का',
                'सहायक प्रधानाध्यापक',
                'एम.एस्सी. (गणित), बि.एड.',
                '१२ वर्ष अध्यापन तथा शैक्षिक समन्वय अनुभव',
                '९८४२०५५६६७',
                'vp@shahidsmriti.edu.np',
                'हामी हाम्रा विद्यार्थीहरूलाई केवल परीक्षामा उत्तीर्ण हुने मात्र नभई जीवन उपयोगी सीप, उच्च नैतिकता र राष्ट्रप्रेमी नागरिक बनाउने यात्रामा समर्पित छौँ। विद्यालयको दैनिक अनुशासन, पाठ्यक्रम कार्यान्वयन तथा परीक्षा प्रणालीलाई आधुनिक प्रविधिमैत्री बनाउन हामी सदैव कटिबद्ध छौँ।',
                'श्री रमेश खड्का माध्यमिक तहको गणित अध्यापनका साथै विद्यालयको दैनिक अनुशासन, परीक्षा शाखा तथा शिक्षक–विद्यार्थी समन्वयमा सक्रिय रहनुभएको छ।'
            )
        """)

    # 8. Hostels & Buses
    cursor.execute("SELECT COUNT(*) FROM hostels")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO hostels (hostel_name, warden, warden_phone, capacity, gender, status)
            VALUES 
            ('सहिद स्मृति छात्र छात्रावास (Boys)', 'श्री कुल बहादुर मगर', '९८४२११२२३३', 120, 'छात्र', 'सक्रिय'),
            ('सहिद स्मृति छात्रा छात्रावास (Girls)', 'श्री सुनिता श्रेष्ठ', '९८४२११२२४४', 120, 'छात्रा', 'सक्रिय')
        """)
        # Seed rooms
        cursor.execute("SELECT id FROM hostels")
        hostel_rows = cursor.fetchall()
        for h in hostel_rows:
            for r_num in range(101, 107):
                cursor.execute("""
                    INSERT INTO hostel_rooms (hostel_id, room_number, floor, capacity, status)
                    VALUES (?, ?, 1, 4, 'AVAILABLE')
                """, (h["id"], str(r_num)))

    cursor.execute("SELECT COUNT(*) FROM buses")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO buses (bus_number, route, driver_name, driver_phone, helper_name, helper_phone, capacity)
            VALUES 
            ('को १ ख २०६६', 'इटहरी चोक - तरहरा - धरान रोड', 'श्री कृष्ण बस्नेत', '९८१२३४५६७८', 'श्री दीपक राई', '९८१२३४५६७९', 35),
            ('को १ ख २०८०', 'भवानीपुर - खनार - दुहबी रोड', 'श्री प्रेम चौधरी', '९८१२३४५६८०', 'श्री सन्तोष लिम्बु', '९८१२३४५६८१', 35)
        """)

    # 9. Teachers
    cursor.execute("SELECT COUNT(*) FROM teachers")
    if cursor.fetchone()[0] == 0:
        teachers_data = [
            ("EMP-001", "रमेश खड्का", "Ramesh Khadka", "मावि शिक्षक / सहायक प्र.अ.", "गणित", "माध्यमिक", "M.Sc. Mathematics", "१२ वर्ष", "९८४२०५५६६७", "vp@shahidsmriti.edu.np", "2070-01-15"),
            ("EMP-002", "दिनेश पौडेल", "Dinesh Poudel", "मावि शिक्षक", "विज्ञान", "माध्यमिक", "M.Sc. Physics", "८ वर्ष", "९८४२०५५६६८", "dinesh@shahidsmriti.edu.np", "2073-04-10"),
            ("EMP-003", "कमला भण्डारी", "Kamala Bhandari", "मावि शिक्षक", "अंग्रेजी", "माध्यमिक", "M.A. English", "९ वर्ष", "९८४२०५५६६९", "kamala@shahidsmriti.edu.np", "2072-02-20"),
            ("EMP-004", "विशाल दाहाल", "Bishal Dahal", "निमावि शिक्षक", "नेपाली", "निम्न माध्यमिक", "B.Ed. Nepali", "६ वर्ष", "९८४२०५५६७०", "bishal@shahidsmriti.edu.np", "2075-01-05"),
            ("EMP-005", "अन्जु लिम्बु", "Anju Limbu", "मावि शिक्षक", "कम्प्युटर", "माध्यमिक", "B.Sc. CSIT", "५ वर्ष", "९८४२०५५६७१", "anju@shahidsmriti.edu.np", "2076-03-15"),
            ("EMP-006", "प्रकाश थापा", "Prakash Thapa", "प्रावि शिक्षक", "सामाजिक", "प्राथमिक", "B.Ed.", "७ वर्ष", "९८४२०५५६७२", "prakash@shahidsmriti.edu.np", "2074-05-12")
        ]
        for t in teachers_data:
            cursor.execute("""
                INSERT INTO teachers (
                    employee_id, name_nepali, name_english, position, subject, level,
                    qualification, experience, phone, email, appointment_date, academic_year_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*t, active_year_id))

    # 10. Staff
    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        staff_data = [
            ("STF-001", "हरि नारायण चौधरी", "Hari Narayan Chaudhary", "लेखा प्रमुख", "प्रशासन तथा लेखा", "BBS", "९८४२६६७७८८", "account@shahidsmriti.edu.np"),
            ("STF-002", "मनिषा गुरुङ", "Manisha Gurung", "पुस्तकालय व्यवस्थापक", "पुस्तकालय", "B.Lis.", "९८४२६६७७८९", "library@shahidsmriti.edu.np"),
            ("STF-003", "राम किशोर यादव", "Ram Kishor Yadav", "प्रयोगशाला सहायक", "विज्ञान शाखा", "I.Sc.", "९८४२६६७७९०", "lab@shahidsmriti.edu.np"),
            ("STF-004", "शान्ति भुजेल", "Shanti Bhujel", "कार्यालय सहयोगी", "प्रशासन", "SEE", "९८४२६६७७९१", "")
        ]
        for s in staff_data:
            cursor.execute("""
                INSERT INTO staff (
                    employee_id, name_nepali, name_english, position, department,
                    qualification, phone, email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, s)

    # 11. Users (Admin, Principal, Teacher, Warden)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("admin", "admin@shahidsmriti.edu.np", hash_password("admin123"), "प्रशासक (Super Admin)", "Super Administrator", "९८४१५५२८५७", "SUPER_ADMIN", None),
            ("principal", "principal@shahidsmriti.edu.np", hash_password("principal123"), "श्री रीता फुयल", "Rita Phuyal", "९८५२०२२३३४", "PRINCIPAL", None),
            ("teacher", "teacher@shahidsmriti.edu.np", hash_password("teacher123"), "श्री रमेश खड्का", "Ramesh Khadka", "९८४२०५५६६७", "TEACHER", 1),
            ("warden", "warden@shahidsmriti.edu.np", hash_password("warden123"), "श्री कुल बहादुर मगर", "Kul Bahadur Magar", "९८४२११२२३३", "HOSTEL_WARDEN", None)
        ]
        for u in users:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name_ne, full_name_en, phone, role, teacher_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, u)

    # 12. Teacher Class Assignment (Assign Teacher 1 to Class 8-A and Class 10-A)
    cursor.execute("SELECT COUNT(*) FROM teacher_class_assignments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM classes WHERE class_numeric = 8")
        c8_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM sections WHERE class_id = ? AND name = 'A'", (c8_id,))
        s8_id = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO teacher_class_assignments (teacher_id, academic_year_id, class_id, section_id, is_class_teacher)
            VALUES (1, ?, ?, ?, 1)
        """, (active_year_id, c8_id, s8_id))

    # 13. Sample Students across classes (including residential and day scholars)
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id, class_numeric FROM classes")
        class_map = {row["class_numeric"]: row["id"] for row in cursor.fetchall()}
        
        sample_students = [
            ("STU-83001", "ADM-83-001", "रोहित कार्की", "Rohit Karki", "छात्र", "2068-04-12", 8, 1, "इटहरी-१९, सुनसरी", "राम बहादुर कार्की", "९८४२०००००१", "दिवा", None, None),
            ("STU-83002", "ADM-83-002", "अनिता चौधरी", "Anita Chaudhary", "छात्रा", "2068-06-25", 8, 2, "इटहरी-१९, सुनसरी", "सुरेश चौधरी", "९८४२००००१०", "आवासीय", 2, "201"),
            ("STU-83003", "ADM-83-003", "सौरभ थापा", "Saurav Thapa", "छात्र", "2068-08-15", 8, 3, "धरान-१५, सुनसरी", "सूर्य बहादुर थापा", "९८४२०००००४", "आवासीय", 1, "101"),
            ("STU-83004", "ADM-83-004", "सुस्मिता दाहाल", "Susmita Dahal", "छात्रा", "2068-02-18", 8, 4, "इटहरी-१९, सुनसरी", "हरि दाहाल", "९८४२००००११", "दिवा", None, None),
            ("STU-83005", "ADM-83-005", "प्रदिप लिम्बु", "Pradip Limbu", "छात्र", "2068-11-04", 8, 5, "इटहरी-६, सुनसरी", "धन बहादुर लिम्बु", "९८४२००००१२", "दिवा", None, None),
            ("STU-83006", "ADM-83-006", "पुजा श्रेष्ठ", "Puja Shrestha", "छात्रा", "2067-03-10", 10, 1, "इटहरी-१९, सुनसरी", "गणेश श्रेष्ठ", "९८४२००००१३", "आवासीय", 2, "202"),
            ("STU-83007", "ADM-83-007", "अमृत खनाल", "Amrit Khanal", "छात्र", "2067-07-22", 10, 2, "खनार, सुनसरी", "माधव खनाल", "९८४२००००१४", "दिवा", None, None),
            ("STU-83008", "ADM-83-008", "भावना राई", "Bhawana Rai", "छात्रा", "2066-05-14", 12, 1, "धरान, सुनसरी", "प्रेम कुमार राई", "९८४२००००१५", "आवासीय", 2, "203"),
            ("STU-83009", "ADM-83-009", "किरण अधिकारी", "Kiran Adhikari", "छात्र", "2066-09-08", 12, 2, "इटहरी-१९, सुनसरी", "केशव अधिकारी", "९८४२००००१६", "दिवा", None, None),
            ("STU-83010", "ADM-83-010", "मनिष पौडेल", "Manish Poudel", "छात्र", "2075-01-11", 1, 1, "भवानीपुर, इटहरी", "गोविन्द पौडेल", "९८४२००००१७", "दिवा", None, None)
        ]
        
        for s in sample_students:
            cid = class_map.get(s[6])
            cursor.execute("SELECT id FROM sections WHERE class_id = ? LIMIT 1", (cid,))
            sec_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO students (
                    student_id, admission_no, name_nepali, name_english, gender,
                    date_of_birth, class_id, section_id, roll_no, address,
                    guardian_name, guardian_relation, guardian_phone,
                    residential_status, hostel_id, room_id, academic_year_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'अभिभावक', ?, ?, ?, ?, ?)
            """, (s[0], s[1], s[2], s[3], s[4], s[5], cid, sec_id, s[7], s[8], s[9], s[10], s[11], s[12], s[13], active_year_id))
            
            # Record in class history
            stu_id_db = cursor.lastrowid
            cursor.execute("""
                INSERT INTO student_class_history (student_id, academic_year_id, class_id, section_id, roll_no, promotion_status)
                VALUES (?, ?, ?, ?, ?, 'INITIAL')
            """, (stu_id_db, active_year_id, cid, sec_id, s[7]))

    # 14. Facilities
    cursor.execute("SELECT COUNT(*) FROM facilities")
    if cursor.fetchone()[0] == 0:
        facilities_data = [
            ("आधुनिक कक्षाकोठा (Smart Classrooms)", "सुविधायुक्त, हावादार तथा प्रोजेक्टर र मल्टिमिडिया प्रविधियुक्त कक्षाकोठाहरू।", 1),
            ("पुस्तकालय (Library)", "हजारौँ पाठ्यपुस्तक, सन्दर्भ सामग्री, पत्रपत्रिका तथा ई–लाइब्रेरी सुविधा।", 2),
            ("विज्ञान प्रयोगशाला (Science Labs)", "भौतिक, रसायन र जीवविज्ञानका आधुनिक उपकरण तथा प्रयोगात्मक सामग्रीयुक्त छुट्टाछुट्टै प्रयोगशाला।", 3),
            ("कम्प्युटर ल्याब (Computer Lab)", "उच्च गतिको इन्टरनेट, आधुनिक कम्प्युटर र कोडिङ तथा प्राविधिक शिक्षाका लागि व्यवस्थित ल्याब।", 4),
            ("छात्रावास (Hostel Facilities)", "छात्र र छात्राका लागि छुट्टाछुट्टै सुरक्षित, पारिवारिक र अध्ययनमैत्री आवासीय छात्रावास।", 5),
            ("खेलमैदान तथा खेलकुद (Sports Ground)", "फुटबल, भलिबल, बास्केटबल, टेबल टेनिस तथा विभिन्न शारीरिक विकासका खेलकुद मैदान।", 6),
            ("स्वच्छ भोजनालय (Hygienic Cafeteria)", "आवासीय तथा दिवा विद्यार्थीहरूका लागि शुद्ध, पोषिलो र ताजा खाना तथा खाजाको व्यवस्था।", 7),
            ("स्वास्थ्य तथा प्राथमिक उपचार (Health Clinic)", "विद्यार्थीहरूको आकस्मिक स्वास्थ्य उपचारका लागि प्राथमिक उपचार कक्ष तथा नियमित स्वास्थ्य परीक्षण।", 8),
            ("यातायात सुविधा (School Buses)", "इटहरी, तरहरा, खनार, दुहबी लगायतका क्षेत्रमा सुरक्षित बस सेवा।", 9),
            ("ICT तथा प्रविधिमैत्री वातावरण", "सञ्चार तथा सूचना प्रविधिको उच्च प्रयोग, सीसीटीभी निगरानी र आधुनिक शैक्षिक पद्धति।", 10)
        ]
        for f in facilities_data:
            cursor.execute("INSERT INTO facilities (title, description, display_order) VALUES (?, ?, ?)", f)

    # 15. Notices
    cursor.execute("SELECT COUNT(*) FROM notices")
    if cursor.fetchone()[0] == 0:
        notices_data = [
            ("शैक्षिक सत्र २०८३ का लागि नयाँ भर्ना आवेदन खुला सम्बन्धी अत्यन्त जरुरी सूचना", "New Admission Open for Academic Session 2083", "यस सहिद स्मृति आवासीय माध्यमिक विद्यालय इटहरी–१९, सुनसरीमा नयाँ शैक्षिक सत्र २०८३ का लागि कक्षा १ देखि १२ (विज्ञान, कम्प्युटर विज्ञान, व्यवस्थापन) सम्म नयाँ भर्ना आवेदन फाराम खुला गरिएको छ। इच्छुक विद्यार्थी तथा अभिभावकहरूले विद्यालय प्रशासन वा अनलाइन वेबसाइटमार्फत समयमै आवेदन फाराम भर्नुहुन अनुरोध गरिन्छ।", "New admission is now open from Class 1 to 12 for the academic session 2083. Apply online or visit school administration.", "भर्ना", "२०८३/०१/०५", 1),
            ("प्रथम त्रैमासिक परीक्षा तालिका प्रकाशन सम्बन्धी सूचना", "First Terminal Examination Schedule Notice", "कक्षा १ देखि १० सम्मको प्रथम त्रैमासिक परीक्षा आगामी महिनाको १० गतेदेखि सञ्चालन हुने भएकाले सम्पूर्ण विद्यार्थीहरूलाई परीक्षा तयारी गर्न तथा अभिभावकहरूलाई आवश्यक सहजीकरण गरिदिनुहुन सूचित गरिन्छ।", "The first terminal examination will commence from 10th of next month.", "परीक्षा", "२०८३/०२/०१", 1),
            ("छात्रावासमा बस्ने विद्यार्थीहरूका लागि आवश्यक आचारसंहिता तथा निर्देशन", "Hostel Rules and Guidelines Notice", "छात्रावासमा नवप्रवेशी तथा नियमित अध्ययनरत छात्र/छात्रा विद्यार्थीहरूले छात्रावास नियमावलीको पूर्ण पालना गर्नुपर्नेछ। अध्ययन समय, भोजन समय तथा भ्रमण तालिका सम्बन्धी विस्तृत जानकारी छात्रावास वार्डेन शाखाबाट लिन सकिनेछ।", "Hostel guidelines and daily routines for residential students.", "छात्रावास", "२०८३/०१/१२", 0)
        ]
        for n in notices_data:
            cursor.execute("""
                INSERT INTO notices (title_ne, title_en, description_ne, description_en, category, publish_date, featured)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, n)

    # 16. News
    cursor.execute("SELECT COUNT(*) FROM news")
    if cursor.fetchone()[0] == 0:
        news_data = [
            ("वार्षिक खेलकुद सप्ताह भव्यताका साथ सम्पन्न", "Annual Sports Week Celebrated with Great Enthusiasm", "सहिद स्मृति आवासीय माध्यमिक विद्यालयको प्राङ्गणमा आयोजित साताव्यापी अन्तर–सदन खेलकुद प्रतियोगिता भव्य रूपमा सम्पन्न भएको छ। प्रतियोगितामा फुटबल, भलिबल, १०० मिटर दौड, बुद्धिचाल लगायतका खेलहरूमा विद्यार्थीहरूले उत्कृष्ट प्रदर्शन गरेका थिए।", "The annual inter-house sports week concluded successfully with active participation of all students.", "खेलकुद", "२०८२/११/२५", 1),
            ("विज्ञान तथा सूचना प्रविधि प्रदर्शनी २०८२ सम्पन्न", "Science and ICT Exhibition 2082 Successfully Organized", "विद्यालयका कक्षा ८ देखि १२ सम्मका विद्यार्थीहरूले निर्माण गरेका रोबोटिक्स, जलविद्युत मोडेल, स्मार्ट सिटी तथा सौर्य ऊर्जा सम्बन्धी ५० भन्दा बढी परियोजनाहरूको भव्य प्रदर्शनी सम्पन्न भएको छ। प्रदर्शनीमा अभिभावक तथा विभिन्न विद्यालयका विद्यार्थीहरूले अवलोकन गरेका थिए।", "Students showcased robotics and scientific projects in the science exhibition.", "शैक्षिक", "२०८२/१०/१५", 1),
            ("सहिद दिवसको अवसरमा विशेष अन्तरक्रिया तथा प्रभातफेरी कार्यक्रम", "Martyrs Day Special Observance and Morning Rally", "माघ १६ गते सहिद दिवसको पावन अवसरमा विद्यालय परिवारद्वारा प्रभातफेरी तथा सहिदहरूको योगदान र त्याग विषयक वक्तृत्वकला प्रतियोगिता सम्पन्न गरिएको छ।", "Martyrs Day observed with rally and oratory competition honoring national heroes.", "कार्यक्रम", "२०८२/१०/१६", 0)
        ]
        for nw in news_data:
            cursor.execute("""
                INSERT INTO news (title_ne, title_en, content_ne, content_en, category, publish_date, featured)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, nw)

    # 17. Achievements
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        achievements_data = [
            ("SEE परीक्षा २०८२ मा शतप्रतिशत नतिजा", "शैक्षिक", "२०८२", "माध्यमिक शिक्षा परीक्षा (SEE) मा विद्यालयका सम्पूर्ण विद्यार्थीहरू उत्कृष्ट ग्रेडसहित शतप्रतिशत उत्तीर्ण हुन सफल भएका छन्।", 1),
            ("कोशी प्रदेशस्तरीय विज्ञान प्रदर्शनीमा प्रथम स्थान", "अतिरिक्त क्रियाकलाप", "२०८२", "कोशी प्रदेशका माध्यमिक विद्यालयहरूबीच आयोजित विज्ञान प्रदर्शनीमा विद्यालयको रोबोटिक्स टिमले प्रथम स्थान हासिल गर्यो।", 2),
            ("इटहरी नगरस्तरीय अन्तर–विद्यालय फुटबल च्याम्पियन", "खेलकुद", "२०८१", "इटहरी उपमहानगरपालिकास्तरीय राष्ट्रपति रनिङ शिल्ड फुटबल प्रतियोगितामा विद्यालय छात्र टोली च्याम्पियन बन्न सफल।", 3)
        ]
        for a in achievements_data:
            cursor.execute("INSERT INTO achievements (title, category, year, description, display_order) VALUES (?, ?, ?, ?, ?)", a)

    # 18. Publications
    cursor.execute("SELECT COUNT(*) FROM publications")
    if cursor.fetchone()[0] == 0:
        pubs_data = [
            ("विद्यालय नागरिक वडापत्र २०८३", "Citizen Charter of Shahid Smriti Residential Secondary School", "/static/docs/citizen_charter.pdf", "नागरिक वडापत्र", "२०८३"),
            ("विद्यालय परिचय तथा सम्भावना पुस्तिका (Prospectus 2083)", "School Prospectus and Academic Overview 2083", "/static/docs/prospectus_2083.pdf", "Prospectus", "२०८३"),
            ("वार्षिक शैक्षिक क्यालेन्डर तथा परीक्षा तालिका २०८३", "Annual Academic Calendar 2083", "/static/docs/calendar_2083.pdf", "वार्षिक प्रतिवेदन", "२०८३"),
            ("छात्रावास सञ्चालन निर्देशिका तथा आचारसंहिता", "Hostel Code of Conduct and Operating Manual", "/static/docs/hostel_rules.pdf", "नियमावली", "२०८२")
        ]
        for p in pubs_data:
            cursor.execute("""
                INSERT INTO publications (title, description, file_url, category, publish_date)
                VALUES (?, ?, ?, ?, ?)
            """, p)

    # 19. Photo Albums & Photos
    cursor.execute("SELECT COUNT(*) FROM photo_albums")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO photo_albums (title_ne, title_en, category)
            VALUES 
            ('वार्षिक खेलकुद सप्ताह २०८२', 'Annual Sports Week 2082', 'खेलकुद'),
            ('विज्ञान तथा प्रविधि प्रदर्शनी', 'Science and ICT Exhibition', 'शैक्षिक कार्यक्रम'),
            ('छात्रावास जीवन र सांस्कृतिक कार्यक्रम', 'Hostel Life and Cultural Events', 'छात्रावास')
        """)
        
    # 20. Videos
    cursor.execute("SELECT COUNT(*) FROM videos")
    if cursor.fetchone()[0] == 0:
        videos_data = [
            ("सहिद स्मृति आवासीय मावि वृत्तचित्र तथा विद्यालय परिचय", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ", "विद्यालयको स्थापना, उद्देश्य, भौतिक पूर्वाधार तथा शैक्षिक गतिविधिसम्बन्धी वृत्तचित्र।", "विद्यालय परिचय", "२०८२/१२/०१"),
            ("वार्षिक सांस्कृतिक कार्यक्रम २०८२ का आकर्षक प्रस्तुतिहरू", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ", "विद्यार्थीहरूद्वारा प्रस्तुत नेपाली मौलिक नृत्य तथा नाटक।", "सांस्कृतिक", "२०८२/११/२०")
        ]
        for v in videos_data:
            cursor.execute("""
                INSERT INTO videos (title, youtube_url, youtube_id, description, category, publish_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, v)

    conn.commit()
    conn.close()
    print("Seed data successfully inserted!")

if __name__ == "__main__":
    seed_all()
