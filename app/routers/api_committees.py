from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit
from app.utils.excel_handler import export_committee_to_excel

router = APIRouter(prefix="/api/committees", tags=["committees"])

class CommitteeMemberCreate(BaseModel):
    name: str
    position: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    term: Optional[str] = "२०८०-२०८३"
    order_index: Optional[int] = 0
    status: Optional[str] = "सक्रिय"

class LeadershipUpdate(BaseModel):
    name: str
    position: str
    photo: Optional[str] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    message_ne: Optional[str] = None
    biography: Optional[str] = None

# --- MANAGEMENT COMMITTEE ---
@router.get("/management")
@router.get("/smc")
def list_management_committee():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_management_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"members": members}

@router.post("/management")
def create_management_member(data: CommitteeMemberCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO school_management_committee (name, position, phone, photo, term, order_index, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.name, data.position, data.phone, data.photo, data.term, data.order_index, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "MANAGEMENT_COMMITTEE", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "व्यवस्थापन समिति सदस्य सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/management/{id}")
def update_management_member(id: int, data: CommitteeMemberCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE school_management_committee SET
            name = ?, position = ?, phone = ?, photo = ?, term = ?, order_index = ?, status = ?
        WHERE id = ?
    """, (data.name, data.position, data.phone, data.photo, data.term, data.order_index, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "MANAGEMENT_COMMITTEE", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "व्यवस्थापन समिति सदस्य अद्यावधिक भयो।"}

@router.delete("/management/{id}")
def delete_management_member(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM school_management_committee WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "MANAGEMENT_COMMITTEE", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "व्यवस्थापन समिति सदस्य मेटाइयो।"}

@router.get("/management/export")
def export_management_committee_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_management_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_committee_to_excel(members, "व्यवस्थापन समिति")
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=smc_members.xlsx"}
    )

# --- TRUSTEE COMMITTEE ---
@router.get("/trustee")
def list_trustee_committee():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trustee_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"members": members}

@router.post("/trustee")
def create_trustee_member(data: CommitteeMemberCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trustee_committee (name, position, phone, photo, order_index, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data.name, data.position, data.phone, data.photo, data.order_index, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "TRUSTEE_COMMITTEE", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "गुठियार समिति सदस्य थपियो।", "id": new_id}

@router.put("/trustee/{id}")
def update_trustee_member(id: int, data: CommitteeMemberCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE trustee_committee SET
            name = ?, position = ?, phone = ?, photo = ?, order_index = ?, status = ?
        WHERE id = ?
    """, (data.name, data.position, data.phone, data.photo, data.order_index, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "TRUSTEE_COMMITTEE", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "गुठियार समिति सदस्य अद्यावधिक भयो।"}

@router.delete("/trustee/{id}")
def delete_trustee_member(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trustee_committee WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "TRUSTEE_COMMITTEE", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "गुठियार समिति सदस्य मेटाइयो।"}

@router.get("/trustee/export")
def export_trustee_committee_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trustee_committee ORDER BY order_index ASC, id ASC")
    members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_committee_to_excel(members, "गुठियार समिति")
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=trustee_members.xlsx"}
    )

# --- LEADERSHIP (Principal & Vice Principal) ---
@router.get("/leadership/{role_type}")
def get_leadership(role_type: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_leadership WHERE role_type = ?", (role_type.upper(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="विवरण फेला परेन।")
    return dict(row)

@router.put("/leadership/{role_type}")
def update_leadership(role_type: str, data: LeadershipUpdate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE school_leadership SET
            name = ?, position = ?, photo = ?, qualification = ?, experience = ?,
            phone = ?, email = ?, message_ne = ?, biography = ?, updated_at = CURRENT_TIMESTAMP
        WHERE role_type = ?
    """, (
        data.name, data.position, data.photo, data.qualification, data.experience,
        data.phone, data.email, data.message_ne, data.biography, role_type.upper()
    ))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "LEADERSHIP", record_id=role_type.upper(), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "नेतृत्व विवरण सफलतापूर्वक अद्यावधिक भयो।"}
