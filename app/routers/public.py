from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from typing import Optional
from app.database import get_db
from app.auth import get_current_user
from app.routers.api_parent import get_current_parent
from app.templates import templates

router = APIRouter(tags=["public_views"])

def get_school_context():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})
    
    # Active ticker notice
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' AND featured = 1 ORDER BY id DESC LIMIT 1")
    ticker_row = cursor.fetchone()
    ticker_notice = dict(ticker_row) if ticker_row else None
    
    conn.close()
    return settings, ticker_notice

@router.get("/", response_class=HTMLResponse)
def page_index(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()

    # Dynamic Stats
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
    
    stats = {
        "total_students": total_students,
        "residential_students": residential_students,
        "total_teachers": total_teachers,
        "total_staff": total_staff,
        "total_classes": total_classes
    }

    # Principal message
    cursor.execute("SELECT * FROM school_leadership WHERE role_type = 'PRINCIPAL'")
    p_row = cursor.fetchone()
    principal = dict(p_row) if p_row else None

    # Latest Notices (top 5)
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT 5")
    latest_notices = [dict(r) for r in cursor.fetchall()]

    # Latest News (top 3)
    cursor.execute("SELECT * FROM news WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT 3")
    latest_news = [dict(r) for r in cursor.fetchall()]

    # Facilities (top 6)
    cursor.execute("SELECT * FROM facilities WHERE status = 'सक्रिय' ORDER BY display_order ASC LIMIT 6")
    facilities = [dict(r) for r in cursor.fetchall()]

    # Achievements (top 4)
    cursor.execute("SELECT * FROM achievements ORDER BY year DESC, id DESC LIMIT 4")
    achievements = [dict(r) for r in cursor.fetchall()]

    # Photos for gallery preview (top 6)
    cursor.execute("""
        SELECT p.*, a.title_ne as album_title 
        FROM photos p 
        LEFT JOIN photo_albums a ON p.album_id = a.id 
        ORDER BY p.id DESC LIMIT 6
    """)
    photos = [dict(r) for r in cursor.fetchall()]

    # Videos (top 2)
    cursor.execute("SELECT * FROM videos ORDER BY id DESC LIMIT 2")
    videos = [dict(r) for r in cursor.fetchall()]

    # Publications (top 3)
    cursor.execute("SELECT * FROM publications WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT 3")
    publications = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return templates.TemplateResponse(request, "public/index.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "stats": stats,
        "principal": principal,
        "latest_notices": latest_notices,
        "notices": latest_notices,
        "latest_news": latest_news,
        "news": latest_news,
        "facilities": facilities,
        "achievements": achievements,
        "photos": photos,
        "videos": videos,
        "publications": publications,
        "active_menu": "home"
    })

@router.get("/about", response_class=HTMLResponse)
def page_about(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT position as role, name, phone FROM school_management_committee ORDER BY order_index ASC")
    committee = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM school_leadership")
    leadership = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/about.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "committee": committee,
        "leadership": leadership,
        "active_menu": "about"
    })

@router.get("/administration", response_class=HTMLResponse)
def page_administration(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_management_committee WHERE status = 'सक्रिय' OR status = 'active' ORDER BY order_index ASC")
    smc = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM trustee_committee WHERE status = 'सक्रिय' OR status = 'active' ORDER BY order_index ASC")
    trustee = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM school_leadership")
    leadership = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/administration.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "smc": smc,
        "trustee": trustee,
        "leadership": leadership,
        "current_user": user,
        "is_admin": is_admin,
        "active_menu": "administration"
    })

@router.get("/management-committee", response_class=HTMLResponse)
def page_management_committee(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_management_committee WHERE status = 'सक्रिय' OR status = 'active' ORDER BY order_index ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/management_committee.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "members": members,
        "current_user": user,
        "is_admin": is_admin,
        "active_menu": "administration"
    })

@router.get("/trustee-committee", response_class=HTMLResponse)
def page_trustee_committee(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trustee_committee WHERE status = 'सक्रिय' OR status = 'active' ORDER BY order_index ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/trustee_committee.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "members": members,
        "current_user": user,
        "is_admin": is_admin,
        "active_menu": "administration"
    })

@router.get("/leadership", response_class=HTMLResponse)
def page_leadership(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_leadership ORDER BY id ASC")
    leaders = [dict(r) for r in cursor.fetchall()]
    principal = next((l for l in leaders if l.get("role_type") == "PRINCIPAL"), (leaders[0] if leaders else {}))
    vice_principal = next((l for l in leaders if l.get("role_type") in ["VICE_PRINCIPAL", "ASSISTANT_PRINCIPAL"]), None)
    other_leaders = [l for l in leaders if l.get("id") not in [principal.get("id"), (vice_principal.get("id") if vice_principal else None)]]
    conn.close()
    return templates.TemplateResponse(request, "public/leadership.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "leaders": leaders,
        "principal": principal,
        "vice_principal": vice_principal,
        "other_leaders": other_leaders,
        "leader": principal,
        "is_admin": is_admin,
        "current_user": user,
        "title": "विद्यालय नेतृत्व तथा प्रशासन",
        "active_menu": "administration"
    })

@router.get("/principal", response_class=HTMLResponse)
def page_principal(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_leadership WHERE role_type = 'PRINCIPAL'")
    leader = dict(cursor.fetchone() or {})
    cursor.execute("SELECT * FROM school_leadership ORDER BY id ASC")
    leaders = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/leadership.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "leader": leader,
        "principal": leader,
        "leaders": leaders,
        "is_admin": is_admin,
        "current_user": user,
        "title": "प्रधानाध्यापकको सन्देश",
        "active_menu": "administration"
    })

@router.get("/assistant-principal", response_class=HTMLResponse)
def page_assistant_principal(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_leadership WHERE role_type IN ('VICE_PRINCIPAL', 'ASSISTANT_PRINCIPAL') LIMIT 1")
    leader = dict(cursor.fetchone() or {})
    cursor.execute("SELECT * FROM school_leadership ORDER BY id ASC")
    leaders = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/leadership.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "leader": leader,
        "vice_principal": leader,
        "leaders": leaders,
        "is_admin": is_admin,
        "current_user": user,
        "title": "सहायक प्रधानाध्यापकको सन्देश",
        "active_menu": "administration"
    })

@router.get("/teachers", response_class=HTMLResponse)
def page_teachers(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL", "CONTENT_EDITOR"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE status = 'सक्रिय' ORDER BY id ASC")
    teachers = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/teachers.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "teachers": teachers,
        "is_admin": is_admin,
        "current_user": user,
        "active_menu": "teachers"
    })

@router.get("/staff", response_class=HTMLResponse)
def page_staff(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE status = 'सक्रिय' ORDER BY id ASC")
    staff = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/staff.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "staff": staff,
        "active_menu": "administration"
    })

@router.get("/academics", response_class=HTMLResponse)
def page_academics(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/academics.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "classes": classes,
        "active_menu": "academics"
    })

@router.get("/students", response_class=HTMLResponse)
def page_students(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.class_name_ne, COUNT(s.id) as student_count,
               SUM(CASE WHEN s.residential_status = 'आवासीय' THEN 1 ELSE 0 END) as residential_count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        GROUP BY c.id
        ORDER BY c.class_numeric ASC
    """)
    class_stats = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय'")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय' AND residential_status = 'आवासीय'")
    residential_students = cursor.fetchone()[0]
    stats = {
        "total_students": total_students,
        "residential_students": residential_students,
        "day_students": total_students - residential_students
    }

    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT s.id, s.student_id, s.admission_no, s.name_nepali, s.name_english,
               s.gender, s.roll_no, s.address, s.guardian_name, s.guardian_phone,
               s.residential_status, s.class_id, c.class_name_ne, sec.name as section_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        WHERE s.status = 'सक्रिय'
        ORDER BY c.class_numeric ASC, s.roll_no ASC
    """)
    students_list = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return templates.TemplateResponse(request, "public/students.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "class_stats": class_stats,
        "classes": classes,
        "students_list": students_list,
        "stats": stats,
        "active_menu": "students"
    })

@router.get("/alumni", response_class=HTMLResponse)
def page_alumni(
    request: Request,
    passed_class: Optional[str] = None,
    pass_out_year: Optional[str] = None,
    search: Optional[str] = None
):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT pass_out_year FROM alumni ORDER BY pass_out_year DESC")
    available_years = [r[0] for r in cursor.fetchall() if r[0]]

    cursor.execute("SELECT COUNT(*) FROM alumni")
    total_alumni = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alumni WHERE passed_class = 'कक्षा १०'")
    total_see = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alumni WHERE passed_class = 'कक्षा १२'")
    total_plus2 = cursor.fetchone()[0]

    query = "SELECT * FROM alumni WHERE 1=1"
    params = []
    if passed_class:
        query += " AND passed_class = ?"
        params.append(passed_class)
    if pass_out_year:
        query += " AND pass_out_year = ?"
        params.append(pass_out_year)
    if search:
        query += " AND (full_name LIKE ? OR address LIKE ? OR phone LIKE ? OR symbol_no LIKE ? OR current_status LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s, s])

    query += " ORDER BY pass_out_year DESC, passed_class DESC, id DESC"
    cursor.execute(query, params)
    alumni_list = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return templates.TemplateResponse(request, "public/alumni.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "alumni_list": alumni_list,
        "available_years": available_years,
        "selected_class": passed_class or "",
        "selected_year": pass_out_year or "",
        "search_term": search or "",
        "total_alumni": total_alumni,
        "total_see": total_see,
        "total_plus2": total_plus2,
        "active_menu": "alumni"
    })

@router.get("/admission", response_class=HTMLResponse)
def page_admission(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/admission.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "classes": classes,
        "active_menu": "admission"
    })

@router.get("/notices", response_class=HTMLResponse)
def page_notices(request: Request, category: Optional[str] = None):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' AND category = ? ORDER BY id DESC", (category,))
    else:
        cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC")
    notices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/notices.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "notices": notices,
        "selected_category": category or "",
        "active_menu": "notices"
    })

@router.get("/news", response_class=HTMLResponse)
def page_news(request: Request, category: Optional[str] = None):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM news WHERE status = 'सक्रिय' AND category = ? ORDER BY id DESC", (category,))
    else:
        cursor.execute("SELECT * FROM news WHERE status = 'सक्रिय' ORDER BY id DESC")
    news_items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/news.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "news": news_items,
        "selected_category": category or "",
        "active_menu": "notices"
    })

@router.get("/publications", response_class=HTMLResponse)
def page_publications(request: Request, category: Optional[str] = None):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM publications WHERE status = 'सक्रिय' AND category = ? ORDER BY id DESC", (category,))
    else:
        cursor.execute("SELECT * FROM publications WHERE status = 'सक्रिय' ORDER BY id DESC")
    publications = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/publications.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "publications": publications,
        "selected_category": category or "",
        "active_menu": "publications"
    })

@router.get("/achievements", response_class=HTMLResponse)
def page_achievements(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM achievements ORDER BY year DESC, id DESC")
    achievements = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/achievements.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "achievements": achievements,
        "active_menu": "achievements"
    })

@router.get("/gallery", response_class=HTMLResponse)
def page_gallery(request: Request, category: Optional[str] = None):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM photo_albums WHERE category = ? ORDER BY id DESC", (category,))
    else:
        cursor.execute("SELECT * FROM photo_albums ORDER BY id DESC")
    albums = [dict(a) for a in cursor.fetchall()]
    for alb in albums:
        cursor.execute("SELECT * FROM photos WHERE album_id = ? ORDER BY id ASC", (alb["id"],))
        alb["photos"] = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/gallery.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "albums": albums,
        "selected_category": category or "",
        "active_menu": "gallery"
    })

@router.get("/videos", response_class=HTMLResponse)
def page_videos(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY id DESC")
    videos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/videos.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "videos": videos,
        "active_menu": "gallery"
    })

@router.get("/facilities", response_class=HTMLResponse)
def page_facilities(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facilities WHERE status = 'सक्रिय' ORDER BY display_order ASC")
    facilities = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/facilities.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "facilities": facilities,
        "active_menu": "about"
    })

@router.get("/contact", response_class=HTMLResponse)
def page_contact(request: Request):
    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "public/contact.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "contact"
    })

@router.get("/support", response_class=HTMLResponse)
@router.get("/partners", response_class=HTMLResponse)
def page_support(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    is_admin = bool(user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"])
    return templates.TemplateResponse(request, "public/support.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "support",
        "current_user": user,
        "is_admin": is_admin
    })

@router.get("/signup", response_class=HTMLResponse)
def page_signup(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    if user:
        if user["role"] == "TEACHER":
            return RedirectResponse(url="/teacher/dashboard", status_code=303)
        elif user["role"] in ("STUDENT", "PARENT"):
            return RedirectResponse(url="/leave-application", status_code=303)
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes WHERE class_numeric >= 1 AND class_numeric <= 12 ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()

    redirect_to = request.query_params.get("redirect", "")

    return templates.TemplateResponse(request, "public/signup.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "classes": classes,
        "redirect_to": redirect_to,
        "active_menu": "signup"
    })

@router.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    if user:
        if user["role"] == "TEACHER":
            return RedirectResponse(url="/teacher/dashboard", status_code=303)
        elif user["role"] in ("STUDENT", "PARENT"):
            return RedirectResponse(url="/leave-application", status_code=303)
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    
    redirect_to = request.query_params.get("redirect", "")
    return templates.TemplateResponse(request, "public/login.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "redirect_to": redirect_to,
        "active_menu": "login"
    })

@router.get("/homework", response_class=HTMLResponse)
def page_homework(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT s.id, s.class_id, s.subject_name_ne, s.subject_code, c.class_name_ne
        FROM subjects s
        JOIN classes c ON s.class_id = c.id
        ORDER BY c.class_numeric ASC, s.id ASC
    """)
    subjects = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT h.*, c.class_name_ne, COALESCE(t.name_nepali, 'विषय शिक्षक') as teacher_name
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        WHERE h.status = 'सक्रिय'
        ORDER BY h.assigned_date DESC, h.id DESC
        LIMIT 30
    """)
    raw_hw = [dict(r) for r in cursor.fetchall()]
    conn.close()

    import json
    homework_list = []
    for hw in raw_hw:
        q_raw = hw.get("questions")
        if q_raw:
            try:
                hw["question_list"] = json.loads(q_raw)
            except Exception:
                hw["question_list"] = []
        else:
            hw["question_list"] = []
        homework_list.append(hw)

    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "public/homework.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "classes": classes,
        "subjects": subjects,
        "homework_list": homework_list,
        "active_menu": "students"
    })

@router.get("/leave-application", response_class=HTMLResponse)
def page_leave_application(request: Request):
    settings, ticker_notice = get_school_context()
    user = get_current_user(request)
    parent = get_current_parent(request)
    
    is_authenticated = bool(user or parent)
    user_role = user.get("role") if user else ("PARENT" if parent else None)
    
    logged_name = ""
    student_info = {
        "student_name": "",
        "class_id": "",
        "roll_no": "",
        "applicant_name": "",
        "applicant_phone": ""
    }

    conn = get_db()
    cursor = conn.cursor()

    if user:
        logged_name = user.get("full_name_ne") or user.get("username", "")
        # Try to find corresponding student record by user's phone or name
        cursor.execute("""
            SELECT id, name_nepali, class_id, roll_no, guardian_name, guardian_phone
            FROM students
            WHERE guardian_phone = ? OR name_nepali = ?
            ORDER BY id DESC LIMIT 1
        """, (user.get("phone", ""), user.get("full_name_ne", "")))
        s_row = cursor.fetchone()
        
        # Or check in user_registrations for this student
        if not s_row and user.get("role") == "STUDENT":
            cursor.execute("""
                SELECT full_name_ne, class_id, roll_no, guardian_name, guardian_phone, phone
                FROM user_registrations
                WHERE phone = ? AND user_type = 'STUDENT'
                ORDER BY id DESC LIMIT 1
            """, (user.get("phone", ""),))
            reg_row = cursor.fetchone()
            if reg_row:
                student_info["student_name"] = reg_row["full_name_ne"]
                student_info["class_id"] = reg_row["class_id"]
                student_info["roll_no"] = reg_row["roll_no"]
                student_info["applicant_name"] = reg_row["full_name_ne"]
                student_info["applicant_phone"] = reg_row["guardian_phone"] or reg_row["phone"]

        if s_row:
            student_info["student_name"] = s_row["name_nepali"]
            student_info["class_id"] = s_row["class_id"]
            student_info["roll_no"] = s_row["roll_no"]
            student_info["applicant_name"] = s_row["guardian_name"] if user.get("role") == "PARENT" else s_row["name_nepali"]
            student_info["applicant_phone"] = s_row["guardian_phone"] or user.get("phone", "")

    elif parent:
        logged_name = parent.get("guardian_name") or "अभिभावक"
        parent_phone = parent.get("phone", "")
        cursor.execute("""
            SELECT id, name_nepali, class_id, roll_no, guardian_name, guardian_phone
            FROM students
            WHERE guardian_phone = ?
            ORDER BY id DESC LIMIT 1
        """, (parent_phone,))
        s_row = cursor.fetchone()
        if s_row:
            student_info["student_name"] = s_row["name_nepali"]
            student_info["class_id"] = s_row["class_id"]
            student_info["roll_no"] = s_row["roll_no"]
            student_info["applicant_name"] = s_row["guardian_name"] or logged_name
            student_info["applicant_phone"] = parent_phone
        else:
            student_info["applicant_name"] = logged_name
            student_info["applicant_phone"] = parent_phone

    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT l.*, c.class_name_ne
        FROM leave_applications l
        JOIN classes c ON l.class_id = c.id
        ORDER BY l.id DESC LIMIT 20
    """)
    recent_leaves = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return templates.TemplateResponse(request, "public/leave_application.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "classes": classes,
        "recent_leaves": recent_leaves,
        "is_authenticated": is_authenticated,
        "current_user": user,
        "user_role": user_role,
        "logged_name": logged_name,
        "student_info": student_info,
        "active_menu": "students"
    })

@router.get("/calendar", response_class=HTMLResponse)
def page_calendar(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC")
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/calendar.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "events": events,
        "active_menu": "academics"
    })

@router.get("/attendance-view", response_class=HTMLResponse)
def page_attendance_view(request: Request):
    parent = get_current_parent(request)
    if parent:
        return RedirectResponse(url="/parent/dashboard", status_code=303)
    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "public/attendance_view.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "students"
    })

@router.get("/results", response_class=HTMLResponse)
def page_results(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    exams = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/results.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "exams": exams,
        "classes": classes,
        "active_menu": "results"
    })

@router.get("/class-notices", response_class=HTMLResponse)
def page_class_notices(request: Request):
    settings, ticker_notice = get_school_context()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC")
    notices = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes ORDER BY class_numeric ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request, "public/notices.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "notices": notices,
        "classes": classes,
        "active_menu": "students"
    })

@router.get("/citizen-charter", response_class=HTMLResponse)
def page_citizen_charter(request: Request):
    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "public/citizen_charter.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "administration"
    })

@router.get("/download-project")
def download_project():
    import os
    import zipfile
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    downloads_dir = os.path.join(project_dir, 'static', 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    zip_path = os.path.join(downloads_dir, 'Shahid_Smriti_School_Website_Complete.zip')
    
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'downloads'}
    exclude_files = {'Shahid_Smriti_School_Website_Complete.zip'}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file in exclude_files or file.endswith('.pyc'):
                    continue
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir)
                zipf.write(abs_path, os.path.join('shahid-smriti-school', rel_path))
                
    return FileResponse(
        path=zip_path,
        media_type='application/zip',
        filename='Shahid_Smriti_School_Website_Complete.zip'
    )

@router.get("/download-db")
def download_db():
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'school.db')
    return FileResponse(
        path=db_path,
        media_type='application/x-sqlite3',
        filename='school_backup.db'
    )

@router.get("/download", response_class=HTMLResponse)
def page_download(request: Request):
    settings, ticker_notice = get_school_context()
    return templates.TemplateResponse(request, "public/download.html", {
        "settings": settings,
        "ticker_notice": ticker_notice,
        "active_menu": "download"
    })


