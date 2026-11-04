from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit
from app.utils.excel_handler import export_staff_to_excel

router = APIRouter(prefix="/api/staff", tags=["staff"])

class StaffCreate(BaseModel):
    employee_id: str
    name_nepali: str
    name_english: str
    photo: Optional[str] = None
    position: str
    department: str
    qualification: Optional[str] = None
    phone: str
    email: Optional[str] = None
    appointment_date: Optional[str] = None
    employment_type: Optional[str] = "स्थायी"
    status: Optional[str] = "सक्रिय"
    remarks: Optional[str] = None

@router.get("")
def list_staff(
    department: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None)
):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM staff WHERE 1=1"
    params = []
    if department:
        query += " AND department = ?"
        params.append(department)
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if search:
        s = f"%{search.strip()}%"
        query += " AND (name_nepali LIKE ? OR name_english LIKE ? OR employee_id LIKE ? OR phone LIKE ?)"
        params.extend([s, s, s, s])
        
    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    staff_members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"staff": staff_members, "total": len(staff_members)}

@router.get("/export")
def export_staff_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff ORDER BY id ASC")
    staff_members = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_staff_to_excel(staff_members)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=staff_data.xlsx"}
    )

@router.get("/{id}")
def get_staff(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE id = ?", (id,))
    s = cursor.fetchone()
    conn.close()
    if not s:
        raise HTTPException(status_code=404, detail="कर्मचारी फेला परेन।")
    return dict(s)

@router.post("")
def create_staff(data: StaffCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM staff WHERE employee_id = ?", (data.employee_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="यो Employee ID पहिले नै दर्ता छ।")
        
    cursor.execute("""
        INSERT INTO staff (
            employee_id, name_nepali, name_english, photo, position, department,
            qualification, phone, email, appointment_date, employment_type, status, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.employee_id, data.name_nepali, data.name_english, data.photo, data.position,
        data.department, data.qualification, data.phone, data.email, data.appointment_date,
        data.employment_type, data.status, data.remarks
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "STAFF", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "कर्मचारी विवरण सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/{id}")
def update_staff(id: int, data: StaffCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="कर्मचारी फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("""
        UPDATE staff SET
            employee_id = ?, name_nepali = ?, name_english = ?, photo = ?, position = ?,
            department = ?, qualification = ?, phone = ?, email = ?, appointment_date = ?,
            employment_type = ?, status = ?, remarks = ?
        WHERE id = ?
    """, (
        data.employee_id, data.name_nepali, data.name_english, data.photo, data.position,
        data.department, data.qualification, data.phone, data.email, data.appointment_date,
        data.employment_type, data.status, data.remarks, id
    ))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "STAFF", record_id=str(id), old_value=old_val, new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "कर्मचारी विवरण सफलतापूर्वक अद्यावधिक भयो।"}

@router.delete("/{id}")
def delete_staff(id: int, request: Request):
    user = require_role("SUPER_ADMIN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="कर्मचारी फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("DELETE FROM staff WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "STAFF", record_id=str(id), old_value=old_val, user=user, request=request)
    return {"success": True, "message": "कर्मचारी विवरण मेटाइयो।"}
