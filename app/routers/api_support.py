from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import io
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/support", tags=["support"])

class SupportDonationCreate(BaseModel):
    donor_name: str
    address: str
    phone: str
    email: str
    website_url: Optional[str] = None
    support_categories: List[str]
    other_category_details: Optional[str] = None
    estimated_amount: Optional[str] = None
    support_type: str
    frequency: Optional[str] = None
    duration: Optional[str] = None
    other_schools_interest: Optional[str] = None

class SupportStatusUpdate(BaseModel):
    status: str
    admin_notes: Optional[str] = None

@router.post("/donate")
def submit_support_pledge(data: SupportDonationCreate, request: Request):
    donor_name = data.donor_name.strip()
    address = data.address.strip()
    phone = data.phone.strip()
    email = data.email.strip()

    if not donor_name or not address or not phone or not email:
        raise HTTPException(
            status_code=400,
            detail="कृपया नाम, ठेगाना, सम्पर्क नम्बर र इमेल अनिवार्य रूपमा भर्नुहोस्।"
        )

    if not data.support_categories:
        raise HTTPException(
            status_code=400,
            detail="कृपया कम्तीमा एउटा सहयोग गर्न चाहेको शीर्षक छनौट गर्नुहोस्।"
        )

    categories_json = json.dumps(data.support_categories, ensure_ascii=False)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO support_donations (
            donor_name, address, phone, email, website_url,
            support_categories, other_category_details, estimated_amount,
            support_type, frequency, duration, other_schools_interest, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'नयाँ')
    """, (
        donor_name,
        address,
        phone,
        email,
        (data.website_url or "").strip() or None,
        categories_json,
        (data.other_category_details or "").strip() or None,
        (data.estimated_amount or "").strip() or None,
        data.support_type.strip(),
        (data.frequency or "").strip() or None,
        (data.duration or "").strip() or None,
        (data.other_schools_interest or "").strip() or None
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "id": new_id,
        "message": "तपाईंको सहयोगको प्रस्ताव सफलतापूर्वक प्राप्त भयो! सहिद स्मृति आवासीय माध्यमिक विद्यालयका बालबालिकाको शिक्षा र उज्यालो भविष्यका लागि तपाईंको अमूल्य सहयोगको हामी उच्च सम्मान गर्दछौं। विद्यालय प्रशासनबाट छिट्टै सम्पर्क गरिनेछ।"
    }

@router.get("/list")
def list_support_pledges(request: Request, status_filter: Optional[str] = Query(None)):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    status_clean = status_filter.strip() if isinstance(status_filter, str) and status_filter.strip() else None
    if status_clean:
        cursor.execute("SELECT * FROM support_donations WHERE status = ? ORDER BY id DESC", (status_clean,))
    else:
        cursor.execute("SELECT * FROM support_donations ORDER BY id DESC")
        
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Parse JSON categories for each row
    for r in rows:
        try:
            r["categories_list"] = json.loads(r.get("support_categories") or "[]")
        except Exception:
            r["categories_list"] = [r.get("support_categories") or ""]

    return {"donations": rows}

@router.put("/{donation_id}/status")
def update_support_status(donation_id: int, data: SupportStatusUpdate, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE support_donations 
        SET status = ?, admin_notes = ?
        WHERE id = ?
    """, (data.status, data.admin_notes, donation_id))
    conn.commit()
    conn.close()

    log_audit("UPDATE", "SUPPORT_PLEDGE", record_id=str(donation_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "सहयोगको अवस्था सफलतापूर्वक अद्यावधिक भयो।"}

@router.delete("/{donation_id}")
def delete_support_pledge(donation_id: int, request: Request):
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM support_donations WHERE id = ?", (donation_id,))
    conn.commit()
    conn.close()

    log_audit("DELETE", "SUPPORT_PLEDGE", record_id=str(donation_id), user=user, request=request)
    return {"success": True, "message": "सहयोगको रेकर्ड सफलतापूर्वक हटाइयो।"}

@router.get("/export")
def export_support_pledges_excel(request: Request):
    require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_donations ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "सहयोग तथा साझेदार"

    headers = [
        "क्र.सं.", "सहयोगी व्यक्ति वा संस्था", "ठेगाना", "सम्पर्क नम्बर", "इमेल",
        "सहयोग शीर्षकहरू", "अनुमानित रकम / मूल्य (रु.)", "सहयोगको प्रकार",
        "अन्तराल", "अवधि", "अन्य विद्यालय विवरण", "अवस्था", "मिति"
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for i, r in enumerate(rows, 1):
        try:
            cats = ", ".join(json.loads(r.get("support_categories") or "[]"))
        except Exception:
            cats = r.get("support_categories") or ""
        if r.get("other_category_details"):
            cats += f" ({r['other_category_details']})"

        ws.append([
            i,
            r.get("donor_name"),
            r.get("address"),
            r.get("phone"),
            r.get("email"),
            cats,
            r.get("estimated_amount") or "-",
            r.get("support_type") or "-",
            r.get("frequency") or "-",
            r.get("duration") or "-",
            r.get("other_schools_interest") or "-",
            r.get("status") or "नयाँ",
            str(r.get("created_at") or "")[:10]
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=school_support_pledges.xlsx"}
    )
