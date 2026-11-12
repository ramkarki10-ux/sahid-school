from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.excel_handler import generate_alumni_template, parse_alumni_excel, export_alumni_to_excel
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/alumni", tags=["alumni"])

class AlumniCreate(BaseModel):
    full_name: str
    passed_class: str # 'कक्षा १०' वा 'कक्षा १२'
    pass_out_year: str # उदा: २०८०
    address: Optional[str] = ""
    phone: Optional[str] = ""
    symbol_no: Optional[str] = ""
    photo: Optional[str] = None
    current_status: Optional[str] = ""
    remarks: Optional[str] = ""

class AlumniUpdate(BaseModel):
    full_name: Optional[str] = None
    passed_class: Optional[str] = None
    pass_out_year: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    symbol_no: Optional[str] = None
    photo: Optional[str] = None
    current_status: Optional[str] = None
    remarks: Optional[str] = None

@router.get("")
def list_alumni(
    passed_class: Optional[str] = None,
    pass_out_year: Optional[str] = None,
    search: Optional[str] = None
):
    """Public or Admin listing of passed out students."""
    if not isinstance(passed_class, str):
        passed_class = None
    if not isinstance(pass_out_year, str):
        pass_out_year = None
    if not isinstance(search, str):
        search = None

    conn = get_db()
    cursor = conn.cursor()

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
    alumni = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(alumni), "alumni": alumni}

@router.post("")
def create_alumni(req: AlumniCreate, request: Request):
    """Super Admin or Admin creates a new alumni record."""
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई पूर्व विद्यार्थी थप्ने अनुमति छैन।")

    name = req.full_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="विद्यार्थीको नाम अनिवार्य छ।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alumni (full_name, passed_class, pass_out_year, address, phone, symbol_no, photo, current_status, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        req.passed_class.strip(),
        req.pass_out_year.strip(),
        (req.address or "").strip(),
        (req.phone or "").strip(),
        (req.symbol_no or "").strip(),
        req.photo,
        (req.current_status or "").strip(),
        (req.remarks or "").strip()
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit("CREATE", "ALUMNI", record_id=str(new_id), user=user, request=request)

    return {"success": True, "message": "पूर्व विद्यार्थी सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/{alumni_id}")
def update_alumni(alumni_id: int, req: AlumniUpdate, request: Request):
    """Super Admin or Admin edits an existing alumni record."""
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई यो विवरण संसोधन गर्ने अनुमति छैन।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alumni WHERE id = ?", (alumni_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="पूर्व विद्यार्थी फेला परेन।")

    item_dict = dict(item)
    full_name = req.full_name if req.full_name is not None else item_dict["full_name"]
    passed_class = req.passed_class if req.passed_class is not None else item_dict["passed_class"]
    pass_out_year = req.pass_out_year if req.pass_out_year is not None else item_dict["pass_out_year"]
    address = req.address if req.address is not None else item_dict["address"]
    phone = req.phone if req.phone is not None else item_dict["phone"]
    symbol_no = req.symbol_no if req.symbol_no is not None else item_dict["symbol_no"]
    photo = req.photo if req.photo is not None else item_dict["photo"]
    current_status = req.current_status if req.current_status is not None else item_dict["current_status"]
    remarks = req.remarks if req.remarks is not None else item_dict["remarks"]

    cursor.execute("""
        UPDATE alumni
        SET full_name = ?, passed_class = ?, pass_out_year = ?, address = ?, phone = ?,
            symbol_no = ?, photo = ?, current_status = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (full_name, passed_class, pass_out_year, address, phone, symbol_no, photo, current_status, remarks, alumni_id))
    conn.commit()
    conn.close()

    log_audit("UPDATE", "ALUMNI", record_id=str(alumni_id), user=user, request=request)

    return {"success": True, "message": "पूर्व विद्यार्थीको विवरण सफलतापूर्वक संसोधन गरियो।"}

@router.delete("/{alumni_id}")
def delete_alumni(alumni_id: int, request: Request):
    """Super Admin or Admin deletes an alumni record."""
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई यो विवरण हटाउने अनुमति छैन।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alumni WHERE id = ?", (alumni_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="पूर्व विद्यार्थी फेला परेन।")

    cursor.execute("DELETE FROM alumni WHERE id = ?", (alumni_id,))
    conn.commit()
    conn.close()

    log_audit("DELETE", "ALUMNI", record_id=str(alumni_id), user=user, request=request)

    return {"success": True, "message": "पूर्व विद्यार्थी सफलतापूर्वक हटाइयो।"}

@router.get("/template")
def download_alumni_template():
    """Download standard Excel template for bulk alumni upload."""
    stream = generate_alumni_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=alumni_import_template.xlsx"}
    )

@router.get("/export")
def export_alumni_data(
    passed_class: Optional[str] = None,
    pass_out_year: Optional[str] = None
):
    """Export alumni records to Excel."""
    if not isinstance(passed_class, str):
        passed_class = None
    if not isinstance(pass_out_year, str):
        pass_out_year = None

    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM alumni WHERE 1=1"
    params = []
    if passed_class:
        query += " AND passed_class = ?"
        params.append(passed_class)
    if pass_out_year:
        query += " AND pass_out_year = ?"
        params.append(pass_out_year)
    query += " ORDER BY pass_out_year DESC, passed_class DESC, id DESC"
    cursor.execute(query, params)
    alumni_list = [dict(r) for r in cursor.fetchall()]
    conn.close()

    stream = export_alumni_to_excel(alumni_list)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=alumni_records.xlsx"}
    )

@router.post("/upload-excel")
async def upload_alumni_excel(file: UploadFile = File(...), request: Request = None):
    """Super Admin or Admin uploads Excel file to bulk import alumni."""
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="तपाईंलाई Excel अपलोड गर्ने अनुमति छैन।")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="कृपया .xlsx वा .xls ढाँचाको Excel फाइल अपलोड गर्नुहोस्।")

    content = await file.read()
    valid_records, errors = parse_alumni_excel(content)

    if not valid_records:
        raise HTTPException(
            status_code=400,
            detail=f"Excel बाट कुनै मान्य रेकर्ड फेला परेन। त्रुटिहरू: {', '.join(errors[:3])}"
        )

    conn = get_db()
    cursor = conn.cursor()
    inserted_count = 0

    for r in valid_records:
        cursor.execute("""
            INSERT INTO alumni (full_name, passed_class, pass_out_year, address, phone, symbol_no, current_status, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["full_name"],
            r["passed_class"],
            r["pass_out_year"],
            r.get("address", ""),
            r.get("phone", ""),
            r.get("symbol_no", ""),
            r.get("current_status", ""),
            r.get("remarks", "")
        ))
        inserted_count += 1

    conn.commit()
    conn.close()

    log_audit("EXCEL_IMPORT", "ALUMNI", record_id=f"count:{inserted_count}", user=user, request=request)

    return {
        "success": True,
        "message": f"सफलतापूर्वक {inserted_count} जना पूर्व विद्यार्थीहरूको विवरण Excel बाट आयात गरियो।",
        "inserted_count": inserted_count,
        "warnings": errors
    }
