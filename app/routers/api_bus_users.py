import math
import io
import csv
from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.excel_handler import generate_bus_users_template, parse_bus_users_file, export_bus_users_to_excel
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/bus-users", tags=["bus_users"])

class BusUserCreate(BaseModel):
    student_name: str
    address: str
    guardian_name: str
    contact_number: str
    bus_stop: str
    bus_number: Optional[str] = "बस नं. १ (को १ ख २०६६)"
    class_name: Optional[str] = ""
    status: Optional[str] = "सक्रिय"
    remarks: Optional[str] = ""

class BusUserUpdate(BaseModel):
    student_name: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    contact_number: Optional[str] = None
    bus_stop: Optional[str] = None
    bus_number: Optional[str] = None
    class_name: Optional[str] = None
    status: Optional[str] = None
    remarks: Optional[str] = None

@router.get("")
def list_bus_users(
    q: Optional[str] = None,
    bus_stop: Optional[str] = None,
    bus_number: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """List bus users with search, filtering, and pagination."""
    if not isinstance(q, str):
        q = None
    if not isinstance(bus_stop, str):
        bus_stop = None
    if not isinstance(bus_number, str):
        bus_number = None

    conn = get_db()
    cursor = conn.cursor()

    # Get unique bus stops and bus numbers for filter dropdowns
    cursor.execute("SELECT DISTINCT bus_stop FROM bus_users WHERE bus_stop IS NOT NULL AND bus_stop != '' ORDER BY bus_stop ASC")
    bus_stops = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT bus_number FROM bus_users WHERE bus_number IS NOT NULL AND bus_number != '' ORDER BY bus_number ASC")
    bus_numbers = [r[0] for r in cursor.fetchall()]

    # Build filtered query
    where_clauses = ["1=1"]
    params = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(student_name LIKE ? OR address LIKE ? OR guardian_name LIKE ? OR contact_number LIKE ? OR bus_stop LIKE ? OR bus_number LIKE ? OR class_name LIKE ?)")
        params.extend([term, term, term, term, term, term, term])

    if bus_stop and bus_stop.strip():
        where_clauses.append("bus_stop = ?")
        params.append(bus_stop.strip())

    if bus_number and bus_number.strip():
        where_clauses.append("bus_number = ?")
        params.append(bus_number.strip())

    where_sql = " AND ".join(where_clauses)

    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM bus_users WHERE {where_sql}", params)
    total = cursor.fetchone()[0]

    # Pagination
    limit = max(1, min(page_size, 100))
    offset = max(0, (page - 1) * limit)
    total_pages = max(1, math.ceil(total / limit))

    cursor.execute(
        f"SELECT * FROM bus_users WHERE {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "users": rows,
        "bus_stops": bus_stops,
        "bus_numbers": bus_numbers
    }

@router.get("/{user_id}")
def get_bus_user(user_id: int):
    """Retrieve single bus user record."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bus_users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="बस प्रयोगकर्ता फेला परेन।")
    return {"success": True, "user": dict(row)}

@router.post("")
def create_bus_user(payload: BusUserCreate, request: Request):
    """Add a single bus user record (Manual Entry)."""
    user = require_auth(request)
    if user.get("role") not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई यो कार्य गर्ने अनुमति छैन।")

    name = payload.student_name.strip()
    addr = payload.address.strip()
    guardian = payload.guardian_name.strip()
    contact = payload.contact_number.strip()
    stop = payload.bus_stop.strip()

    if not name or not addr or not contact or not stop:
        raise HTTPException(status_code=400, detail="विद्यार्थीको नाम, ठेगाना, सम्पर्क र वस चढ्ने स्थान अनिवार्य छन्।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bus_users (student_name, address, guardian_name, contact_number, bus_stop, bus_number, class_name, status, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        addr,
        guardian or "अभिभावक",
        contact,
        stop,
        payload.bus_number.strip() if payload.bus_number else "बस नं. १ (को १ ख २०६६)",
        (payload.class_name or "").strip(),
        payload.status or "सक्रिय",
        (payload.remarks or "").strip()
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit("CREATE", "BUS_USERS", record_id=str(new_id), user=user, request=request)

    return {
        "success": True,
        "id": new_id,
        "message": f"विद्यार्थी '{name}' को बस प्रयोगकर्ता विवरण सफलतापूर्वक सुरक्षित भयो।"
    }

@router.put("/{user_id}")
def update_bus_user(user_id: int, payload: BusUserUpdate, request: Request):
    """Update existing bus user record."""
    user = require_auth(request)
    if user.get("role") not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई यो कार्य गर्ने अनुमति छैन।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bus_users WHERE id = ?", (user_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        raise HTTPException(status_code=404, detail="बस प्रयोगकर्ता फेला परेन।")

    c_dict = dict(current)
    new_name = payload.student_name.strip() if payload.student_name is not None else c_dict["student_name"]
    new_addr = payload.address.strip() if payload.address is not None else c_dict["address"]
    new_guardian = payload.guardian_name.strip() if payload.guardian_name is not None else c_dict["guardian_name"]
    new_contact = payload.contact_number.strip() if payload.contact_number is not None else c_dict["contact_number"]
    new_stop = payload.bus_stop.strip() if payload.bus_stop is not None else c_dict["bus_stop"]
    new_bus = payload.bus_number.strip() if payload.bus_number is not None else c_dict["bus_number"]
    new_class = payload.class_name.strip() if payload.class_name is not None else c_dict["class_name"]
    new_status = payload.status.strip() if payload.status is not None else c_dict["status"]
    new_remarks = payload.remarks.strip() if payload.remarks is not None else c_dict["remarks"]

    cursor.execute("""
        UPDATE bus_users
        SET student_name = ?, address = ?, guardian_name = ?, contact_number = ?,
            bus_stop = ?, bus_number = ?, class_name = ?, status = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        new_name, new_addr, new_guardian, new_contact, new_stop, new_bus, new_class, new_status, new_remarks, user_id
    ))
    conn.commit()
    conn.close()

    log_audit("UPDATE", "BUS_USERS", record_id=str(user_id), user=user, request=request)

    return {
        "success": True,
        "message": f"विद्यार्थी '{new_name}' को विवरण सफलतापूर्वक अद्यावधिक गरियो।"
    }

@router.delete("/{user_id}")
def delete_bus_user(user_id: int, request: Request):
    """Delete a bus user record."""
    user = require_auth(request)
    if user.get("role") not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई यो कार्य गर्ने अनुमति छैन।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT student_name FROM bus_users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="बस प्रयोगकर्ता फेला परेन।")

    s_name = row[0]
    cursor.execute("DELETE FROM bus_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    log_audit("DELETE", "BUS_USERS", record_id=str(user_id), user=user, request=request)

    return {
        "success": True,
        "message": f"विद्यार्थी '{s_name}' को बस प्रयोगकर्ता रेकर्ड सफलतापूर्वक हटाइयो।"
    }

@router.post("/upload")
async def bulk_upload_bus_users(file: UploadFile = File(...), request: Request = None):
    """Bulk import bus users from Excel (.xlsx, .xls) or CSV (.csv) file."""
    user = require_auth(request)
    if user.get("role") not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई फाइल आयात गर्ने अनुमति छैन।")

    fn = file.filename.lower()
    if not (fn.endswith(".xlsx") or fn.endswith(".xls") or fn.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="कृपया मान्य Excel (.xlsx, .xls) वा CSV (.csv) फाइल छान्नुहोस्।"
        )

    content = await file.read()
    valid_records, errors = parse_bus_users_file(content, file.filename)

    if not valid_records:
        detail_msg = "फाइलबाट कुनै मान्य रेकर्ड फेला परेन।"
        if errors:
            detail_msg += f" कारण: {'; '.join(errors[:4])}"
        raise HTTPException(status_code=400, detail=detail_msg)

    conn = get_db()
    cursor = conn.cursor()
    inserted_count = 0

    for r in valid_records:
        cursor.execute("""
            INSERT INTO bus_users (student_name, address, guardian_name, contact_number, bus_stop, bus_number, class_name, status, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["student_name"],
            r["address"],
            r["guardian_name"],
            r["contact_number"],
            r["bus_stop"],
            r.get("bus_number") or "बस नं. १ (को १ ख २०६६)",
            r.get("class_name") or "",
            r.get("status") or "सक्रिय",
            r.get("remarks") or ""
        ))
        inserted_count += 1

    conn.commit()
    conn.close()

    log_audit("EXCEL_IMPORT", "BUS_USERS", record_id=f"count:{inserted_count}", user=user, request=request)

    return {
        "success": True,
        "message": f"सफलतापूर्वक {inserted_count} जना विद्यार्थीहरूको बस विवरण आयात गरियो।",
        "inserted_count": inserted_count,
        "warnings": errors
    }

@router.get("/template")
def download_bus_users_excel_template():
    """Download standard Excel (.xlsx) template for bulk bus user upload."""
    stream = generate_bus_users_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=school_bus_users_template.xlsx"}
    )

@router.get("/template-csv")
def download_bus_users_csv_template():
    """Download standard CSV template with UTF-8 BOM for bulk bus user upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "विद्यार्थीको पूरा नाम, थर",
        "ठेगाना",
        "अभिभावकको नाम, थर",
        "सम्पर्क नम्बर",
        "वस चढ्ने स्थान (Bus Stop)",
        "बस नम्बर / रुट",
        "कक्षा",
        "कैफियत"
    ])
    writer.writerow(["रोहित कार्की", "इटहरी-१९, सुनसरी", "राम बहादुर कार्की", "9852033133", "ब्रह्मपुर चोक", "बस नं. १ (को १ ख २०६६)", "कक्षा १०", "बिहान र दिउँसो"])
    writer.writerow(["अनिता चौधरी", "इटहरी-२०, तरहरा", "सुरेश चौधरी", "9842000010", "तरहरा बजार", "बस नं. १ (को १ ख २०६६)", "कक्षा ९", "नियमित"])
    
    csv_bytes = output.getvalue().encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=school_bus_users_template.csv"}
    )

@router.get("/export")
def export_bus_users(
    q: Optional[str] = None,
    bus_stop: Optional[str] = None,
    bus_number: Optional[str] = None
):
    """Export bus users to styled Excel file."""
    if not isinstance(q, str):
        q = None
    if not isinstance(bus_stop, str):
        bus_stop = None
    if not isinstance(bus_number, str):
        bus_number = None

    conn = get_db()
    cursor = conn.cursor()

    where_clauses = ["1=1"]
    params = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(student_name LIKE ? OR address LIKE ? OR guardian_name LIKE ? OR contact_number LIKE ? OR bus_stop LIKE ? OR bus_number LIKE ? OR class_name LIKE ?)")
        params.extend([term, term, term, term, term, term, term])

    if bus_stop and bus_stop.strip():
        where_clauses.append("bus_stop = ?")
        params.append(bus_stop.strip())

    if bus_number and bus_number.strip():
        where_clauses.append("bus_number = ?")
        params.append(bus_number.strip())

    where_sql = " AND ".join(where_clauses)
    cursor.execute(f"SELECT * FROM bus_users WHERE {where_sql} ORDER BY id DESC", params)
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    stream = export_bus_users_to_excel(records)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=school_bus_users_records.xlsx"}
    )
