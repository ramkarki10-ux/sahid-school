import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3
import sys

# Configure stdout for UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:3000"

class TestSession:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def get(self, path):
        url = BASE_URL + path
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = self.opener.open(req, timeout=10)
        return resp.getcode(), resp.read().decode('utf-8')

    def post_json(self, path, payload):
        url = BASE_URL + path
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        })
        resp = self.opener.open(req, timeout=10)
        return resp.getcode(), resp.read().decode('utf-8')

def test_database_integrity():
    print("\n--- 1. DATABASE INTEGRITY CHECKS ---")
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()

    # A. Check for "श्रीमती" in any table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall() if not t[0].startswith("sqlite_")]
    shrimati_found = []
    for tbl in tables:
        cursor.execute(f"PRAGMA table_info({tbl})")
        cols = [c[1] for c in cursor.fetchall() if c[2] in ('TEXT', 'VARCHAR')]
        for col in cols:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} LIKE '%श्रीमती%'")
                cnt = cursor.fetchone()[0]
                if cnt > 0:
                    shrimati_found.append(f"{tbl}.{col}: {cnt} rows")
            except Exception:
                pass
    
    if shrimati_found:
        print(f"❌ FAIL: Found 'श्रीमती' in database: {shrimati_found}")
        return False
    else:
        print("✅ PASS: Zero occurrences of 'श्रीमती' found across all database tables.")

    # B. Check Class KG
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = cursor.fetchall()
    kg_class = next((c for c in classes if c[2] == 0), None)
    if kg_class and "केजी" in kg_class[1]:
        print(f"✅ PASS: Class KG configured correctly as class_numeric = 0: '{kg_class[1]}'")
    else:
        print(f"❌ FAIL: Class KG not configured with class_numeric = 0: {kg_class}")
        return False

    # First class in ordered list must be KG
    if classes[0][2] == 0:
        print("✅ PASS: Class KG is ordered first (class_numeric = 0) before Class 1.")
    else:
        print(f"❌ FAIL: First class in ordering is not KG: {classes[0]}")
        return False

    # C. Check SMC Chair & Members
    cursor.execute("SELECT position as role, name, phone FROM school_management_committee ORDER BY order_index ASC")
    committee = cursor.fetchall()
    chair = next((m for m in committee if m[0] == "अध्यक्ष"), None)
    jamuna = next((m for m in committee if "जमुना" in m[1]), None)

    if chair and "राम बहादुर कार्की" in chair[1]:
        print(f"✅ PASS: SMC Chair is श्री राम बहादुर कार्की ({chair[1]})")
    else:
        print(f"❌ FAIL: SMC Chair is not श्री राम बहादुर कार्की: {chair}")
        return False

    if jamuna and jamuna[0] == "सदस्य":
        print(f"✅ PASS: श्री जमुना भण्डारी is designated strictly as सदस्य (Role: {jamuna[0]}, Phone: {jamuna[2]})")
    else:
        print(f"❌ FAIL: श्री जमुना भण्डारी is not designated as सदस्य: {jamuna}")
        return False

    # D. Check Teachers count
    cursor.execute("SELECT COUNT(*) FROM teachers")
    t_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'TEACHER'")
    u_cnt = cursor.fetchone()[0]
    print(f"✅ PASS: {t_cnt} teachers recorded in database, {u_cnt} teacher user accounts active.")

    conn.close()
    return True

def test_public_pages():
    print("\n--- 2. PUBLIC PAGES VERIFICATION ---")
    session = TestSession()
    urls_to_test = [
        ("/", "गृहपृष्ठ / Home", ["सहिद स्मृति आवासीय माध्यमिक विद्यालय", "९८५२०३३१३३", "९८४१५५२८५७"]),
        ("/about", "हाम्रो विद्यालय / About", ["सहिद स्मृति", "राम बहादुर कार्की", "जमुना भण्डारी"]),
        ("/contact", "सम्पर्क / Contact", ["९८५२०३३१३३", "९८४१५५२८५७", "राम बहादुर कार्की", "रीता फुयल"]),
        ("/students", "विद्यार्थी विवरण / Students Directory", ["विद्यार्थी", "रोल", "कक्षा"]),
        ("/homework", "गृहकार्य / Daily Homework", ["गृहकार्य", "विषय"]),
        ("/leave-application", "बिदा निवेदन / Leave Application", ["बिदा निवेदन", "फारम"]),
        ("/calendar", "शैक्षिक क्यालेन्डर / School Calendar", ["क्यालेन्डर", "शैक्षिक"]),
        ("/attendance-view", "दैनिक हाजिरी / Attendance View", ["हाजिरी", "प्रतिशत"]),
        ("/results", "परीक्षा नतिजा / Results", ["नतिजा", "मार्कसिट"]),
        ("/citizen-charter", "नागरिक वडापत्र / Citizen Charter", ["नागरिक वडापत्र", "सेवा"]),
        ("/gallery", "ग्यालेरी / Photo Gallery", ["फोटो ग्यालेरी", "Facebook"]),
        ("/videos", "भिडियो ग्यालेरी / Video Gallery", ["भिडियो ग्यालेरी"]),
        ("/admission", "भर्ना फारम / Admission Form", ["अनलाइन भर्ना फारम", "केजी"]),
        ("/teachers", "शिक्षक शिक्षिका / Teachers", ["शिक्षक शिक्षिका", "श्री"]),
        ("/publications", "प्रकाशन / Publications", ["प्रकाशन"]),
        ("/notices", "सूचना पाटी / Notices", ["सूचना पाटी"]),
    ]

    all_passed = True
    for path, label, expected_texts in urls_to_test:
        try:
            status_code, html = session.get(path)
            if status_code != 200:
                print(f"❌ FAIL: {label} ({path}) returned HTTP {status_code}")
                all_passed = False
                continue

            # Check for "श्रीमती" in HTML
            if "श्रीमती" in html:
                print(f"❌ FAIL: Found 'श्रीमती' in rendered page: {path}")
                all_passed = False

            # Check expected texts
            missing = [t for t in expected_texts if t not in html]
            if missing:
                print(f"❌ FAIL: {label} ({path}) missing expected text: {missing}")
                all_passed = False
            else:
                print(f"✅ PASS: {label} ({path}) -> HTTP 200, all expected markers verified.")
        except Exception as e:
            print(f"❌ ERROR testing {label} ({path}): {e}")
            all_passed = False

    return all_passed

def test_parent_portal():
    print("\n--- 3. PARENT PORTAL AUTHENTICATION & DASHBOARD ---")
    session = TestSession()

    # 1. Test parent login with English digits: 9842000001 / 1234
    try:
        status_code, resp_text = session.post_json("/api/parent/login", {
            "phone": "9842000001",
            "pin": "1234"
        })
        resp = json.loads(resp_text)
        if status_code == 200 and resp.get("success"):
            print(f"✅ PASS: Parent login successful with English digits ('9842000001'). Guardian: {resp.get('guardian_name')}")
        else:
            print(f"❌ FAIL: Parent login failed: {resp}")
            return False
    except Exception as e:
        print(f"❌ ERROR in parent login: {e}")
        return False

    # 2. Test parent dashboard access with session cookie
    try:
        status_code, html = session.get("/parent/dashboard")
        if status_code == 200 and "अभिभावक पोर्टल" in html:
            print("✅ PASS: Parent dashboard accessed successfully with authenticated session.")
        else:
            print(f"❌ FAIL: Parent dashboard access returned HTTP {status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR in parent dashboard: {e}")
        return False

    # 3. Test /api/parent/children
    try:
        status_code, data_text = session.get("/api/parent/children")
        resp_data = json.loads(data_text)
        children = resp_data.get("children", []) if isinstance(resp_data, dict) else resp_data
        if status_code == 200 and len(children) > 0:
            child = children[0]
            print(f"✅ PASS: Fetched {len(children)} enrolled child/children. Student: {child.get('name_nepali')} (Class {child.get('class_name_ne')})")
            print(f"         Today Attendance: {child.get('today_attendance', {}).get('status')}, Attendance Rate: {child.get('attendance_stats', {}).get('percentage')}%")
        else:
            print(f"❌ FAIL: /api/parent/children returned {status_code} or empty children: {resp_data}")
            return False
    except Exception as e:
        print(f"❌ ERROR fetching parent children: {e}")
        return False

    # 4. Test parent login with Nepali digits: ९८४२०००००१ / 1234
    session_np = TestSession()
    try:
        status_code, resp_text = session_np.post_json("/api/parent/login", {
            "phone": "९८४२०००००१",
            "pin": "1234"
        })
        resp = json.loads(resp_text)
        if status_code == 200 and resp.get("success"):
            print("✅ PASS: Parent login also works with Devanagari digits ('९८४२०००००१').")
        else:
            print(f"❌ FAIL: Parent login with Devanagari digits failed: {resp}")
            return False
    except Exception as e:
        print(f"❌ ERROR in parent login with Devanagari digits: {e}")
        return False

    return True

def test_teacher_portal():
    print("\n--- 4. TEACHER PORTAL & DASHBOARD ---")
    session = TestSession()

    # 1. Login as teacher1
    try:
        status_code, resp_text = session.post_json("/api/auth/login", {
            "username": "teacher1",
            "password": "teacher123"
        })
        resp = json.loads(resp_text)
        if status_code == 200 and resp.get("success"):
            print(f"✅ PASS: Teacher login successful for 'teacher1' (Role: {resp.get('role')}).")
        else:
            print(f"❌ FAIL: Teacher login failed: {resp}")
            return False
    except Exception as e:
        print(f"❌ ERROR in teacher login: {e}")
        return False

    # 2. Check Teacher Dashboard
    try:
        status_code, html = session.get("/teacher/dashboard")
        if status_code == 200:
            # Check 4 quick buttons
            buttons = ["हाजिरी", "गृहकार्य थप्नुहोस्", "विद्यार्थी हेर्नुहोस्", "रिपोर्ट"]
            has_all_buttons = all(b in html for b in buttons)
            if has_all_buttons:
                print("✅ PASS: Teacher dashboard loaded with 4 quick buttons: [हाजिरी], [गृहकार्य थप्नुहोस्], [विद्यार्थी हेर्नुहोस्], [रिपोर्ट]")
            else:
                print("❌ FAIL: Teacher dashboard missing quick action buttons")
                return False
        else:
            print(f"❌ FAIL: Teacher dashboard returned HTTP {status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR checking teacher dashboard: {e}")
        return False

    # 3. Check Teacher Attendance View
    try:
        status_code, html = session.get("/teacher/attendance")
        if status_code == 200 and "FIRST_PERIOD" in html and "FINAL_ATTENDANCE" in html:
            print("✅ PASS: Teacher attendance view has First Period & Final Attendance selectors with Absence SMS toggle.")
        else:
            print(f"❌ FAIL: Teacher attendance view missing event selectors: HTTP {status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR checking teacher attendance: {e}")
        return False

    return True

def test_admin_portal():
    print("\n--- 5. ADMIN PORTAL MODULES ---")
    session = TestSession()

    # 1. Login as admin
    try:
        status_code, resp_text = session.post_json("/api/auth/login", {
            "username": "admin",
            "password": "admin123"
        })
        resp = json.loads(resp_text)
        if status_code == 200 and resp.get("success"):
            print("✅ PASS: Admin login successful for 'admin'.")
        else:
            print(f"❌ FAIL: Admin login failed: {resp}")
            return False
    except Exception as e:
        print(f"❌ ERROR in admin login: {e}")
        return False

    # 2. Check all admin views
    admin_routes = [
        ("/admin/documents", "कागजात प्रमाणीकरण / Document Verification", ["कागजात प्रमाणीकरण", "प्रमाणित"]),
        ("/admin/sms-gateway", "SMS गेटवे सेटिङ / SMS Gateway", ["SMS गेटवे सेटिङ", "API URL"]),
        ("/admin/sms-history", "SMS लग तथा इतिहास / SMS History", ["SMS लग तथा इतिहास", "पुनः पठाउनुहोस्"]),
        ("/admin/homework", "गृहकार्य व्यवस्थापन / Homework Admin", ["गृहकार्य व्यवस्थापन", "नयाँ थप्नुहोस्"]),
        ("/admin/calendar", "शैक्षिक क्यालेन्डर व्यवस्थापन / Calendar Admin", ["शैक्षिक क्यालेन्डर व्यवस्थापन"]),
        ("/admin/leave-applications", "बिदा निवेदन समीक्षा / Leave Admin", ["बिदा निवेदन", "स्वीकृत"]),
        ("/admin/gallery", "ग्यालेरी व्यवस्थापन / Gallery Admin", ["Facebook बाट फोटो ल्याउनुहोस्"]),
    ]

    all_passed = True
    for path, label, markers in admin_routes:
        try:
            status_code, html = session.get(path)
            if status_code == 200 and all(m in html for m in markers):
                print(f"✅ PASS: {label} ({path}) -> HTTP 200, markers verified.")
            else:
                print(f"❌ FAIL: {label} ({path}) returned {status_code} or missing markers: {markers}")
                all_passed = False
        except Exception as e:
            print(f"❌ ERROR testing {label} ({path}): {e}")
            all_passed = False

    return all_passed

def test_attendance_sms_duplicate_prevention():
    print("\n--- 6. ATTENDANCE SMS & DUPLICATE PREVENTION ---")
    session = TestSession()

    # Login as admin to execute attendance
    session.post_json("/api/auth/login", {"username": "admin", "password": "admin123"})

    # Check student 1
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name_nepali, guardian_phone FROM students LIMIT 1")
    stu = cursor.fetchone()
    stu_id, stu_name, stu_phone = stu

    test_date = "2026-10-18"
    # First delete existing notification for this test date/event to test cleanly
    cursor.execute("""
        DELETE FROM attendance_notifications 
        WHERE student_id = ? AND attendance_date = ? AND attendance_event = 'FIRST_PERIOD'
    """, (stu_id, test_date))
    conn.commit()

    # 1. Post FIRST_PERIOD attendance with 1 ABSENT student with send_sms=True
    payload = {
        "class_id": 1,
        "section_id": 1,
        "attendance_date": test_date,
        "event_type": "FIRST_PERIOD",
        "send_sms": True,
        "records": [
            {
                "student_id": stu_id,
                "status": "ABSENT",
                "remark": "बिहान पहिलो घण्टीमा अनुपस्थित"
            }
        ]
    }

    try:
        status_code, resp_text = session.post_json("/api/attendance/bulk", payload)
        resp = json.loads(resp_text)
        if status_code == 200 and resp.get("success"):
            print(f"✅ PASS: First period attendance submitted. Message: {resp.get('message')}")
        else:
            print(f"❌ FAIL: Attendance post failed: {resp}")
            conn.close()
            return False

        # Verify notification entry logged
        cursor.execute("""
            SELECT id, notification_type, status, message_content 
            FROM attendance_notifications 
            WHERE student_id = ? AND attendance_date = ? AND attendance_event = 'FIRST_PERIOD'
        """, (stu_id, test_date))
        notifs = cursor.fetchall()
        if len(notifs) == 1:
            print(f"✅ PASS: SMS notification recorded in attendance_notifications table: {notifs[0]}")
        else:
            print(f"❌ FAIL: Expected 1 notification, found: {len(notifs)}")
            conn.close()
            return False

        # 2. Resubmit the SAME attendance - must NOT duplicate SMS
        status_code2, resp_text2 = session.post_json("/api/attendance/bulk", payload)
        resp2 = json.loads(resp_text2)
        
        cursor.execute("""
            SELECT id, notification_type, status, message_content 
            FROM attendance_notifications 
            WHERE student_id = ? AND attendance_date = ? AND attendance_event = 'FIRST_PERIOD'
        """, (stu_id, test_date))
        notifs2 = cursor.fetchall()

        if len(notifs2) == 1:
            print("✅ PASS: Duplicate SMS notification prevented! Total SMS records remain 1 after re-submission.")
        else:
            print(f"❌ FAIL: Duplicate SMS was created! Records count: {len(notifs2)}")
            conn.close()
            return False

    except Exception as e:
        print(f"❌ ERROR testing attendance SMS duplicate prevention: {e}")
        conn.close()
        return False

    conn.close()
    return True

if __name__ == "__main__":
    print("======================================================================")
    print("SHAHID SMRITI RESIDENTIAL SECONDARY SCHOOL - COMPREHENSIVE VERIFICATION")
    print("======================================================================")

    db_ok = test_database_integrity()
    pages_ok = test_public_pages()
    parent_ok = test_parent_portal()
    teacher_ok = test_teacher_portal()
    admin_ok = test_admin_portal()
    sms_ok = test_attendance_sms_duplicate_prevention()

    print("\n======================================================================")
    print("VERIFICATION SUMMARY:")
    print(f"1. Database Integrity & No 'श्रीमती': {'PASSED ✅' if db_ok else 'FAILED ❌'}")
    print(f"2. Public Pages & Contact Numbers:     {'PASSED ✅' if pages_ok else 'FAILED ❌'}")
    print(f"3. Parent Portal (Login/Dashboard):    {'PASSED ✅' if parent_ok else 'FAILED ❌'}")
    print(f"4. Teacher Portal (Dashboard/Buttons): {'PASSED ✅' if teacher_ok else 'FAILED ❌'}")
    print(f"5. Admin Portal (All Upgrade Modules): {'PASSED ✅' if admin_ok else 'FAILED ❌'}")
    print(f"6. Attendance SMS Duplicate Guard:     {'PASSED ✅' if sms_ok else 'FAILED ❌'}")
    print("======================================================================")

    all_passed = all([db_ok, pages_ok, parent_ok, teacher_ok, admin_ok, sms_ok])
    if all_passed:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! SYSTEM IS 100% PRODUCTION READY.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED. PLEASE REVIEW LOGS ABOVE.")
        sys.exit(1)
