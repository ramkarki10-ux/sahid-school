from fastapi import APIRouter, Request, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io
import openpyxl
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit
from app.utils.excel_handler import generate_teacher_template, export_teachers_to_excel, TEACHER_EXCEL_COLUMNS

router = APIRouter(prefix="/api/teachers", tags=["teachers"])

class TeacherCreate(BaseModel):
    employee_id: str
    name_nepali: str
    name_english: str
    photo: Optional[str] = None
    position: str
    subject: str
    level: str
    qualification: Optional[str] = None
    experience: Optional[str] = None
    phone: str
    email: Optional[str] = None
    appointment_date: Optional[str] = None
    employment_type: Optional[str] = "स्थायी"
    academic_year_id: Optional[int] = None
    status: Optional[str] = "सक्रिय"
    remarks: Optional[str] = None

class TeacherAssignmentCreate(BaseModel):
    teacher_id: int
    academic_year_id: int
    class_id: int
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    is_class_teacher: Optional[int] = 0

class TeacherAssignmentUpdate(BaseModel):
    teacher_id: int
    academic_year_id: Optional[int] = 1
    class_id: int
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    is_class_teacher: Optional[int] = 0

@router.get("")
def list_teachers(
    subject: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None)
):
    subject = subject if isinstance(subject, str) and subject.strip() else None
    level = level if isinstance(level, str) and level.strip() else None
    status_filter = status_filter if isinstance(status_filter, str) and status_filter.strip() else None
    search = search if isinstance(search, str) and search.strip() else None

    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM teachers WHERE 1=1"
    params = []
    
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if level:
        query += " AND level = ?"
        params.append(level)
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if search:
        s = f"%{search.strip()}%"
        query += " AND (name_nepali LIKE ? OR name_english LIKE ? OR employee_id LIKE ? OR phone LIKE ?)"
        params.extend([s, s, s, s])
        
    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    raw_teachers = [dict(r) for r in cursor.fetchall()]
    conn.close()

    teachers = []
    for t in raw_teachers:
        item = dict(t)
        photo = item.get("photo")
        if photo and not str(photo).startswith("data:image/") and not str(photo).startswith("http://") and not str(photo).startswith("https://"):
            item["photo"] = f"https://sahid-school.vercel.app/{str(photo).lstrip('/')}"
        item["avatar_url"] = item.get("photo") or "https://sahid-school.vercel.app/static/images/default_avatar.png"
        pos = item.get("position") or item.get("designation") or "शिक्षक"
        item["position"] = pos
        item["designation"] = pos
        teachers.append(item)

    return {"teachers": teachers, "total": len(teachers)}

@router.get("/template")
def download_teacher_template():
    excel_stream = generate_teacher_template()
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=teacher_import_template.xlsx"}
    )

@router.post("/import")
async def import_teachers(request: Request, file: UploadFile = File(...)):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    
    headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
    header_idx = {h: idx for idx, h in enumerate(headers)}
    
    conn = get_db()
    cursor = conn.cursor()
    imported = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        emp_id = str(row[header_idx.get("Employee ID", 0)] or "").strip()
        name_ne = str(row[header_idx.get("Name Nepali", 1)] or "").strip()
        name_en = str(row[header_idx.get("Name English", 2)] or "").strip()
        pos = str(row[header_idx.get("Position", 3)] or "").strip()
        sub = str(row[header_idx.get("Subject", 4)] or "").strip()
        lvl = str(row[header_idx.get("Level", 5)] or "").strip()
        qual = str(row[header_idx.get("Qualification", 6)] or "").strip()
        exp = str(row[header_idx.get("Experience", 7)] or "").strip()
        phone = str(row[header_idx.get("Phone", 8)] or "").strip()
        email = str(row[header_idx.get("Email", 9)] or "").strip()
        app_date = str(row[header_idx.get("Appointment Date", 10)] or "").strip()
        emp_type = str(row[header_idx.get("Employment Type", 11)] or "स्थायी").strip()
        stat = str(row[header_idx.get("Status", 12)] or "सक्रिय").strip()
        
        if not emp_id or not name_ne:
            continue
            
        cursor.execute("""
            INSERT OR REPLACE INTO teachers (
                employee_id, name_nepali, name_english, position, subject, level,
                qualification, experience, phone, email, appointment_date, employment_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (emp_id, name_ne, name_en, pos, sub, lvl, qual, exp, phone, email, app_date, emp_type, stat))
        imported += 1
        
    conn.commit()
    conn.close()
    log_audit("EXCEL_IMPORT", "TEACHERS", new_value={"count": imported}, user=user, request=request)
    return {"success": True, "message": f"सफलतापूर्वक {imported} शिक्षक आयात गरियो।"}

@router.get("/export")
def export_teachers_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers ORDER BY id ASC")
    teachers = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_teachers_to_excel(teachers)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=teachers_data.xlsx"}
    )

@router.get("/{id}")
def get_teacher(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE id = ?", (id,))
    t = cursor.fetchone()
    if not t:
        conn.close()
        raise HTTPException(status_code=404, detail="शिक्षक फेला परेन।")
    teacher_dict = dict(t)
    
    # Assignments
    cursor.execute("""
        SELECT tca.*, c.class_name_ne, sec.name as section_name, s.subject_name_ne
        FROM teacher_class_assignments tca
        LEFT JOIN classes c ON tca.class_id = c.id
        LEFT JOIN sections sec ON tca.section_id = sec.id
        LEFT JOIN subjects s ON tca.subject_id = s.id
        WHERE tca.teacher_id = ?
    """, (id,))
    teacher_dict["assignments"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return teacher_dict

@router.post("")
def create_teacher(data: TeacherCreate, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM teachers WHERE employee_id = ?", (data.employee_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="यो Employee ID पहिले नै दर्ता छ।")
        
    cursor.execute("""
        INSERT INTO teachers (
            employee_id, name_nepali, name_english, photo, position, subject, level,
            qualification, experience, phone, email, appointment_date, employment_type,
            academic_year_id, status, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.employee_id, data.name_nepali, data.name_english, data.photo, data.position,
        data.subject, data.level, data.qualification, data.experience, data.phone,
        data.email, data.appointment_date, data.employment_type, data.academic_year_id,
        data.status, data.remarks
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_audit("CREATE", "TEACHERS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "शिक्षक विवरण सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/{id}")
def update_teacher(id: int, data: TeacherCreate, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="शिक्षक फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("""
        UPDATE teachers SET
            employee_id = ?, name_nepali = ?, name_english = ?, photo = ?, position = ?,
            subject = ?, level = ?, qualification = ?, experience = ?, phone = ?,
            email = ?, appointment_date = ?, employment_type = ?, status = ?,
            remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.employee_id, data.name_nepali, data.name_english, data.photo, data.position,
        data.subject, data.level, data.qualification, data.experience, data.phone,
        data.email, data.appointment_date, data.employment_type, data.status,
        data.remarks, id
    ))
    conn.commit()
    conn.close()
    
    log_audit("UPDATE", "TEACHERS", record_id=str(id), old_value=old_val, new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "शिक्षक विवरण सफलतापूर्वक अद्यावधिक भयो।"}

@router.delete("/{id}")
def delete_teacher(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="शिक्षक फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("DELETE FROM teachers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    log_audit("DELETE", "TEACHERS", record_id=str(id), old_value=old_val, user=user, request=request)
    return {"success": True, "message": "शिक्षक विवरण सफलतापूर्वक मेटाइयो।"}

# Teacher class assignment endpoints (Section 27 & 53)
@router.get("/assignments/all")
def get_all_assignments(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tca.*, t.name_nepali as teacher_name, t.employee_id,
               c.class_name_ne, sec.name as section_name, s.subject_name_ne
        FROM teacher_class_assignments tca
        JOIN teachers t ON tca.teacher_id = t.id
        JOIN classes c ON tca.class_id = c.id
        LEFT JOIN sections sec ON tca.section_id = sec.id
        LEFT JOIN subjects s ON tca.subject_id = s.id
        ORDER BY c.class_numeric ASC, sec.name ASC
    """)
    assignments = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"assignments": assignments}

@router.post("/assignments")
def assign_teacher_class(data: TeacherAssignmentCreate, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO teacher_class_assignments (teacher_id, academic_year_id, class_id, section_id, subject_id, is_class_teacher)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data.teacher_id, data.academic_year_id, data.class_id, data.section_id, data.subject_id, data.is_class_teacher))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_audit("ASSIGN_TEACHER_CLASS", "TEACHER_ASSIGNMENT", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "शिक्षकलाई कक्षा सफलतापूर्वक बाँडफाँड गरियो।", "id": new_id}

@router.put("/assignments/{id}")
def update_teacher_assignment(id: int, data: TeacherAssignmentUpdate, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE teacher_class_assignments 
        SET teacher_id = ?, 
            class_id = ?, 
            section_id = ?, 
            subject_id = ?, 
            is_class_teacher = ?
        WHERE id = ?
    """, (data.teacher_id, data.class_id, data.section_id, data.subject_id, data.is_class_teacher, id))
    conn.commit()
    conn.close()
    
    log_audit("UPDATE_TEACHER_CLASS", "TEACHER_ASSIGNMENT", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "कक्षा बाँडफाँड विवरण सफलतापूर्वक संसोधन गरियो।"}

@router.delete("/assignments/{id}")
def delete_teacher_assignment(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teacher_class_assignments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE_TEACHER_CLASS", "TEACHER_ASSIGNMENT", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "कक्षा बाँडफाँड मेटाइयो।"}
