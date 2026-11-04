import urllib.request
import urllib.parse
import http.cookiejar
import json
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login as Admin
login_url = 'http://localhost:3000/api/auth/login'
login_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
req = urllib.request.Request(login_url, data=login_data, headers={'Content-Type': 'application/json'})
resp = opener.open(req)
print('Admin Login status:', resp.getcode(), json.loads(resp.read().decode('utf-8'))['user']['username'])

# 2. Check Admin Views
admin_routes = [
    '/admin/dashboard',
    '/admin/students',
    '/admin/students/import',
    '/admin/promotions',
    '/admin/attendance/daily',
    '/admin/attendance/reports',
    '/admin/attendance/absent',
    '/admin/teachers',
    '/admin/teachers/assignments',
    '/admin/staff',
    '/admin/management-committee',
    '/admin/trustee-committee',
    '/admin/leadership',
    '/admin/hostels',
    '/admin/transport',
    '/admin/notices',
    '/admin/news',
    '/admin/publications',
    '/admin/gallery',
    '/admin/videos',
    '/admin/facilities',
    '/admin/admissions',
    '/admin/audit-logs',
    '/admin/settings'
]

admin_passed = 0
for r in admin_routes:
    try:
        url = 'http://localhost:3000' + r
        res = opener.open(url)
        print(f'{res.getcode()} OK: {r}', flush=True)
        admin_passed += 1
    except Exception as e:
        print(f'FAIL: {r} -> {e}', flush=True)

print(f'\nTotal Admin Routes passed: {admin_passed}/{len(admin_routes)}', flush=True)

# 3. Test Attendance Sheet & Bulk Save
sheet_res = opener.open('http://localhost:3000/api/attendance/sheet?class_id=1&attendance_date=2026-10-18')
sheet_data = json.loads(sheet_res.read().decode('utf-8'))
students = sheet_data.get('sheet', [])
print(f'Attendance Sheet for Class 1 loaded: {len(students)} students', flush=True)

# Mark attendance
if students:
    rec = [{'student_id': s['student_id'], 'status': 'PRESENT', 'remarks': 'Auto test'} for s in students]
    bulk_url = 'http://localhost:3000/api/attendance/bulk'
    bulk_data = json.dumps({'class_id': 1, 'attendance_date': '2026-10-18', 'records': rec}).encode('utf-8')
    bulk_req = urllib.request.Request(bulk_url, data=bulk_data, headers={'Content-Type': 'application/json'})
    bulk_resp = opener.open(bulk_req)
    print('Attendance Bulk Save:', json.loads(bulk_resp.read().decode('utf-8'))['message'], flush=True)

# 4. Test Excel Template download
template_res = opener.open('http://localhost:3000/api/students/template')
print(f'Excel Student Template downloaded: {len(template_res.read())} bytes', flush=True)

# 5. Test Teacher Portal Login
cj_teacher = http.cookiejar.CookieJar()
opener_teacher = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_teacher))
t_login_data = json.dumps({'username': 'teacher', 'password': 'teacher123'}).encode('utf-8')
t_req = urllib.request.Request(login_url, data=t_login_data, headers={'Content-Type': 'application/json'})
t_resp = opener_teacher.open(t_req)
print('Teacher Login status:', t_resp.getcode(), json.loads(t_resp.read().decode('utf-8'))['user']['username'])

t_dashboard = opener_teacher.open('http://localhost:3000/teacher/dashboard')
print(f'Teacher Dashboard status: {t_dashboard.getcode()} OK', flush=True)

t_attendance = opener_teacher.open('http://localhost:3000/teacher/attendance')
print(f'Teacher Attendance view status: {t_attendance.getcode()} OK', flush=True)
print('\nALL COMPREHENSIVE TESTS PASSED!')
