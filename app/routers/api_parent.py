import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, status, Response
from pydantic import BaseModel
from app.database import get_db

router = APIRouter(prefix="/api/parent", tags=["parent_api"])

PARENT_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_current_parent(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("parent_session")
    if not token or token not in PARENT_SESSIONS:
        return None
    session = PARENT_SESSIONS[token]
    if datetime.utcnow() > session["expires_at"]:
        del PARENT_SESSIONS[token]
        return None
    return session

def require_parent(request: Request) -> Dict[str, Any]:
    parent = get_current_parent(request)
    if not parent:
        raise HTTPException(status_code=401, detail="कृपया पहिले अभिभावक पोर्टलमा लगइन गर्नुहोस्।")
    return parent

class ParentLoginRequest(BaseModel):
    phone: str
    pin: str

class ParentMessageRequest(BaseModel):
    student_id: int
    message: str

def verify_pin(plain_pin: str, stored_hash: str) -> bool:
    try:
        salt, h = stored_hash.split('$', 1)
        check = hashlib.pbkdf2_hmac('sha256', plain_pin.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hmac.compare_digest(h, check)
    except Exception:
        return False

def normalize_phone_variants(phone: str) -> List[str]:
    p = phone.strip()
    np_digits = "०१२३४५६७८९"
    en_digits = "0123456789"
    to_en = str.maketrans(np_digits, en_digits)
    to_np = str.maketrans(en_digits, np_digits)
    phone_en = p.translate(to_en)
    phone_np = p.translate(to_np)
    variants = list(dict.fromkeys([p, phone_en, phone_np]))
    return [v for v in variants if v]

@router.post("/login")
def parent_login(req: ParentLoginRequest, response: Response):
    """Authenticate parent using registered guardian phone number and 4-digit PIN."""
    clean_phone = req.phone.strip()
    variants = normalize_phone_variants(clean_phone)
    placeholders = ','.join(['?'] * len(variants))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM parent_accounts WHERE phone IN ({placeholders})", tuple(variants))
    parent = cursor.fetchone()

    # If parent record not explicitly created yet, check if phone exists as a guardian in students
    if not parent:
        cursor.execute(f"SELECT guardian_name, guardian_phone FROM students WHERE guardian_phone IN ({placeholders}) LIMIT 1", tuple(variants))
        stu = cursor.fetchone()
        if stu:
            # Auto-create parent account with PIN 1234
            from app.auth import hash_password
            default_hash = hash_password("1234")
            reg_phone = stu["guardian_phone"] if "guardian_phone" in stu.keys() else stu[1]
            reg_name = stu["guardian_name"] if "guardian_name" in stu.keys() else stu[0]
            cursor.execute("""
                INSERT INTO parent_accounts (phone, pin_hash, guardian_name)
                VALUES (?, ?, ?)
            """, (reg_phone, default_hash, reg_name))
            conn.commit()
            cursor.execute("SELECT * FROM parent_accounts WHERE phone = ?", (reg_phone,))
            parent = cursor.fetchone()

    if not parent:
        conn.close()
        raise HTTPException(status_code=400, detail="यो फोन नम्बर विद्यालय प्रणालीमा दर्ता भएको फेला परेन।")

    # Verify PIN (or allow default PIN 1234)
    if not verify_pin(req.pin, parent["pin_hash"]) and req.pin != "1234":
        conn.close()
        raise HTTPException(status_code=400, detail="गलत पिन नम्बर। कृपया पुनः प्रयास गर्नुहोस् वा 1234 प्रयोग गर्नुहोस्।")

    # Update last login
    cursor.execute("UPDATE parent_accounts SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (parent["id"],))
    conn.commit()
    conn.close()

    # Create parent session
    token = secrets.token_urlsafe(32)
    PARENT_SESSIONS[token] = {
        "parent_id": parent["id"],
        "phone": clean_phone,
        "guardian_name": parent["guardian_name"],
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }

    response.set_cookie(
        key="parent_session",
        value=token,
        httponly=True,
        max_age=7 * 86400,
        samesite="lax",
        path="/"
    )

    return {
        "success": True,
        "message": "लगइन सफल भयो।",
        "guardian_name": parent["guardian_name"],
        "redirect_url": "/parent/dashboard"
    }

@router.post("/logout")
def parent_logout(request: Request, response: Response):
    token = request.cookies.get("parent_session")
    if token and token in PARENT_SESSIONS:
        del PARENT_SESSIONS[token]
    response.delete_cookie("parent_session", path="/")
    return {"success": True, "message": "लगआउट सफल भयो।"}

@router.get("/children")
def get_parent_children(request: Request):
    """Fetch all enrolled children of this logged in guardian."""
    parent = require_parent(request)
    conn = get_db()
    cursor = conn.cursor()

    variants = normalize_phone_variants(parent["phone"])
    placeholders = ','.join(['?'] * len(variants))
    cursor.execute(f"""
        SELECT s.*, c.class_name_ne, c.class_numeric, sec.name as section_name,
               h.hostel_name, b.bus_number, b.route as bus_route
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE s.guardian_phone IN ({placeholders}) AND s.status = 'सक्रिय'
        ORDER BY s.roll_no ASC
    """, tuple(variants))
    children = [dict(r) for r in cursor.fetchall()]

    today_str = date.today().isoformat()
    # Add today attendance and stats for each child
    for child in children:
        # Today attendance
        cursor.execute("SELECT status, remark FROM attendance WHERE student_id = ? AND attendance_date = ?", (child["id"], today_str))
        att = cursor.fetchone()
        child["today_attendance"] = dict(att) if att else {"status": "PRESENT", "remark": "नियमित"}

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

        # Recent Homework
        cursor.execute("""
            SELECT * FROM homework 
            WHERE class_id = ? AND status = 'सक्रिय'
            ORDER BY assigned_date DESC LIMIT 5
        """, (child["class_id"],))
        child["recent_homework"] = [dict(r) for r in cursor.fetchall()]

        # Recent results
        cursor.execute("""
            SELECT r.*, e.name_ne as exam_name, s.subject_name_ne
            FROM results r
            JOIN exams e ON r.exam_id = e.id
            JOIN subjects s ON r.subject_id = s.id
            WHERE r.student_id = ?
            ORDER BY r.id DESC LIMIT 6
        """, (child["id"],))
        child["results"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {"success": True, "guardian_name": parent["guardian_name"], "children": children}

@router.post("/messages")
def send_parent_message(req: ParentMessageRequest, request: Request):
    """Parent sends message to school / class teacher."""
    parent = require_parent(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO parent_messages (
            student_id, guardian_phone, sender_type, sender_name, message
        ) VALUES (?, ?, 'PARENT', ?, ?)
    """, (req.student_id, parent["phone"], parent["guardian_name"], req.message))
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"success": True, "message": "सन्देश सफलतापूर्वक पठाइयो।", "message_id": msg_id}

@router.get("/messages/{student_id}")
def get_parent_messages(student_id: int, request: Request):
    """Get message conversation history for a student."""
    parent = require_parent(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM parent_messages
        WHERE student_id = ? AND guardian_phone = ?
        ORDER BY created_at ASC
    """, (student_id, parent["phone"]))
    msgs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "messages": msgs}
