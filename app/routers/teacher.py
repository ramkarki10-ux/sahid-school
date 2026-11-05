from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date
from app.database import get_db
from app.auth import get_current_user
from app.templates import templates

router = APIRouter(prefix="/teacher", tags=["teacher_views"])

def check_teacher_auth(request: Request):
    user = get_current_user(request)
    if not user:
        return None
    if user["role"] not in ["TEACHER", "SUPER_ADMIN", "PRINCIPAL"]:
        return None
    return user

def get_teacher_classes(user: dict):
    conn = get_db()
    cursor = conn.cursor()
    teacher_id = user.get("teacher_id")
    if not teacher_id and user["role"] == "TEACHER":
        cursor.execute("SELECT id FROM teachers WHERE email = ? OR phone = ? LIMIT 1", (user["username"], user["username"]))
        t_row = cursor.fetchone()
        if t_row:
            teacher_id = t_row["id"]

    if teacher_id:
        cursor.execute("""
            SELECT a.class_id, a.is_class_teacher,
                   c.class_name_ne, c.class_numeric, 'A' as section,
                   COUNT(s.id) as student_count
            FROM teacher_class_assignments a
            JOIN classes c ON a.class_id = c.id
            LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
            WHERE a.teacher_id = ?
            GROUP BY a.class_id
            ORDER BY c.class_numeric ASC
        """, (teacher_id,))
    else:
        cursor.execute("""
            SELECT c.id as class_id, 'सम्पूर्ण कक्षा' as subject_name, 1 as is_class_teacher,
                   c.class_name_ne, c.class_numeric, 'A' as section,
                   COUNT(s.id) as student_count
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
            GROUP BY c.id
            ORDER BY c.class_numeric ASC
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

    return templates.TemplateResponse(request, "teacher/attendance.html", {
        "user": user,
        "settings": settings,
        "assigned_classes": assigned_classes,
        "selected_class_id": class_id,
        "today_date": date.today().isoformat()
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
