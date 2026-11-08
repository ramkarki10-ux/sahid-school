import os
import json
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, status, Query, Header
from pydantic import BaseModel

from app.database import get_db
from app.auth import (
    verify_password,
    create_session,
    get_current_user_from_token,
    get_current_user
)

router = APIRouter(prefix="/api/mobile", tags=["mobile_api"])

class MobileLoginRequest(BaseModel):
    username: str
    password: str

class MarkAttendanceItem(BaseModel):
    student_id: int
    status: str # 'PRESENT', 'ABSENT', 'LEAVE'
    remarks: Optional[str] = None

class MarkAttendanceRequest(BaseModel):
    class_id: int
    attendance_date: str # YYYY-MM-DD
    records: List[MarkAttendanceItem]

def get_mobile_user(request: Request, authorization: Optional[str] = Header(None)):
    """Authenticate mobile user from Bearer token or cookie."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif request.cookies.get("session_token"):
        token = request.cookies.get("session_token")
    
    if token:
        user = get_current_user_from_token(token)
        if user:
            return user
    return None

# 1. Mobile Authentication
@router.post("/login")
def mobile_login(req: MobileLoginRequest):
    """Mobile cross-platform login for Admin, Teacher, Student, and Parent."""
    username = req.username.strip()
    password = req.password

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users 
        WHERE (username = ? OR phone = ?) AND status = 'ACTIVE'
    """, (username, username))
    user_row = cursor.fetchone()

    if not user_row or not verify_password(password, user_row["password_hash"]):
        conn.close()
        raise HTTPException(
            status_code=401,
            detail="गलत युजरनेम वा पासवर्ड। कृपया पुनः प्रयास गर्नुहोस्।"
        )

    user = dict(user_row)
    token = create_session(user)

    # Fetch extra profile info depending on role
    profile_extra = {}
    if user["role"] == "TEACHER" and user.get("teacher_id"):
        cursor.execute("SELECT * FROM teachers WHERE id = ?", (user["teacher_id"],))
        t_row = cursor.fetchone()
        if t_row:
            profile_extra["teacher_details"] = dict(t_row)
    elif user["role"] == "STUDENT":
        cursor.execute("SELECT s.*, c.class_name_ne FROM students s LEFT JOIN classes c ON s.class_id = c.id WHERE s.guardian_phone = ? OR s.admission_no = ?", (user["phone"], user["username"]))
        s_row = cursor.fetchone()
        if s_row:
            profile_extra["student_details"] = dict(s_row)

    conn.close()

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name_ne": user.get("full_name_ne") or user["username"],
            "full_name_en": user.get("full_name_en") or "",
            "role": user["role"],
            "phone": user.get("phone") or "",
            **profile_extra
        }
    }

@router.get("/profile")
def mobile_profile(request: Request, authorization: Optional[str] = Header(None)):
    """Get current logged in user details for mobile app."""
    user = get_mobile_user(request, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="लगइन सत्र समाप्त भयो।")
    return {"success": True, "user": user}

# 2. Mobile Feed
@router.get("/feed")
def mobile_feed(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    authorization: Optional[str] = Header(None)
):
    """Get dynamic Facebook-style news feed for React Native / Flutter."""
    conn = get_db()
    cursor = conn.cursor()
    user = get_mobile_user(request, authorization)
    user_id = user.get("user_id") if user else None

    cursor.execute("""
        SELECT p.*, n.title_ne as notice_title, n.publish_date as notice_date
        FROM feed_posts p
        LEFT JOIN notices n ON p.notice_id = n.id
        WHERE p.status = 'ACTIVE'
        ORDER BY p.id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    posts = []
    for r in cursor.fetchall():
        p = dict(r)
        p["has_liked"] = False
        if user_id:
            cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (p["id"], user_id))
            p["has_liked"] = bool(cursor.fetchone())

        cursor.execute("SELECT * FROM post_comments WHERE post_id = ? ORDER BY id ASC LIMIT 5", (p["id"],))
        p["recent_comments"] = [dict(c) for c in cursor.fetchall()]
        posts.append(p)

    conn.close()
    return {"success": True, "posts": posts}

# 3. Mobile Attendance
@router.get("/attendance/summary")
def mobile_attendance_summary(date_str: Optional[str] = None):
    """Attendance summary counters and metrics for mobile dashboard."""
    target_date = date_str or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय'")
    total_students = cursor.fetchone()[0]

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as leave
        FROM attendance WHERE attendance_date = ?
    """, (target_date,))
    row = cursor.fetchone()
    present = row["present"] or 0
    absent = row["absent"] or 0
    leave = row["leave"] or 0

    conn.close()
    return {
        "success": True,
        "date": target_date,
        "total_students": total_students,
        "present": present,
        "absent": absent,
        "leave": leave,
        "percentage": round((present / total_students * 100), 1) if total_students > 0 else 0
    }

@router.get("/attendance/class/{class_id}")
def mobile_class_attendance(class_id: int, date_str: Optional[str] = None):
    """Get students of a class with their attendance status for marking/review."""
    target_date = date_str or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id as student_id, s.admission_no, s.name_nepali, s.name_english, s.roll_no,
               a.status as attendance_status, a.remark
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        WHERE s.class_id = ? AND s.status = 'सक्रिय'
        ORDER BY s.roll_no ASC
    """, (target_date, class_id))
    students = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "success": True,
        "class_id": class_id,
        "date": target_date,
        "students": students
    }

@router.post("/attendance/mark")
def mobile_mark_attendance(
    req: MarkAttendanceRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Mark attendance from mobile app (Teachers/Admins)."""
    user = get_mobile_user(request, authorization)
    if not user or user.get("role") not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL", "TEACHER"]:
        raise HTTPException(status_code=403, detail="हाजिरी गर्ने अनुमति छैन।")

    conn = get_db()
    cursor = conn.cursor()

    recorded_by = user.get("user_id") or 1
    marked_count = 0

    for item in req.records:
        cursor.execute("""
            INSERT INTO attendance (
                student_id, academic_year_id, attendance_date, class_id,
                status, remark, recorded_by, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                status = excluded.status,
                remark = excluded.remark,
                recorded_by = excluded.recorded_by,
                updated_at = CURRENT_TIMESTAMP
        """, (item.student_id, req.attendance_date, req.class_id, item.status, item.remarks or "", recorded_by))
        marked_count += 1

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"{marked_count} जना विद्यार्थीहरूको हाजिरी सफलतापूर्वक सुरक्षित गरियो।",
        "date": req.attendance_date
    }

# 4. Mobile Notices
@router.get("/notices")
def mobile_notices(limit: int = 30):
    """Get school notices for mobile app."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT ?", (limit,))
    notices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "notices": notices}

# 5. Mobile Calendar
@router.get("/calendar")
def mobile_calendar():
    """Get academic calendar events for mobile app."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC")
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "events": events}

# 6. Mobile Gallery
@router.get("/gallery")
def mobile_gallery():
    """Get photo albums and pictures for mobile gallery."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo_albums ORDER BY id DESC")
    albums = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM photos ORDER BY id DESC LIMIT 50")
    photos = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "albums": albums, "photos": photos}

# 7. Mobile Classes
@router.get("/classes")
def mobile_classes():
    """Get all classes (१ देखि १२) for mobile dropdowns."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY id ASC")
    classes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "classes": classes}
