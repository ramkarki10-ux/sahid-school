import json
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
    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/dashboard.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "today_date": date.today().isoformat(),
        "today_bs": today_bs,
        "today_bs_date": today_bs["date_bs"],
        "today_bs_formatted": today_bs["formatted"],
        "today_bs_full": today_bs["formatted_full"],
        "active_page": "dashboard"
    })

@router.get("/attendance", response_class=HTMLResponse)
def teacher_attendance(request: Request, class_id: Optional[int] = None):
    if not isinstance(class_id, int):
        class_id = None
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    # Fetch all school classes so every teacher can take attendance for any class
    cursor.execute("""
        SELECT c.id as class_id, c.id, c.class_name_ne, c.class_numeric,
               COUNT(s.id) as student_count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        GROUP BY c.id
        ORDER BY c.class_numeric ASC, c.id ASC
    """)
    all_classes = [dict(r) for r in cursor.fetchall()]

    assigned_classes = get_teacher_classes(user)
    if not class_id:
        if assigned_classes:
            class_id = assigned_classes[0]["class_id"]
        elif all_classes:
            class_id = all_classes[0]["class_id"]

    conn.close()

    today_ad = date.today().isoformat()
    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/attendance.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "all_classes": all_classes,
        "classes": all_classes,
        "selected_class_id": class_id,
        "today_date": today_ad,
        "today_bs": today_bs,
        "today_bs_date": today_bs["date_bs"],
        "today_bs_formatted": today_bs["formatted"],
        "today_bs_full": today_bs["formatted_full"],
        "active_page": "attendance"
    })

@router.get("/homework", response_class=HTMLResponse)
def teacher_homework(
    request: Request,
    class_id: Optional[int] = None,
    subject_name: Optional[str] = None
):
    if not isinstance(class_id, int):
        class_id = None
    if not isinstance(subject_name, str):
        subject_name = None
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    # All classes for dropdown
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY c_order ASC, class_numeric ASC, id ASC" if False else "SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC, id ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    # Fetch subjects with class mapping
    cursor.execute("""
        SELECT s.id, s.class_id, s.subject_name_ne, s.subject_code, c.class_name_ne, c.class_numeric
        FROM subjects s
        JOIN classes c ON s.class_id = c.id
        ORDER BY c.class_numeric ASC, s.id ASC
    """)
    subjects = [dict(r) for r in cursor.fetchall()]

    # Query homework items
    query = """
        SELECT h.*, 
               c.class_name_ne, c.class_numeric,
               COALESCE(t.name_nepali, 'विषय शिक्षक') as teacher_name
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        WHERE h.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND h.class_id = ?"
        params.append(class_id)
    if subject_name:
        query += " AND h.subject_name LIKE ?"
        params.append(f"%{subject_name}%")
    
    query += " ORDER BY h.assigned_date DESC, h.id DESC"
    cursor.execute(query, params)
    raw_hw = [dict(r) for r in cursor.fetchall()]

    homework_list = []
    for item in raw_hw:
        q_raw = item.get("questions")
        if q_raw:
            try:
                item["question_list"] = json.loads(q_raw)
            except Exception:
                item["question_list"] = []
        else:
            item["question_list"] = []
        homework_list.append(item)

    assigned_classes = get_teacher_classes(user)
    conn.close()

    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/homework.html", {
        "user": user,
        "settings": settings,
        "classes": classes,
        "subjects": subjects,
        "homework_list": homework_list,
        "selected_class_id": class_id,
        "selected_subject": subject_name or "",
        "assigned_classes": assigned_classes,
        "today_date": date.today().isoformat(),
        "today_bs": today_bs,
        "today_bs_date": today_bs["date_bs"],
        "today_bs_formatted": today_bs["formatted"],
        "today_bs_full": today_bs["formatted_full"],
        "active_page": "homework"
    })

@router.get("/reports", response_class=HTMLResponse)
def teacher_reports(request: Request, report_date: Optional[str] = None):
    if not isinstance(report_date, str):
        report_date = None
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    att_date = report_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    # All classes for complete report visibility
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC, id ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    # Fetch daily attendance summary for all classes
    cursor.execute("""
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
        GROUP BY c.id
        ORDER BY c.class_numeric ASC, c.id ASC
    """, (att_date,))
    class_reports = [dict(r) for r in cursor.fetchall()]

    total_stu = sum(c["total_students"] for c in class_reports)
    total_pres = sum(c["present_count"] or 0 for c in class_reports)
    total_abs = sum(c["absent_count"] or 0 for c in class_reports)
    total_leave = sum(c["leave_count"] or 0 for c in class_reports)
    pct = round((total_pres / total_stu * 100), 1) if total_stu > 0 else 0

    # Absent students list for today
    cursor.execute("""
        SELECT a.*, s.name_nepali as student_name, s.roll_no, s.father_name, s.guardian_phone as father_phone, 
               s.emergency_contact, s.residential_status, c.class_name_ne, 'A' as section
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON a.class_id = c.id
        WHERE a.attendance_date = ? AND a.status = 'ABSENT'
        ORDER BY c.class_numeric ASC, s.roll_no ASC
    """, (att_date,))
    absent_students = [dict(r) for r in cursor.fetchall()]

    # Homework stats
    cursor.execute("""
        SELECT c.class_name_ne, h.subject_name, h.title, h.assigned_date, h.due_date,
               COALESCE(t.name_nepali, 'शिक्षक') as teacher_name
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        WHERE h.status = 'सक्रिय'
        ORDER BY h.assigned_date DESC LIMIT 15
    """)
    recent_homework = [dict(r) for r in cursor.fetchall()]

    conn.close()

    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/reports.html", {
        "user": user,
        "settings": settings,
        "classes": classes,
        "class_reports": class_reports,
        "absent_students": absent_students,
        "recent_homework": recent_homework,
        "report_date": att_date,
        "today_date": date.today().isoformat(),
        "today_bs": today_bs,
        "today_bs_date": today_bs["date_bs"],
        "today_bs_formatted": today_bs["formatted"],
        "today_bs_full": today_bs["formatted_full"],
        "total_students": total_stu,
        "total_present": total_pres,
        "total_absent": total_abs,
        "total_leave": total_leave,
        "percentage": pct,
        "active_page": "reports"
    })

@router.get("/students", response_class=HTMLResponse)
def teacher_students(
    request: Request,
    class_id: Optional[int] = None,
    res_status: Optional[str] = None,
    search: Optional[str] = None
):
    if not isinstance(class_id, int):
        class_id = None
    if not isinstance(res_status, str):
        res_status = None
    if not isinstance(search, str):
        search = None
    user = check_teacher_auth(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC, id ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    query = """
        SELECT s.*, c.class_name_ne, c.class_numeric, 'A' as section
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if res_status:
        query += " AND s.residential_status = ?"
        params.append(res_status)
    if search:
        query += " AND (s.name_nepali LIKE ? OR s.name_english LIKE ? OR s.student_id LIKE ? OR CAST(s.roll_no AS TEXT) LIKE ?)"
        s_wild = f"%{search}%"
        params.extend([s_wild, s_wild, s_wild, s_wild])

    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()

    today_bs = get_today_bs()

    return templates.TemplateResponse(request, "teacher/students.html", {
        "user": user,
        "settings": settings,
        "classes": classes,
        "students": students,
        "selected_class_id": class_id,
        "selected_res": res_status or "",
        "search_term": search or "",
        "today_bs": today_bs,
        "active_page": "students"
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

    return templates.TemplateResponse(request, "admin/attendance_absent.html", {
        "user": user,
        "settings": settings,
        "absent_students": absent_students,
        "today_date": today,
        "active_page": "teacher_absent"
    })

@router.get("/daily-report", response_class=HTMLResponse)
def teacher_daily_report(request: Request, report_date: Optional[str] = Query(None)):
    return RedirectResponse(url=f"/teacher/reports?report_date={report_date or date.today().isoformat()}", status_code=303)

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
