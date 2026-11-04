from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from app.database import get_db
from app.routers.api_parent import get_current_parent

router = APIRouter(prefix="/parent", tags=["parent_views"])
templates = Jinja2Templates(directory="templates")

def get_school_context():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' AND featured = 1 ORDER BY id DESC LIMIT 1")
    ticker_row = cursor.fetchone()
    ticker_notice = dict(ticker_row) if ticker_row else None
    conn.close()
    return settings, ticker_notice

@router.get("/login", response_class=HTMLResponse)
def parent_login_page(request: Request):
    parent = get_current_parent(request)
    if parent:
        return RedirectResponse(url="/parent/dashboard", status_code=303)
    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "parent/login.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "parent"
    })

@router.get("/dashboard", response_class=HTMLResponse)
def parent_dashboard_page(request: Request):
    parent = get_current_parent(request)
    if not parent:
        return RedirectResponse(url="/parent/login", status_code=303)
    
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()

    # Fetch children linked to parent phone
    cursor.execute("""
        SELECT s.*, c.class_name_ne, c.class_numeric, sec.name as section_name,
               h.hostel_name, h.warden, h.warden_phone,
               b.bus_number, b.route as bus_route, b.driver_name, b.driver_phone
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE s.guardian_phone = ? AND s.status = 'सक्रिय'
        ORDER BY s.roll_no ASC
    """, (parent["phone"],))
    children = [dict(r) for r in cursor.fetchall()]

    today_str = date.today().isoformat()
    for child in children:
        # Today attendance
        cursor.execute("SELECT status, remark FROM attendance WHERE student_id = ? AND attendance_date = ?", (child["id"], today_str))
        att = cursor.fetchone()
        child["today_attendance"] = dict(att) if att else {"status": "PRESENT", "remark": "नियमित उपस्थिति"}

        # Total attendance stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_days,
                SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as present_days,
                SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as absent_days,
                SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as leave_days
            FROM attendance WHERE student_id = ?
        """, (child["id"],))
        stats_row = cursor.fetchone()
        tot = stats_row["total_days"] or 0
        pres = stats_row["present_days"] or 0
        child["attendance_stats"] = {
            "total_days": tot,
            "present_days": pres,
            "absent_days": stats_row["absent_days"] or 0,
            "percentage": round(pres / tot * 100, 1) if tot > 0 else 100.0
        }

        # Homework
        cursor.execute("""
            SELECT h.*, t.name_nepali as teacher_name
            FROM homework h
            JOIN teachers t ON h.teacher_id = t.id
            WHERE h.class_id = ? AND h.status = 'सक्रिय'
            ORDER BY h.assigned_date DESC LIMIT 5
        """, (child["class_id"],))
        raw_hw = [dict(r) for r in cursor.fetchall()]
        parsed_hw = []
        for hw in raw_hw:
            q_raw = hw.get("questions")
            if q_raw:
                try:
                    import json
                    hw["question_list"] = json.loads(q_raw)
                except Exception:
                    hw["question_list"] = []
            else:
                hw["question_list"] = []
            parsed_hw.append(hw)
        child["recent_homework"] = parsed_hw

        # Results
        cursor.execute("""
            SELECT r.*, e.name_ne as exam_name, s.subject_name_ne
            FROM results r
            JOIN exams e ON r.exam_id = e.id
            JOIN subjects s ON r.subject_id = s.id
            WHERE r.student_id = ?
            ORDER BY r.id DESC LIMIT 6
        """, (child["id"],))
        child["results"] = [dict(r) for r in cursor.fetchall()]

    # School notices
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT 4")
    notices = [dict(r) for r in cursor.fetchall()]

    # Calendar events
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC LIMIT 5")
    events = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return templates.TemplateResponse(request, "parent/dashboard.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "parent": parent,
        "children": children,
        "notices": notices,
        "events": events,
        "active_menu": "parent"
    })

@router.get("/logout")
def parent_logout_view():
    resp = RedirectResponse(url="/parent/login", status_code=303)
    resp.delete_cookie("parent_session", path="/")
    return resp
