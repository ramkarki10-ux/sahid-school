from typing import Optional, List, Dict
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date
from app.database import get_db
from app.auth import get_current_user
from app.templates import templates
from app.utils.nepali_date import get_today_bs, ad_to_bs, bs_to_ad

router = APIRouter(prefix="/teacher", tags=["teacher_views"])

def check_teacher_auth(request: Request):
    user = get_current_user(request)
    if not user:
        return None
    if user["role"] not in ["TEACHER", "SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        return None
    return user

def get_teacher_classes(user: dict):
    conn = get_db()
    cursor = conn.cursor()
    teacher_id = user.get("teacher_id")
    is_admin_or_principal = user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]

    classes = []
    if teacher_id and not is_admin_or_principal:
        cursor.execute("""
            SELECT a.class_id, a.is_class_teacher,
                   c.class_name_ne, c.class_numeric, 'A' as section,
                   COUNT(s.id) as student_count
            FROM teacher_class_assignments a
            JOIN classes c ON a.class_id = c.id
            LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
            WHERE a.teacher_id = ?
            GROUP BY a.class_id
            ORDER BY c.class_numeric ASC, c.id ASC
        """, (teacher_id,))
        classes = [dict(r) for r in cursor.fetchall()]

    # If admin/principal or teacher has no specific assignments, load all classes
    if not classes:
        cursor.execute("""
            SELECT c.id as class_id, 'सम्पूर्ण कक्षा' as subject_name, 1 as is_class_teacher,
                   c.class_name_ne, c.class_numeric, 'A' as section,
                   COUNT(s.id) as student_count
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
            GROUP BY c.id
            ORDER BY c.class_numeric ASC, c.id ASC
        """)
        classes = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return classes

@router.get("/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request):
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    conn.close()

    assigned_classes = get_teacher_classes(user)

    return templates.TemplateResponse(request, "teacher/dashboard.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "today_date": date.today().isoformat()
    })

@router.get("/attendance", response_class=HTMLResponse)
def teacher_attendance(request: Request, class_id: int = Query(None)):
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    conn.close()

    assigned_classes = get_teacher_classes(user)
    if not class_id and assigned_classes:
        class_id = assigned_classes[0]["class_id"]

    today_ad = date.today().isoformat()
    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/attendance.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "selected_class_id": class_id,
        "today_date": today_ad,
        "today_bs": today_bs,
        "today_bs_date": today_bs["date_bs"],
        "today_bs_formatted": today_bs["formatted"],
        "today_bs_full": today_bs["formatted_full"],
    })

@router.get("/absent", response_class=HTMLResponse)
def teacher_absent(request: Request):
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    
    today = date.today().isoformat()
    assigned_classes = get_teacher_classes(user)
    class_ids = [c["class_id"] for c in assigned_classes]

    if class_ids:
        placeholders = ",".join(["?"] * len(class_ids))
        cursor.execute(f"""
            SELECT a.*, s.name_nepali as student_name, s.father_name, s.guardian_phone as father_phone, s.emergency_contact, 
                   s.residential_status, c.class_name_ne, 'A' as section
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN classes c ON a.class_id = c.id
            WHERE a.attendance_date = ? AND a.status = 'ABSENT' AND a.class_id IN ({placeholders})
            ORDER BY c.class_numeric ASC, s.roll_no ASC
        """, [today] + class_ids)
        absent_students = [dict(r) for r in cursor.fetchall()]
    else:
        absent_students = []
    
    conn.close()

    return templates.TemplateResponse(request, "admin/attendance_absent.html", {
        "user": user,
        "settings": settings,
        "absent_students": absent_students,
        "today_date": today,
        "active_page": "teacher_absent"
    })

@router.get("/daily-report", response_class=HTMLResponse)
def teacher_daily_report(request: Request, report_date: Optional[str] = Query(None)):
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    att_date = report_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    assigned_classes = get_teacher_classes(user)
    class_ids = [c["class_id"] for c in assigned_classes]

    class_reports = []
    total_stu = 0
    total_pres = 0
    total_abs = 0
    total_leave = 0

    if class_ids:
        placeholders = ",".join(["?"] * len(class_ids))
        cursor.execute(f"""
            SELECT c.id as class_id, c.class_name_ne, c.class_numeric,
                   COUNT(DISTINCT s.id) as total_students,
                   SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END) as present_count,
                   SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END) as absent_count,
                   SUM(CASE WHEN a.status = 'LEAVE' THEN 1 ELSE 0 END) as leave_count,
                   MAX(a.created_at) as submitted_at,
                   COALESCE(u.full_name_ne, u.username) as recorded_by_name
            FROM classes c
            JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
            LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
            LEFT JOIN users u ON a.recorded_by = u.id
            WHERE c.id IN ({placeholders})
            GROUP BY c.id
            ORDER BY c.class_numeric ASC
        """, [att_date] + class_ids)
        class_reports = [dict(r) for r in cursor.fetchall()]

        total_stu = sum(c["total_students"] for c in class_reports)
        total_pres = sum(c["present_count"] or 0 for c in class_reports)
        total_abs = sum(c["absent_count"] or 0 for c in class_reports)
        total_leave = sum(c["leave_count"] or 0 for c in class_reports)

    conn.close()

    pct = round((total_pres / total_stu * 100), 1) if total_stu > 0 else 0

    return templates.TemplateResponse(request, "teacher/daily_report.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "class_reports": class_reports,
        "report_date": att_date,
        "today_date": date.today().isoformat(),
        "total_students": total_stu,
        "total_present": total_pres,
        "total_absent": total_abs,
        "total_leave": total_leave,
        "percentage": pct,
        "active_page": "daily_report"
    })

@router.get("/profile", response_class=HTMLResponse)
def teacher_profile(request: Request):
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    # Fetch teacher profile details
    teacher_info = None
    teacher_id = user.get("teacher_id")
    if teacher_id:
        cursor.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,))
        teacher_info = cursor.fetchone()
    if not teacher_info:
        cursor.execute("SELECT * FROM teachers WHERE email = ? OR phone = ? LIMIT 1", (user["username"], user["username"]))
        teacher_info = cursor.fetchone()

    assigned_classes = get_teacher_classes(user)
    conn.close()

    return templates.TemplateResponse(request, "teacher/profile.html", {
        "user": user,
        "settings": settings,
        "teacher_info": dict(teacher_info) if teacher_info else {},
        "assigned_classes": assigned_classes,
        "active_page": "profile"
    })
