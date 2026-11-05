import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.database import get_db
from app.auth import require_role, require_auth, hash_password
from app.utils.audit import log_audit
from app.utils.excel_handler import (
    export_facilities_to_excel,
    export_hostels_to_excel,
    export_transport_to_excel
)

router = APIRouter(prefix="/api", tags=["misc"])

# Universal Upload directory
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    UPLOAD_DIR = Path("/tmp/static/uploads")
else:
    UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"

try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

ALLOWED_UPLOAD_EXTS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".zip"
}
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

@router.post("/upload")
async def universal_upload(request: Request, file: UploadFile = File(...)):
    """Universal document & media file uploader for Admin panel."""
    require_auth(request)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य फाइल प्रकार ({ext})। केवल PDF, Word, Excel, Images, CSV वा ZIP फाइलहरू अनुमति छ।"
        )
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="फाइल साइज २५ MB भन्दा बढी हुन सक्दैन।")
    
    clean_name = "".join(c for c in file.filename if c.isalnum() or c in "._-").strip()
    unique_name = f"{uuid.uuid4().hex[:10]}_{clean_name}"
    file_path = UPLOAD_DIR / unique_name
    with open(file_path, "wb") as f:
        f.write(contents)
        
    return {
        "success": True,
        "url": f"/static/uploads/{unique_name}",
        "filename": file.filename,
        "size": len(contents)
    }

# --- DASHBOARD STATS ---
@router.get("/stats")
def get_dashboard_stats(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    
    # Total students
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय'")
    total_students = cursor.fetchone()[0]
    
    # Residential students
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय' AND residential_status = 'आवासीय'")
    residential_students = cursor.fetchone()[0]
    
    # Total teachers
    cursor.execute("SELECT COUNT(*) FROM teachers WHERE status = 'सक्रिय'")
    total_teachers = cursor.fetchone()[0]
    
    # Total staff
    cursor.execute("SELECT COUNT(*) FROM staff WHERE status = 'सक्रिय'")
    total_staff = cursor.fetchone()[0]
    
    # Total classes
    cursor.execute("SELECT COUNT(*) FROM classes")
    total_classes = cursor.fetchone()[0]
    
    # Today attendance
    today = date.today().isoformat()
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as absent
        FROM attendance WHERE attendance_date = ?
    """, (today,))
    att_row = cursor.fetchone()
    today_present = att_row["present"] or 0
    today_absent = att_row["absent"] or 0
    
    # New admissions count
    cursor.execute("SELECT COUNT(*) FROM admission_applications WHERE status = 'नयाँ'")
    new_admissions = cursor.fetchone()[0]
    
    # Students by class
    cursor.execute("""
        SELECT c.class_name_ne, COUNT(s.id) as count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        GROUP BY c.id
        ORDER BY c.class_numeric ASC
    """)
    students_by_class = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total_students": total_students,
        "residential_students": residential_students,
        "day_students": total_students - residential_students,
        "total_teachers": total_teachers,
        "total_staff": total_staff,
        "total_classes": total_classes,
        "today_present": today_present,
        "today_absent": today_absent,
        "new_admissions": new_admissions,
        "students_by_class": students_by_class
    }

# --- SETTINGS ---
class SchoolSettingsUpdate(BaseModel):
    name_ne: str
    name_en: str
    tagline_ne: Optional[str] = None
    tagline_en: Optional[str] = None
    address_ne: str
    address_en: str
    established_ne: str
    established_en: str
    phone: str
    notice_board_phone: Optional[str] = None
    email: str
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    about_text_ne: Optional[str] = None

@router.get("/settings")
def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

@router.put("/settings")
def update_settings(data: SchoolSettingsUpdate, request: Request):
    user = require_role("SUPER_ADMIN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE school_settings SET
            name_ne = ?, name_en = ?, tagline_ne = ?, tagline_en = ?,
            address_ne = ?, address_en = ?, established_ne = ?, established_en = ?,
            phone = ?, notice_board_phone = ?, email = ?, facebook_url = ?,
            youtube_url = ?, about_text_ne = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (
        data.name_ne, data.name_en, data.tagline_ne, data.tagline_en,
        data.address_ne, data.address_en, data.established_ne, data.established_en,
        data.phone, data.notice_board_phone, data.email, data.facebook_url,
        data.youtube_url, data.about_text_ne
    ))
    conn.commit()
    conn.close()
    log_audit("UPDATE_SETTINGS", "SETTINGS", new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "विद्यालयको सेटिङ सफलतापूर्वक सुरक्षित भयो।"}

# --- AUDIT LOGS ---
@router.get("/audit-logs")
def get_audit_logs(request: Request, limit: int = 100):
    require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"logs": logs}

# --- HOSTELS ---
class HostelCreate(BaseModel):
    name_ne: str
    name_en: Optional[str] = None
    capacity: int
    gender_type: str = "छात्र"
    warden_name: Optional[str] = None
    warden_phone: Optional[str] = None
    status: Optional[str] = "सक्रिय"

class RoomCreate(BaseModel):
    hostel_id: int
    room_number: str
    capacity: int = 4
    status: Optional[str] = "सक्रिय"

@router.get("/hostels")
def list_hostels():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hostels")
    hostels = [dict(h) for h in cursor.fetchall()]
    for h in hostels:
        cursor.execute("SELECT * FROM hostel_rooms WHERE hostel_id = ?", (h["id"],))
        h["rooms"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"hostels": hostels}

@router.post("/hostels")
def create_hostel(data: HostelCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "WARDEN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hostels (name_ne, name_en, capacity, gender_type, warden_name, warden_phone, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.name_ne, data.name_en, data.capacity, data.gender_type, data.warden_name, data.warden_phone, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "HOSTELS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "छात्रावास सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/hostels/{id}")
def update_hostel(id: int, data: HostelCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "WARDEN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE hostels SET
            name_ne = ?, name_en = ?, capacity = ?, gender_type = ?,
            warden_name = ?, warden_phone = ?, status = ?
        WHERE id = ?
    """, (data.name_ne, data.name_en, data.capacity, data.gender_type, data.warden_name, data.warden_phone, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "HOSTELS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "छात्रावास विवरण अद्यावधिक भयो।"}

@router.delete("/hostels/{id}")
def delete_hostel(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hostel_rooms WHERE hostel_id = ?", (id,))
    cursor.execute("DELETE FROM hostels WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "HOSTELS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "छात्रावास सफलतापूर्वक हटाइयो।"}

@router.post("/hostels/rooms")
def create_hostel_room(data: RoomCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "WARDEN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hostel_rooms (hostel_id, room_number, capacity, status)
        VALUES (?, ?, ?, ?)
    """, (data.hostel_id, data.room_number, data.capacity, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "message": "कोठा सफलतापूर्वक थपियो।", "id": new_id}

@router.delete("/hostels/rooms/{id}")
def delete_hostel_room(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "WARDEN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hostel_rooms WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "कोठा हटाइयो।"}

@router.get("/hostels/export")
def export_hostels_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hostels")
    hostels = [dict(h) for h in cursor.fetchall()]
    conn.close()
    stream = export_hostels_to_excel(hostels)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hostels_data.xlsx"}
    )

# --- BUSES / TRANSPORT ---
class BusCreate(BaseModel):
    bus_number: str
    vehicle_number: str
    route_name: str
    driver_name: str
    driver_phone: str
    capacity: int = 35
    status: Optional[str] = "सक्रिय"

@router.get("/transport")
def list_transport():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buses")
    buses = [dict(b) for b in cursor.fetchall()]
    conn.close()
    return {"buses": buses}

@router.post("/transport")
def create_bus(data: BusCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO buses (bus_number, vehicle_number, route_name, driver_name, driver_phone, capacity, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.bus_number, data.vehicle_number, data.route_name, data.driver_name, data.driver_phone, data.capacity, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "TRANSPORT", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "बस सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/transport/{id}")
def update_bus(id: int, data: BusCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE buses SET
            bus_number = ?, vehicle_number = ?, route_name = ?,
            driver_name = ?, driver_phone = ?, capacity = ?, status = ?
        WHERE id = ?
    """, (data.bus_number, data.vehicle_number, data.route_name, data.driver_name, data.driver_phone, data.capacity, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "TRANSPORT", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "बस विवरण अद्यावधिक भयो।"}

@router.delete("/transport/{id}")
def delete_bus(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM buses WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "TRANSPORT", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "बस सफलतापूर्वक हटाइयो।"}

@router.get("/transport/export")
def export_transport_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buses")
    buses = [dict(b) for b in cursor.fetchall()]
    conn.close()
    stream = export_transport_to_excel(buses)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=transport_data.xlsx"}
    )

# --- FACILITIES ---
class FacilityCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    icon: Optional[str] = "check-circle-2"
    image: Optional[str] = "/static/images/hero-banner.jpg"
    display_order: Optional[int] = 1
    status: Optional[str] = "सक्रिय"

@router.get("/facilities")
def list_facilities():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, title as title_ne, description as description_ne, display_order as order_index FROM facilities ORDER BY display_order ASC")
    facilities = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return {"facilities": facilities}

@router.post("/facilities")
def create_facility(data: FacilityCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO facilities (title, description, icon, image, display_order, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data.title, data.description, data.icon, data.image, data.display_order, data.status))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "FACILITIES", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "सुविधा सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/facilities/{id}")
def update_facility(id: int, data: FacilityCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE facilities SET
            title = ?, description = ?, icon = ?, image = ?,
            display_order = ?, status = ?
        WHERE id = ?
    """, (data.title, data.description, data.icon, data.image, data.display_order, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "FACILITIES", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "सुविधा विवरण अद्यावधिक भयो।"}

@router.delete("/facilities/{id}")
def delete_facility(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facilities WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "FACILITIES", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "सुविधा हटाइयो।"}

@router.get("/facilities/export")
def export_facilities_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facilities ORDER BY display_order ASC")
    facilities = [dict(f) for f in cursor.fetchall()]
    conn.close()
    stream = export_facilities_to_excel(facilities)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=facilities_data.xlsx"}
    )
