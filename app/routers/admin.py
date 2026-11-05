from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user, require_role
from app.templates import templates

router = APIRouter(prefix="/admin", tags=["admin_views"])

def check_admin_auth(request: Request):
    user = get_current_user(request)
    if not user:
        return None
    if user["role"] not in ["SUPER_ADMIN", "PRINCIPAL", "VICE_PRINCIPAL", "ACCOUNTANT", "WARDEN", "CONTENT_EDITOR"]:
        return None
    return user

def get_admin_context(request: Request, active_page: str = "dashboard"):
    user = check_admin_auth(request)
    if not user:
        return None, None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    cursor.execute("SELECT * FROM academic_years WHERE is_active = 1 LIMIT 1")
    ay_row = cursor.fetchone()
    current_academic_year = dict(ay_row) if ay_row else {"year_ne": "२०८२/८३", "id": 1}
    cursor.execute("SELECT * FROM academic_years ORDER BY id DESC")
    academic_years = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return user, {
        "user": user,
        "current_user": user,
        "admin_active": active_page,
        "settings": settings,
        "active_page": active_page,
        "current_academic_year": current_academic_year,
        "academic_years": academic_years
    }

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user, ctx = get_admin_context(request, "dashboard")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय'")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय' AND residential_status = 'आवासीय'")
    residential_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM teachers WHERE status = 'सक्रिय'")
    total_teachers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM staff WHERE status = 'सक्रिय'")
    total_staff = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM classes")
    total_classes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM admission_applications WHERE status = 'नयाँ'")
    new_admissions = cursor.fetchone()[0]

    today = date.today().isoformat()
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as absent
        FROM attendance WHERE attendance_date = ?
    """, (today,))
    att_row = cursor.fetchone()
    today_present = att_row["present"] or 0
    today_absent = att_row["absent"] or 0

    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 8")
    recent_logs = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT c.class_name_ne, COUNT(s.id) as count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        GROUP BY c.id ORDER BY c.class_numeric ASC
    """)
    students_by_class = [dict(r) for r in cursor.fetchall()]

    conn.close()

    ctx.update({
        "stats": {
            "total_students": total_students,
            "residential_students": residential_students,
            "day_students": total_students - residential_students,
            "total_teachers": total_teachers,
            "total_staff": total_staff,
            "total_classes": total_classes,
            "today_present": today_present,
            "today_absent": today_absent,
            "new_admissions": new_admissions,
            "students_by_class": students_by_class
        },
        "recent_logs": recent_logs,
        "students_by_class": students_by_class
    })
    return templates.TemplateResponse(request, "admin/dashboard.html", ctx)

@router.get("/students", response_class=HTMLResponse)
def admin_students(request: Request, class_id: int = Query(None), search: str = Query(None)):
    user, ctx = get_admin_context(request, "students")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    query = """
        SELECT s.*, s.name_nepali as student_name, s.roll_no as roll_number, s.registration_no as registration_number, 
               s.guardian_phone as father_phone, c.class_name_ne 
        FROM students s 
        LEFT JOIN classes c ON s.class_id = c.id 
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if search:
        query += " AND (s.name_nepali LIKE ? OR s.name_english LIKE ? OR s.student_id LIKE ? OR s.admission_no LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
    query += " ORDER BY s.class_id ASC, s.roll_no ASC, s.id ASC LIMIT 100"
    
    cursor.execute(query, params)
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "classes": classes,
        "students": students,
        "selected_class_id": class_id,
        "search_term": search or ""
    })
    return templates.TemplateResponse(request, "admin/students.html", ctx)

@router.get("/students/import", response_class=HTMLResponse)
def admin_students_import(request: Request):
    user, ctx = get_admin_context(request, "student_import")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "admin/student_import.html", ctx)

@router.get("/students/{id}", response_class=HTMLResponse)
def admin_student_profile(id: int, request: Request):
    user, ctx = get_admin_context(request, "students")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, s.name_nepali as student_name, s.roll_no as roll_number, s.registration_no as registration_number,
               c.class_name_ne, h.name_ne as hostel_name, b.route_name as bus_route
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE s.id = ?
    """, (id,))
    student_row = cursor.fetchone()
    if not student_row:
        conn.close()
        return RedirectResponse(url="/admin/students", status_code=303)
    student = dict(student_row)

    cursor.execute("""
        SELECT h.*, fc.class_name_ne as from_class, tc.class_name_ne as to_class
        FROM student_class_history h
        LEFT JOIN classes fc ON h.from_class_id = fc.id
        LEFT JOIN classes tc ON h.to_class_id = tc.id
        WHERE h.student_id = ?
        ORDER BY h.id DESC
    """, (id,))
    history = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM attendance WHERE student_id = ? ORDER BY attendance_date DESC LIMIT 30
    """, (id,))
    attendance_records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    ctx.update({
        "student": student,
        "history": history,
        "attendance_records": attendance_records
    })
    return templates.TemplateResponse(request, "admin/student_profile.html", ctx)

@router.get("/promotions", response_class=HTMLResponse)
def admin_promotions(request: Request):
    user, ctx = get_admin_context(request, "student_promotion")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"classes": classes})
    return templates.TemplateResponse(request, "admin/student_promotion.html", ctx)

@router.get("/attendance/daily", response_class=HTMLResponse)
def admin_attendance_daily(request: Request, att_date: Optional[str] = Query(None)):
    user, ctx = get_admin_context(request, "attendance_daily")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    target_date = att_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id as class_id, c.class_name_ne, c.class_numeric,
            COUNT(DISTINCT s.id) as total_students,
            SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN a.status = 'LEAVE' THEN 1 ELSE 0 END) as leave_count,
            COUNT(a.id) as recorded_attendance_count,
            MAX(a.created_at) as submitted_at,
            COALESCE(u.full_name_ne, u.username) as teacher_name
        FROM classes c
        JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        LEFT JOIN users u ON a.recorded_by = u.id
        GROUP BY c.id
        ORDER BY c.class_numeric ASC
    """, (target_date,))
    classes_summary = [dict(r) for r in cursor.fetchall()]
    
    total_students = sum(c["total_students"] for c in classes_summary)
    total_present = sum(c["present_count"] or 0 for c in classes_summary)
    total_absent = sum(c["absent_count"] or 0 for c in classes_summary)
    total_leave = sum(c["leave_count"] or 0 for c in classes_summary)
    attendance_pct = round((total_present / total_students * 100), 1) if total_students > 0 else 0
    
    pending_classes = [c for c in classes_summary if (c["recorded_attendance_count"] or 0) == 0]
    submitted_classes = [c for c in classes_summary if (c["recorded_attendance_count"] or 0) > 0]
    
    cursor.execute("""
        SELECT attendance_date,
               SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as pres,
               SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as abs
        FROM attendance
        GROUP BY attendance_date
        ORDER BY attendance_date DESC LIMIT 7
    """)
    trend_rows = [dict(r) for r in cursor.fetchall()]
    trend_rows.reverse()
    conn.close()
    
    ctx.update({
        "classes_summary": classes_summary,
        "pending_classes": pending_classes,
        "submitted_classes": submitted_classes,
        "total_students": total_students,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_leave": total_leave,
        "attendance_pct": attendance_pct,
        "target_date": target_date,
        "today_date": date.today().isoformat(),
        "trend_rows": trend_rows
    })
    return templates.TemplateResponse(request, "admin/attendance_daily.html", ctx)

@router.get("/attendance/class-wise", response_class=HTMLResponse)
def admin_attendance_class_wise(
    request: Request,
    class_id: Optional[int] = Query(None),
    att_date: Optional[str] = Query(None)
):
    user, ctx = get_admin_context(request, "attendance_class_wise")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    target_date = att_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    
    selected_class_id = class_id or (classes[0]["id"] if classes else 1)
    
    cursor.execute("""
        SELECT s.id, s.roll_no, s.name_nepali, s.name_english, s.guardian_name, s.guardian_phone,
               a.status, a.remark, COALESCE(u.full_name_ne, u.username) as recorder_name, a.updated_at
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        LEFT JOIN users u ON a.recorded_by = u.id
        WHERE s.class_id = ? AND s.status = 'सक्रिय'
        ORDER BY s.roll_no ASC
    """, (target_date, selected_class_id))
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    pres = sum(1 for s in students if s["status"] == "PRESENT")
    absent = sum(1 for s in students if s["status"] == "ABSENT")
    leave = sum(1 for s in students if s["status"] == "LEAVE")
    total = len(students)
    pct = round((pres / total * 100), 1) if total > 0 else 0
    
    ctx.update({
        "classes": classes,
        "selected_class_id": selected_class_id,
        "target_date": target_date,
        "students": students,
        "pres": pres,
        "absent": absent,
        "leave": leave,
        "total": total,
        "pct": pct
    })
    return templates.TemplateResponse(request, "admin/attendance_class_wise.html", ctx)

@router.get("/attendance/monthly", response_class=HTMLResponse)
def admin_attendance_monthly(
    request: Request,
    year_month: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None)
):
    user, ctx = get_admin_context(request, "attendance_monthly")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    ym = year_month or date.today().strftime("%Y-%m")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    
    query = """
        SELECT s.id, s.roll_no, s.name_nepali, c.class_name_ne
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT student_id, attendance_date, status
        FROM attendance
        WHERE attendance_date LIKE ?
    """, (f"{ym}%",))
    att_records = cursor.fetchall()
    conn.close()
    
    stu_att = {}
    for r in att_records:
        sid = r["student_id"]
        dt = r["attendance_date"]
        try:
            day_num = int(dt.split("-")[-1])
        except Exception:
            day_num = 1
        if sid not in stu_att:
            stu_att[sid] = {}
        stu_att[sid][day_num] = r["status"]
        
    monthly_data = []
    for s in student_rows:
        sid = s["id"]
        day_map = stu_att.get(sid, {})
        pres = sum(1 for st in day_map.values() if st == "PRESENT")
        ab = sum(1 for st in day_map.values() if st == "ABSENT")
        lv = sum(1 for st in day_map.values() if st == "LEAVE")
        tot = pres + ab + lv
        pct = round((pres / tot * 100), 1) if tot > 0 else 0
        monthly_data.append({
            "id": sid,
            "roll_no": s["roll_no"],
            "name": s["name_nepali"],
            "class_name": s["class_name_ne"],
            "days": day_map,
            "pres": pres,
            "abs": ab,
            "leave": lv,
            "pct": pct
        })
        
    ctx.update({
        "classes": classes,
        "selected_class_id": class_id,
        "year_month": ym,
        "monthly_data": monthly_data,
        "num_days": 31
    })
    return templates.TemplateResponse(request, "admin/attendance_monthly.html", ctx)

@router.get("/attendance/quarterly", response_class=HTMLResponse)
def admin_attendance_quarterly(
    request: Request,
    quarter: int = Query(1),
    class_id: Optional[int] = Query(None)
):
    user, ctx = get_admin_context(request, "attendance_quarterly")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    
    query = """
        SELECT s.id, s.roll_no, s.name_nepali, c.class_name_ne
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT student_id,
               SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as pres,
               SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as abs,
               SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as lev
        FROM attendance
        GROUP BY student_id
    """)
    att_map = {r["student_id"]: r for r in cursor.fetchall()}
    conn.close()
    
    quarterly_data = []
    for s in student_rows:
        sid = s["id"]
        stat = att_map.get(sid, {"pres": 0, "abs": 0, "lev": 0})
        pres = stat["pres"] or 0
        ab = stat["abs"] or 0
        lv = stat["lev"] or 0
        working = pres + ab + lv
        if working == 0:
            working = 60
        pct = round((pres / working * 100), 1) if working > 0 else 0
        quarterly_data.append({
            "roll_no": s["roll_no"],
            "name": s["name_nepali"],
            "class_name": s["class_name_ne"],
            "working_days": working,
            "pres": pres,
            "abs": ab,
            "leave": lv,
            "pct": pct
        })
        
    ctx.update({
        "classes": classes,
        "selected_class_id": class_id,
        "quarter": quarter,
        "quarterly_data": quarterly_data
    })
    return templates.TemplateResponse(request, "admin/attendance_quarterly.html", ctx)

@router.get("/attendance/annual", response_class=HTMLResponse)
def admin_attendance_annual(
    request: Request,
    class_id: Optional[int] = Query(None)
):
    user, ctx = get_admin_context(request, "attendance_annual")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    
    query = """
        SELECT s.id, s.roll_no, s.name_nepali, c.class_name_ne
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT student_id,
               SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as pres,
               SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as abs,
               SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as lev
        FROM attendance
        GROUP BY student_id
    """)
    att_map = {r["student_id"]: r for r in cursor.fetchall()}
    conn.close()
    
    annual_data = []
    for s in student_rows:
        sid = s["id"]
        stat = att_map.get(sid, {"pres": 0, "abs": 0, "lev": 0})
        pres = stat["pres"] or 0
        ab = stat["abs"] or 0
        lv = stat["lev"] or 0
        working = pres + ab + lv
        if working == 0:
            working = 220
        pct = round((pres / working * 100), 1) if working > 0 else 0
        annual_data.append({
            "roll_no": s["roll_no"],
            "name": s["name_nepali"],
            "class_name": s["class_name_ne"],
            "working_days": working,
            "pres": pres,
            "abs": ab,
            "leave": lv,
            "pct": pct
        })
        
    ctx.update({
        "classes": classes,
        "selected_class_id": class_id,
        "annual_data": annual_data
    })
    return templates.TemplateResponse(request, "admin/attendance_annual.html", ctx)

@router.get("/attendance/correction", response_class=HTMLResponse)
def admin_attendance_correction(
    request: Request,
    class_id: Optional[int] = Query(None),
    att_date: Optional[str] = Query(None)
):
    user, ctx = get_admin_context(request, "attendance_correction")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    target_date = att_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    
    selected_class_id = class_id or (classes[0]["id"] if classes else 1)
    
    cursor.execute("""
        SELECT s.id, s.roll_no, s.name_nepali, c.class_name_ne,
               a.status, a.remark, a.updated_at
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        WHERE s.class_id = ? AND s.status = 'सक्रिय'
        ORDER BY s.roll_no ASC
    """, (target_date, selected_class_id))
    students = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT l.*, s.name_nepali as student_name, s.roll_no, c.class_name_ne,
               COALESCE(u.full_name_ne, u.username, 'प्रशासक') as modifier_name
        FROM attendance_audit_logs l
        LEFT JOIN students s ON l.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON l.modified_by = u.id
        ORDER BY l.id DESC LIMIT 20
    """)
    audit_logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    ctx.update({
        "classes": classes,
        "selected_class_id": selected_class_id,
        "target_date": target_date,
        "students": students,
        "audit_logs": audit_logs
    })
    return templates.TemplateResponse(request, "admin/attendance_correction.html", ctx)

@router.get("/attendance/export", response_class=HTMLResponse)
def admin_attendance_export_hub(request: Request):
    user, ctx = get_admin_context(request, "attendance_export")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    ctx.update({
        "classes": classes,
        "today_date": date.today().isoformat(),
        "year_month": date.today().strftime("%Y-%m")
    })
    return templates.TemplateResponse(request, "admin/attendance_export.html", ctx)

@router.get("/attendance/reports", response_class=HTMLResponse)
def admin_attendance_reports(request: Request):
    user, ctx = get_admin_context(request, "attendance_reports")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"classes": classes})
    return templates.TemplateResponse(request, "admin/attendance_reports.html", ctx)

@router.get("/attendance/absent", response_class=HTMLResponse)
def admin_attendance_absent(request: Request):
    user, ctx = get_admin_context(request, "attendance_absent")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, s.name_nepali as student_name, s.father_name, s.guardian_phone as father_phone, s.emergency_contact, 
               s.residential_status, c.class_name_ne, 'A' as section
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON a.class_id = c.id
        WHERE a.attendance_date = ? AND a.status = 'ABSENT'
        ORDER BY c.class_numeric ASC, s.roll_no ASC
    """, (today,))
    absent_students = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "absent_students": absent_students,
        "today_date": today
    })
    return templates.TemplateResponse(request, "admin/attendance_absent.html", ctx)

@router.get("/teachers", response_class=HTMLResponse)
def admin_teachers(request: Request):
    user, ctx = get_admin_context(request, "teachers")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, name_nepali as name FROM teachers ORDER BY id ASC")
    teachers = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"teachers": teachers})
    return templates.TemplateResponse(request, "admin/teachers.html", ctx)

@router.get("/teachers/assignments", response_class=HTMLResponse)
def admin_teacher_assignments(request: Request):
    user, ctx = get_admin_context(request, "teacher_assignments")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, name_nepali as name FROM teachers WHERE status = 'सक्रिय' ORDER BY name_nepali ASC")
    teachers = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT a.*, t.name_nepali as teacher_name, c.class_name_ne 
        FROM teacher_class_assignments a
        JOIN teachers t ON a.teacher_id = t.id
        JOIN classes c ON a.class_id = c.id
        ORDER BY c.class_numeric ASC, a.is_class_teacher DESC
    """)
    assignments = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "teachers": teachers,
        "classes": classes,
        "assignments": assignments
    })
    return templates.TemplateResponse(request, "admin/teacher_assignments.html", ctx)

@router.get("/staff", response_class=HTMLResponse)
def admin_staff(request: Request):
    user, ctx = get_admin_context(request, "staff")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, name_nepali as name FROM staff ORDER BY id ASC")
    staff = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"staff": staff})
    return templates.TemplateResponse(request, "admin/staff.html", ctx)

@router.get("/management-committee", response_class=HTMLResponse)
def admin_management_committee(request: Request):
    user, ctx = get_admin_context(request, "management_committee")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_management_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"members": members})
    return templates.TemplateResponse(request, "admin/management_committee.html", ctx)

@router.get("/trustee-committee", response_class=HTMLResponse)
def admin_trustee_committee(request: Request):
    user, ctx = get_admin_context(request, "trustee_committee")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trustee_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"members": members})
    return templates.TemplateResponse(request, "admin/trustee_committee.html", ctx)

@router.get("/leadership", response_class=HTMLResponse)
def admin_leadership(request: Request):
    user, ctx = get_admin_context(request, "leadership")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, position as designation, message_ne as message FROM school_leadership WHERE role_type = 'PRINCIPAL'")
    p_row = cursor.fetchone()
    principal = dict(p_row) if p_row else None

    cursor.execute("SELECT *, position as designation, message_ne as message FROM school_leadership WHERE role_type = 'VICE_PRINCIPAL'")
    vp_row = cursor.fetchone()
    vp = dict(vp_row) if vp_row else None
    conn.close()

    ctx.update({"principal": principal, "vp": vp})
    return templates.TemplateResponse(request, "admin/leadership.html", ctx)

@router.get("/hostels", response_class=HTMLResponse)
def admin_hostels(request: Request):
    user, ctx = get_admin_context(request, "hostels")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hostels")
    hostels = [dict(h) for h in cursor.fetchall()]
    for h in hostels:
        cursor.execute("SELECT * FROM hostel_rooms WHERE hostel_id = ?", (h["id"],))
        h["rooms"] = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"hostels": hostels})
    return templates.TemplateResponse(request, "admin/hostels.html", ctx)

@router.get("/transport", response_class=HTMLResponse)
def admin_transport(request: Request):
    user, ctx = get_admin_context(request, "transport")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buses")
    buses = [dict(b) for b in cursor.fetchall()]
    conn.close()

    ctx.update({"buses": buses})
    return templates.TemplateResponse(request, "admin/transport.html", ctx)

@router.get("/notices", response_class=HTMLResponse)
def admin_notices(request: Request):
    user, ctx = get_admin_context(request, "notices")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"notices": notices})
    return templates.TemplateResponse(request, "admin/notices.html", ctx)

@router.get("/news", response_class=HTMLResponse)
def admin_news(request: Request):
    user, ctx = get_admin_context(request, "news")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY id DESC")
    news = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"news": news})
    return templates.TemplateResponse(request, "admin/news.html", ctx)

@router.get("/publications", response_class=HTMLResponse)
def admin_publications(request: Request):
    user, ctx = get_admin_context(request, "publications")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publications ORDER BY id DESC")
    publications = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"publications": publications})
    return templates.TemplateResponse(request, "admin/publications.html", ctx)

@router.get("/gallery", response_class=HTMLResponse)
def admin_gallery(request: Request):
    user, ctx = get_admin_context(request, "gallery")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo_albums ORDER BY id DESC")
    albums = [dict(a) for a in cursor.fetchall()]
    for alb in albums:
        cursor.execute("SELECT * FROM photos WHERE album_id = ?", (alb["id"],))
        alb["photos"] = [dict(p) for p in cursor.fetchall()]
    conn.close()

    ctx.update({"albums": albums})
    return templates.TemplateResponse(request, "admin/gallery.html", ctx)

@router.get("/videos", response_class=HTMLResponse)
def admin_videos(request: Request):
    user, ctx = get_admin_context(request, "videos")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY id DESC")
    videos = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"videos": videos})
    return templates.TemplateResponse(request, "admin/videos.html", ctx)

@router.get("/facilities", response_class=HTMLResponse)
def admin_facilities(request: Request):
    user, ctx = get_admin_context(request, "facilities")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, title as title_ne, description as description_ne, display_order as order_index FROM facilities ORDER BY display_order ASC")
    facilities = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"facilities": facilities})
    return templates.TemplateResponse(request, "admin/facilities.html", ctx)

@router.get("/admissions", response_class=HTMLResponse)
def admin_admissions(request: Request):
    user, ctx = get_admin_context(request, "admissions")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admission_applications ORDER BY id DESC")
    applications = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"applications": applications})
    return templates.TemplateResponse(request, "admin/admissions.html", ctx)

@router.get("/audit-logs", response_class=HTMLResponse)
def admin_audit_logs(request: Request):
    user, ctx = get_admin_context(request, "audit_logs")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"logs": logs})
    return templates.TemplateResponse(request, "admin/audit_logs.html", ctx)

@router.get("/settings", response_class=HTMLResponse)
def admin_settings(request: Request):
    user, ctx = get_admin_context(request, "settings")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "admin/settings.html", ctx)

@router.get("/documents", response_class=HTMLResponse)
def admin_documents(request: Request):
    user, ctx = get_admin_context(request, "documents")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, s.name_nepali as student_name, s.roll_no, c.class_name_ne, u.full_name_ne as verifier_name
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON d.verified_by = u.id
        ORDER BY d.id DESC
    """)
    documents = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"documents": documents})
    return templates.TemplateResponse(request, "admin/document_verification.html", ctx)

@router.get("/sms-gateway", response_class=HTMLResponse)
def admin_sms_gateway(request: Request):
    user, ctx = get_admin_context(request, "sms_gateway")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sms_gateway_settings WHERE id = 1")
    sms_settings = dict(cursor.fetchone() or {})
    conn.close()

    ctx.update({"sms_settings": sms_settings})
    return templates.TemplateResponse(request, "admin/sms_gateway.html", ctx)

@router.get("/sms-history", response_class=HTMLResponse)
def admin_sms_history(request: Request):
    user, ctx = get_admin_context(request, "sms_history")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, s.name_nepali as student_name, c.class_name_ne
        FROM attendance_notifications n
        LEFT JOIN students s ON n.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        ORDER BY n.id DESC LIMIT 100
    """)
    notifications = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"notifications": notifications})
    return templates.TemplateResponse(request, "admin/sms_history.html", ctx)

@router.get("/homework", response_class=HTMLResponse)
def admin_homework(request: Request):
    user, ctx = get_admin_context(request, "homework")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    # Fetch subjects with class mapping
    cursor.execute("""
        SELECT s.id, s.class_id, s.subject_name_ne, s.subject_code, c.class_name_ne, c.class_numeric
        FROM subjects s
        JOIN classes c ON s.class_id = c.id
        ORDER BY c.class_numeric ASC, s.id ASC
    """)
    subjects = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT h.*, c.class_name_ne, c.class_numeric, COALESCE(t.name_nepali, 'विषय शिक्षक') as teacher_name
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        ORDER BY h.id DESC
    """)
    homework_list = [dict(r) for r in cursor.fetchall()]

    # Parse questions JSON if present
    import json
    for hw in homework_list:
        q_raw = hw.get("questions")
        if q_raw:
            try:
                hw["question_list"] = json.loads(q_raw)
            except Exception:
                hw["question_list"] = []
        else:
            hw["question_list"] = []

    cursor.execute("SELECT id, name_nepali FROM teachers ORDER BY name_nepali ASC")
    teachers = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "classes": classes,
        "subjects": subjects,
        "homework_list": homework_list,
        "teachers": teachers
    })
    return templates.TemplateResponse(request, "admin/homework.html", ctx)

@router.get("/calendar", response_class=HTMLResponse)
def admin_calendar(request: Request):
    user, ctx = get_admin_context(request, "calendar")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC")
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"events": events})
    return templates.TemplateResponse(request, "admin/calendar.html", ctx)

@router.get("/leave-applications", response_class=HTMLResponse)
def admin_leave_applications(request: Request):
    user, ctx = get_admin_context(request, "leave_applications")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, c.class_name_ne, u.full_name_ne as reviewer_name
        FROM leave_applications l
        JOIN classes c ON l.class_id = c.id
        LEFT JOIN users u ON l.reviewed_by = u.id
        ORDER BY l.id DESC
    """)
    leaves = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"leaves": leaves})
    return templates.TemplateResponse(request, "admin/leave_applications.html", ctx)

@router.get("/registrations", response_class=HTMLResponse)
def admin_registrations(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user_type: Optional[str] = Query(None)
):
    """Super Admin page to review, approve, reject, or delete user registrations."""
    user, ctx = get_admin_context(request, "registrations")
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    # Counts
    cursor.execute("SELECT COUNT(*) FROM user_registrations WHERE status = 'विचाराधीन'")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_registrations WHERE user_type = 'STUDENT'")
    student_reg_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_registrations WHERE user_type = 'TEACHER'")
    teacher_reg_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_registrations WHERE user_type = 'PARENT'")
    parent_reg_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_registrations")
    total_reg_count = cursor.fetchone()[0]

    query = """
        SELECT r.*, u.full_name_ne as reviewer_name
        FROM user_registrations r
        LEFT JOIN users u ON r.reviewed_by = u.id
        WHERE 1=1
    """
    params = []
    if status_filter and status_filter != "all":
        query += " AND r.status = ?"
        params.append(status_filter)
    if user_type and user_type != "all":
        query += " AND r.user_type = ?"
        params.append(user_type.upper())

    query += " ORDER BY r.id DESC"
    cursor.execute(query, params)
    registrations = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "registrations": registrations,
        "pending_count": pending_count,
        "student_reg_count": student_reg_count,
        "teacher_reg_count": teacher_reg_count,
        "parent_reg_count": parent_reg_count,
        "total_reg_count": total_reg_count,
        "current_status": status_filter or "all",
        "current_type": user_type or "all"
    })
    return templates.TemplateResponse(request, "admin/registrations.html", ctx)

class TeacherAttendanceUpdateRequest(BaseModel):
    teacher_id: int
    attendance_date: str
    status: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    remark: Optional[str] = None

@router.get("/teacher-attendance", response_class=HTMLResponse)
def admin_teacher_attendance(request: Request, date_param: Optional[str] = Query(None, alias="date")):
    user, ctx = get_admin_context(request, "teacher_attendance")
    if not user or user.get("role") not in ["SUPER_ADMIN", "PRINCIPAL"]:
        return RedirectResponse(url="/login", status_code=303)
    
    target_date = date_param or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.id as teacher_id, t.employee_id, t.name_nepali, t.position, t.level, t.subject,
               COALESCE(ta.status, 'PRESENT') as status,
               ta.check_in_time, ta.check_out_time, ta.remark
        FROM teachers t
        LEFT JOIN teacher_attendance ta ON t.id = ta.teacher_id AND ta.attendance_date = ?
        ORDER BY t.id ASC
    """, (target_date,))
    records = [dict(r) for r in cursor.fetchall()]
    
    total = len(records)
    present = sum(1 for r in records if r["status"] == "PRESENT")
    absent = sum(1 for r in records if r["status"] == "ABSENT")
    leave = sum(1 for r in records if r["status"] in ["LEAVE", "LATE"])
    
    conn.close()
    
    ctx.update({
        "selected_date": target_date,
        "records": records,
        "stats": {
            "total": total,
            "present": present,
            "absent": absent,
            "leave": leave
        }
    })
    return templates.TemplateResponse(request, "admin/teacher_attendance.html", ctx)

@router.post("/teacher-attendance/update")
def admin_update_teacher_attendance(req: TeacherAttendanceUpdateRequest, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO teacher_attendance (teacher_id, attendance_date, status, check_in_time, check_out_time, remark, recorded_by, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(teacher_id, attendance_date) DO UPDATE SET
            status = excluded.status,
            check_in_time = excluded.check_in_time,
            check_out_time = excluded.check_out_time,
            remark = excluded.remark,
            recorded_by = excluded.recorded_by,
            updated_at = CURRENT_TIMESTAMP
    """, (req.teacher_id, req.attendance_date, req.status, req.check_in_time, req.check_out_time, req.remark, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True, "message": "शिक्षक हाजिरी अद्यावधिक भयो।"}

@router.get("/attendance")
def admin_attendance_redirect():
    return RedirectResponse(url="/admin/attendance/daily", status_code=303)

@router.get("/attendance-reports", response_class=HTMLResponse)
def admin_attendance_reports_alias(request: Request):
    return admin_attendance_reports(request)

@router.get("/results", response_class=HTMLResponse)
def admin_results_page(
    request: Request,
    exam_id: Optional[int] = Query(None),
    class_id: Optional[int] = Query(None)
):
    user, ctx = get_admin_context(request, "results")
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    # Get exams
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    exams = [dict(r) for r in cursor.fetchall()]

    # Default to first exam if not selected
    sel_exam_id = exam_id or (exams[0]["id"] if exams else 1)

    # Get classes
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    # Get all students for select modal
    cursor.execute("""
        SELECT s.id, s.name_nepali, s.roll_no, c.class_name_ne
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
        ORDER BY c.class_numeric ASC, s.roll_no ASC
    """)
    all_students = [dict(r) for r in cursor.fetchall()]

    # Get all subjects for select modal
    cursor.execute("""
        SELECT sub.id, sub.subject_name_ne, c.class_name_ne
        FROM subjects sub
        JOIN classes c ON sub.class_id = c.id
        ORDER BY c.class_numeric ASC, sub.id ASC
    """)
    all_subjects = [dict(r) for r in cursor.fetchall()]

    # Get results list
    query = """
        SELECT r.*, s.student_id as stu_code, s.roll_no, s.name_nepali,
               c.class_name_ne, sub.subject_name_ne
        FROM results r
        JOIN students s ON r.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        JOIN subjects sub ON r.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if sel_exam_id:
        query += " AND r.exam_id = ?"
        params.append(sel_exam_id)
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)

    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC, sub.id ASC"
    cursor.execute(query, params)
    results_list = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({
        "exams": exams,
        "selected_exam_id": sel_exam_id,
        "classes": classes,
        "selected_class_id": class_id,
        "all_students": all_students,
        "all_subjects": all_subjects,
        "results_list": results_list
    })
    return templates.TemplateResponse(request, "admin/results.html", ctx)

@router.get("/contact-messages", response_class=HTMLResponse)
def admin_contact_messages_page(request: Request):
    user, ctx = get_admin_context(request, "contact_messages")
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact_messages ORDER BY id DESC")
    messages = [dict(r) for r in cursor.fetchall()]
    conn.close()

    ctx.update({"messages": messages})
    return templates.TemplateResponse(request, "admin/contact_messages.html", ctx)



