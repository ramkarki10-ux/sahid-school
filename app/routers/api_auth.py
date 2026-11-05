from fastapi import APIRouter, Request, Response, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.auth import verify_password, hash_password, create_session, get_current_user, require_auth, SESSIONS
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    user_type: str  # 'STUDENT', 'TEACHER', 'PARENT'
    first_name: str
    last_name: str
    phone: str
    password: str
    # Student specific
    class_id: Optional[int] = None
    roll_no: Optional[int] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    # Teacher specific
    subject: Optional[str] = None
    # Parent specific
    student_name: Optional[str] = None
    student_phone: Optional[str] = None

@router.post("/signup")
def api_signup(req: SignupRequest, request: Request):
    """
    Public self-registration endpoint for Students, Teachers, and Parents.
    - STUDENT: Requires Class 1-12, Roll, Guardian info. Submitted for Super Admin review.
    - TEACHER: Requires Phone, Subject/Role. Submitted for Super Admin review.
    - PARENT: Requires Phone, Student info. Directly approved and activated without Admin approval.
    """
    user_type = req.user_type.upper().strip()
    if user_type not in ("STUDENT", "TEACHER", "PARENT"):
        raise HTTPException(status_code=400, detail="कृपया मान्य विकल्प छनोट गर्नुहोस् (विद्यार्थी, शिक्षक, वा अभिभावक)।")

    first_name = req.first_name.strip()
    last_name = req.last_name.strip()
    full_name_ne = f"{first_name} {last_name}".strip()
    phone = req.phone.strip()
    password = req.password.strip()

    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="कृपया आफ्नो नाम र थर अनिवार्य भर्नुहोस्।")
    if not phone or len(phone) < 7:
        raise HTTPException(status_code=400, detail="कृपया मान्य मोबाइल नम्बर भर्नुहोस्।")
    if not password or len(password) < 4:
        raise HTTPException(status_code=400, detail="पासवर्ड कम्तीमा ४ अक्षर वा अंकको हुनुपर्छ।")

    conn = get_db()
    cursor = conn.cursor()

    # Check if this phone is already an active user
    cursor.execute("SELECT id, role, status FROM users WHERE username = ? OR phone = ?", (phone, phone))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="यो मोबाइल नम्बर पहिले नै प्रणालीमा दर्ता भइसकेको छ। कृपया लगइन गर्नुहोस्।")

    # Check if there is already a pending registration with this phone
    cursor.execute("SELECT id, status FROM user_registrations WHERE phone = ? AND status = 'विचाराधीन'", (phone,))
    pending_reg = cursor.fetchone()
    if pending_reg:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="यो मोबाइल नम्बरबाट दर्ता आवेदन पहिले नै पेस भइसकेको छ र प्रमुख एडमिनको स्वीकृतिको पर्खाइमा छ।"
        )

    pwd_hash = hash_password(password)

    if user_type == "STUDENT":
        if not req.class_id:
            conn.close()
            raise HTTPException(status_code=400, detail="विद्यार्थीको लागि कक्षा (१ देखि १२) छनोट गर्न अनिवार्य छ।")
        if not req.roll_no:
            conn.close()
            raise HTTPException(status_code=400, detail="विद्यार्थीको रोल नम्बर अनिवार्य छ।")
        if not req.guardian_name or not req.guardian_phone:
            conn.close()
            raise HTTPException(status_code=400, detail="अभिभावकको नाम र मोबाइल नम्बर अनिवार्य छ।")

        # Get class name
        cursor.execute("SELECT class_name_ne FROM classes WHERE id = ?", (req.class_id,))
        cls_row = cursor.fetchone()
        class_name = cls_row["class_name_ne"] if cls_row else f"कक्षा {req.class_id}"

        cursor.execute("""
            INSERT INTO user_registrations (
                user_type, first_name, last_name, full_name_ne, phone, password_hash,
                class_id, class_name, roll_no, guardian_name, guardian_phone,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'विचाराधीन')
        """, (
            user_type, first_name, last_name, full_name_ne, phone, pwd_hash,
            req.class_id, class_name, req.roll_no, req.guardian_name.strip(), req.guardian_phone.strip()
        ))
        reg_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "registration_id": reg_id,
            "user_type": "STUDENT",
            "status": "विचाराधीन",
            "requires_approval": True,
            "message": "विद्यार्थी दर्ता सफलतापूर्वक पेस भयो! प्रमुख एडमिनले रुजु गरी स्वीकृत गरेपछि खाता पूर्ण हुनेछ र तपाईंले लगइन गर्न सक्नुहुनेछ।"
        }

    elif user_type == "TEACHER":
        subject = (req.subject or "").strip() or "शिक्षक"
        cursor.execute("""
            INSERT INTO user_registrations (
                user_type, first_name, last_name, full_name_ne, phone, password_hash,
                subject, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'विचाराधीन')
        """, (
            user_type, first_name, last_name, full_name_ne, phone, pwd_hash,
            subject
        ))
        reg_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "registration_id": reg_id,
            "user_type": "TEACHER",
            "status": "विचाराधीन",
            "requires_approval": True,
            "message": "शिक्षक दर्ता सफलतापूर्वक पेस भयो! प्रमुख एडमिनले रुजु गरी स्वीकृत गरेपछि तपाईंको शिक्षक आइडी सक्रिय हुनेछ।"
        }

    else:  # PARENT (अभिभावक) - Automatically approved!
        student_name = (req.student_name or "").strip()
        student_phone = (req.student_phone or "").strip()
        if not student_name:
            conn.close()
            raise HTTPException(status_code=400, detail="कृपया आफ्नो विद्यार्थीको नाम अनिवार्य भर्नुहोस्।")

        # Save to registrations with status 'स्वीकृत'
        cursor.execute("""
            INSERT INTO user_registrations (
                user_type, first_name, last_name, full_name_ne, phone, password_hash,
                student_name, student_phone, status, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'स्वीकृत', CURRENT_TIMESTAMP)
        """, (
            user_type, first_name, last_name, full_name_ne, phone, pwd_hash,
            student_name, student_phone
        ))
        reg_id = cursor.lastrowid

        # Directly create/activate user account in users table
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name_ne, phone, role, status)
            VALUES (?, ?, ?, ?, 'PARENT', 'ACTIVE')
        """, (phone, pwd_hash, full_name_ne, phone))

        # Also store in parent_accounts
        cursor.execute("""
            INSERT OR REPLACE INTO parent_accounts (phone, pin_hash, guardian_name)
            VALUES (?, ?, ?)
        """, (phone, pwd_hash, full_name_ne))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "registration_id": reg_id,
            "user_type": "PARENT",
            "status": "स्वीकृत",
            "requires_approval": False,
            "message": "अभिभावक खाता सफलतापूर्वक तयार भयो! तपाईं तुरुन्तै लगइन गर्न सक्नुहुन्छ।"
        }

@router.post("/login")
def api_login(req: LoginRequest, response: Response, request: Request):
    """
    Authenticate user via username OR phone number.
    Handles Admins, Teachers, Students, and Parents.
    Shows informative pending message if registration is awaiting Super Admin approval.
    """
    identifier = req.username.strip()
    conn = get_db()
    cursor = conn.cursor()

    # Search in users table by username OR phone
    cursor.execute("""
        SELECT id, username, password_hash, full_name_ne, full_name_en, role, teacher_id, status, phone
        FROM users 
        WHERE username = ? OR phone = ?
    """, (identifier, identifier))
    user = cursor.fetchone()

    # If not found in users table, check if there is a pending/rejected registration
    if not user:
        cursor.execute("""
            SELECT id, user_type, full_name_ne, status, password_hash 
            FROM user_registrations 
            WHERE phone = ?
            ORDER BY id DESC LIMIT 1
        """, (identifier,))
        reg = cursor.fetchone()
        conn.close()

        if reg:
            if reg["status"] == "विचाराधीन":
                raise HTTPException(
                    status_code=403,
                    detail="तपाईंको दर्ता आवेदन प्रमुख एडमिनको स्वीकृतिको पर्खाइमा छ (Pending Approval)। प्रमुख एडमिनले स्वीकृत गरेपछि मात्र खाता खुल्नेछ।"
                )
            elif reg["status"] == "अस्वीकृत":
                raise HTTPException(
                    status_code=403,
                    detail="तपाईंको दर्ता आवेदन अस्वीकृत गरिएको छ। थप जानकारीका लागि विद्यालय प्रशासनमा सम्पर्क गर्नुहोस्।"
                )

        raise HTTPException(status_code=401, detail="गलत प्रयोगकर्ता नाम/मोबाइल नम्बर वा पासवर्ड।")

    conn.close()

    # Verify password
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="गलत प्रयोगकर्ता नाम/मोबाइल नम्बर वा पासवर्ड।")

    if user["status"] not in ("ACTIVE", "सक्रिय"):
        raise HTTPException(status_code=403, detail="तपाईंको खाता निष्क्रिय गरिएको छ।")

    user_dict = dict(user)
    token = create_session(user_dict)

    # Set HTTP-only cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )

    # Determine default redirect URL based on role
    redirect_url = "/admin/dashboard"
    if user["role"] == "TEACHER":
        redirect_url = "/teacher/dashboard"
    elif user["role"] in ("STUDENT", "PARENT"):
        redirect_url = "/leave-application"

    log_audit("LOGIN", "AUTH", record_id=str(user["id"]), user={"user_id": user["id"], "username": user["username"]}, request=request)

    return {
        "success": True,
        "message": "सफलतापूर्वक लगइन भयो।",
        "token": token,
        "redirect_url": redirect_url,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name_ne": user["full_name_ne"],
            "teacher_id": user["teacher_id"],
            "phone": user["phone"]
        }
    }

@router.post("/logout")
def api_logout(request: Request, response: Response):
    user = get_current_user(request)
    token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        del SESSIONS[token]

    response.delete_cookie("session_token")
    response.delete_cookie("parent_session")
    if user:
        log_audit("LOGOUT", "AUTH", user=user, request=request)

    return {"success": True, "message": "सफलतापूर्वक लगआउट भयो।"}

@router.get("/me")
def api_me(request: Request):
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}

# ==========================================
# ADMIN REGISTRATIONS MANAGEMENT ENDPOINTS
# ==========================================

def require_admin_role(request: Request):
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "PRINCIPAL", "VICE_PRINCIPAL", "ADMIN"]:
        raise HTTPException(status_code=403, detail="यो कार्य गर्न प्रमुख एडमिन वा व्यवस्थापकको अधिकार आवश्यक छ।")
    return user

@router.get("/registrations")
def list_registrations(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user_type: Optional[str] = Query(None)
):
    """List all registrations for Super Admin review."""
    require_admin_role(request)
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT r.*, u.full_name_ne as reviewer_name
        FROM user_registrations r
        LEFT JOIN users u ON r.reviewed_by = u.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)
    if user_type:
        query += " AND r.user_type = ?"
        params.append(user_type.upper())

    query += " ORDER BY r.id DESC"
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(items), "registrations": items}

@router.post("/registrations/{reg_id}/approve")
def approve_registration(reg_id: int, request: Request):
    """
    Super Admin approval of Student or Teacher registration.
    Creates and activates the user account in users table.
    """
    admin_user = require_admin_role(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_registrations WHERE id = ?", (reg_id,))
    reg = cursor.fetchone()
    if not reg:
        conn.close()
        raise HTTPException(status_code=404, detail="दर्ता रेकर्ड फेला परेन।")

    reg_dict = dict(reg)
    user_type = reg_dict["user_type"].upper()
    phone = reg_dict["phone"]
    full_name_ne = reg_dict["full_name_ne"]
    pwd_hash = reg_dict["password_hash"]

    # 1. Update registration status
    cursor.execute("""
        UPDATE user_registrations 
        SET status = 'स्वीकृत', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (admin_user["user_id"], reg_id))

    # 2. Create or activate in users table
    role = "STUDENT" if user_type == "STUDENT" else ("TEACHER" if user_type == "TEACHER" else "PARENT")
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR phone = ?", (phone, phone))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE users SET status = 'ACTIVE', role = ?, password_hash = ?, full_name_ne = ?
            WHERE id = ?
        """, (role, pwd_hash, full_name_ne, existing["id"]))
    else:
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name_ne, phone, role, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (phone, pwd_hash, full_name_ne, phone, role))

    # 3. If student, also ensure matching entry in students table if not exists
    if user_type == "STUDENT" and reg_dict.get("class_id") and reg_dict.get("roll_no"):
        cursor.execute("""
            SELECT id FROM students WHERE class_id = ? AND roll_no = ?
        """, (reg_dict["class_id"], reg_dict["roll_no"]))
        stu_row = cursor.fetchone()
        if not stu_row:
            # Generate temporary student_id and admission_no
            curr_year = datetime.now().year
            stu_id_str = f"STU-{reg_dict['class_id']}-{reg_dict['roll_no']}-{reg_id}"
            cursor.execute("""
                INSERT INTO students (
                    student_id, admission_no, name_nepali, name_english, gender,
                    date_of_birth, class_id, roll_no, address, guardian_name,
                    guardian_relation, guardian_phone, academic_year_id, status
                ) VALUES (?, ?, ?, ?, 'अन्य', '२०६५-०१-०१', ?, ?, 'इटहरी-१९, सुनसरी', ?, 'अभिभावक', ?, 1, 'सक्रिय')
            """, (
                stu_id_str, stu_id_str, full_name_ne, full_name_ne,
                reg_dict["class_id"], reg_dict["roll_no"],
                reg_dict.get("guardian_name") or "अभिभावक",
                reg_dict.get("guardian_phone") or phone
            ))

    conn.commit()
    conn.close()

    log_audit("APPROVE_REGISTRATION", "AUTH", record_id=str(reg_id), user=admin_user, request=request)

    return {
        "success": True,
        "message": f"{full_name_ne} ({user_type}) को खाता सफलतापूर्वक स्वीकृत गरियो।"
    }

@router.post("/registrations/{reg_id}/reject")
def reject_registration(reg_id: int, request: Request):
    """Super Admin rejection / cancellation of registration."""
    admin_user = require_admin_role(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, full_name_ne, phone FROM user_registrations WHERE id = ?", (reg_id,))
    reg = cursor.fetchone()
    if not reg:
        conn.close()
        raise HTTPException(status_code=404, detail="दर्ता रेकर्ड फेला परेन।")

    cursor.execute("""
        UPDATE user_registrations 
        SET status = 'अस्वीकृत', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (admin_user["user_id"], reg_id))

    # Deactivate in users table so rejected user cannot log in
    phone = reg["phone"]
    cursor.execute("""
        UPDATE users 
        SET status = 'INACTIVE' 
        WHERE (username = ? OR phone = ?) AND role NOT IN ('SUPER_ADMIN', 'ADMIN')
    """, (phone, phone))

    conn.commit()
    conn.close()

    log_audit("REJECT_REGISTRATION", "AUTH", record_id=str(reg_id), user=admin_user, request=request)

    return {"success": True, "message": f"{reg['full_name_ne']} को खाता/दर्ता आवेदन रद्द (अस्वीकृत) गरियो।"}

@router.delete("/registrations/{reg_id}")
def delete_registration(reg_id: int, request: Request):
    """Delete a registration record completely."""
    admin_user = require_admin_role(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, phone, full_name_ne FROM user_registrations WHERE id = ?", (reg_id,))
    reg = cursor.fetchone()
    if not reg:
        conn.close()
        raise HTTPException(status_code=404, detail="दर्ता रेकर्ड फेला परेन।")

    phone = reg["phone"]
    cursor.execute("DELETE FROM user_registrations WHERE id = ?", (reg_id,))
    cursor.execute("""
        DELETE FROM users 
        WHERE (username = ? OR phone = ?) AND role NOT IN ('SUPER_ADMIN', 'ADMIN')
    """, (phone, phone))

    conn.commit()
    conn.close()

    log_audit("DELETE_REGISTRATION", "AUTH", record_id=str(reg_id), user=admin_user, request=request)

    return {"success": True, "message": f"{reg['full_name_ne']} को दर्ता विवरण सफलतापूर्वक मेटाइयो (Deleted)।"}
