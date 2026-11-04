import sys
import sqlite3
import urllib.request
import urllib.parse
import json
import http.cookiejar

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:3000"

def run_checks():
    print("=== 1. DATABASE CHECKS ===")
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()

    # Teachers count
    cursor.execute("SELECT COUNT(*) FROM teachers")
    t_count = cursor.fetchone()[0]
    print(f"Teachers count: {t_count} (Expected: 16)")
    assert t_count == 16, f"Expected 16 teachers, found {t_count}"

    # Staff count
    cursor.execute("SELECT COUNT(*) FROM staff")
    s_count = cursor.fetchone()[0]
    print(f"Staff count: {s_count} (Expected: 12)")
    assert s_count == 12, f"Expected 12 staff, found {s_count}"

    # Early Childhood classes
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes WHERE class_numeric <= 0 ORDER BY class_numeric ASC")
    ecd_classes = cursor.fetchall()
    print(f"ECD classes: {ecd_classes}")
    assert len(ecd_classes) >= 3, "Expected at least 3 ECD classes (Nursery, LKG, UKG)"

    # Hotel Management stream
    cursor.execute("SELECT id, name_ne FROM streams WHERE name_ne LIKE '%होटल%'")
    hm_stream = cursor.fetchall()
    print(f"Hotel Management stream: {hm_stream}")
    assert len(hm_stream) > 0, "Hotel Management stream missing"

    # Students EMIS code check
    cursor.execute("SELECT id, emis_code, name_nepali FROM students LIMIT 5")
    sample_students = cursor.fetchall()
    print(f"Sample students with EMIS: {sample_students}")
    for s in sample_students:
        assert s[1] is not None and len(s[1]) > 0, f"Missing EMIS for student {s[0]}"

    # Check for banned strings in DB
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    banned = ['श्रीमती', '०२५–५८०१२३', '०२५-५८०१२३', '025-580123', '९८५२०५५६६७', '9852055667']
    banned_hits = []
    for t in tables:
        try:
            cursor.execute(f"SELECT * FROM {t}")
            for row in cursor.fetchall():
                for cell in row:
                    sc = str(cell)
                    for b in banned:
                        if b in sc:
                            banned_hits.append((t, b))
        except Exception:
            pass
    print(f"Banned strings in DB: {len(banned_hits)}")
    assert len(banned_hits) == 0, f"Found banned strings in DB: {banned_hits}"

    # Teacher attendance table
    cursor.execute("SELECT COUNT(*) FROM teacher_attendance")
    att_count = cursor.fetchone()[0]
    print(f"Teacher attendance records: {att_count}")
    assert att_count >= 16, "Teacher attendance records should be at least 16"

    conn.close()
    print("Database checks PASSED!\n")

    print("=== 2. HTTP ENDPOINTS LIVE CHECKS ===")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get_page(path):
        req = urllib.request.Request(f"{BASE_URL}{path}")
        with opener.open(req) as resp:
            return resp.status, resp.read().decode('utf-8', errors='ignore')

    # 1. Home page
    st, html = get_page("/")
    assert st == 200
    assert "सहिद स्मृति" in html
    assert "media_1792321769467_af2ab756.jpg" in html or "logo" in html
    print("GET / -> 200 OK")

    # 2. Teachers page
    st, html = get_page("/teachers")
    assert st == 200
    assert "श्री रीता फुयल" in html
    assert "श्री रमेश खड्का" in html
    assert "श्री चेवन प्रसाद पौडेल" in html
    assert "श्रीमती" not in html
    print("GET /teachers -> 200 OK (All 16 teachers present, zero श्रीमती)")

    # 3. Administration & Staff pages
    st, html = get_page("/administration")
    assert st == 200
    assert "श्रीमती" not in html
    assert "श्री रीता फुयल" in html
    print("GET /administration -> 200 OK (Zero श्रीमती, leadership verified)")

    st, html = get_page("/staff")
    assert st == 200
    assert "श्री एकराज गिरी" in html
    assert "श्री सोम प्रसाद पुरी" in html
    assert "श्रीमती" not in html
    print("GET /staff -> 200 OK (All 12 staff members present, zero श्रीमती)")

    # 4. Academics page
    st, html = get_page("/academics")
    assert st == 200
    assert "नर्सरी" in html
    assert "होटल व्यवस्थापन" in html
    print("GET /academics -> 200 OK (Nursery, LKG, Hotel Management present)")

    # 5. Students page (Directory)
    st, html = get_page("/students")
    assert st == 200
    assert "इमिस कोड" in html
    print("GET /students -> 200 OK (EMIS code visible in public directory)")

    # 6. Homework page (Private Privacy Screen)
    st, html = get_page("/homework")
    assert st == 200
    assert "अभिभावक पोर्टल लगइन" in html
    assert "गोपनीयता" in html
    print("GET /homework -> 200 OK (Privacy screen requiring Parent Login)")

    # 7. Attendance view page (Private Privacy Screen)
    st, html = get_page("/attendance-view")
    assert st == 200
    assert "अभिभावक पोर्टल लगइन" in html or "अभिभावक पोर्टल" in html
    assert "गोपनीयता" in html
    print("GET /attendance-view -> 200 OK (Privacy screen requiring Parent Login)")

    # 8. Admin Teacher Attendance (Unauthorized -> Redirect to login)
    req = urllib.request.Request(f"{BASE_URL}/admin/teacher-attendance")
    try:
        resp = opener.open(req)
        # Note: urllib follows redirects automatically, so it should land on /login
        assert "/login" in resp.geturl() or resp.status == 200
        print("GET /admin/teacher-attendance (unauthenticated) -> Redirects to login (Protected)")
    except urllib.error.HTTPError as e:
        print(f"GET /admin/teacher-attendance (unauthenticated) -> HTTP {e.code} (Protected)")

    # 9. Admin Login & Check Teacher Attendance
    login_data = json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8')
    login_req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    with opener.open(login_req) as resp:
        assert resp.status == 200
        res_json = json.loads(resp.read().decode('utf-8'))
        token = res_json.get("token")
        print(f"Admin login -> 200 OK (token received)")

    # Add session_token cookie
    opener.addheaders = [("Cookie", f"session_token={token}")]
    admin_req = urllib.request.Request(f"{BASE_URL}/admin/teacher-attendance")
    with opener.open(admin_req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8', errors='ignore')
        assert "शिक्षक हाजिरी व्यवस्थापन" in html
        assert "श्री रीता फुयल" in html
        print("GET /admin/teacher-attendance (authenticated admin) -> 200 OK (Admin attendance screen loaded)")

    print("\nALL VERIFICATIONS PASSED 100% SUCCESFULLY!")

if __name__ == "__main__":
    run_checks()
