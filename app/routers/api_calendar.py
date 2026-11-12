from fastapi import APIRouter, Request, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import base64
import os
import uuid
from pathlib import Path
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.excel_handler import export_calendar_to_excel
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_CALENDAR_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".docx", ".doc"}
MAX_CALENDAR_SIZE = 15 * 1024 * 1024  # 15 MB

class CalendarEventCreate(BaseModel):
    title: str
    event_type: str  # बिदा, पर्व, परीक्षा, खेलकुद, वार्षिकोत्सव, बैठक, अन्य
    start_date: str
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_holiday: bool = False
    color: Optional[str] = "#1e3a8a"

@router.get("/events")
def get_calendar_events(
    request: Request,
    event_type: Optional[str] = Query(None),
    year_month: Optional[str] = Query(None)
):
    """Retrieve all school calendar events with optional filters."""
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM school_calendar_events WHERE 1=1"
    params = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if year_month:
        query += " AND start_date LIKE ?"
        params.append(f"{year_month}%")

    query += " ORDER BY start_date ASC"
    cursor.execute(query, params)
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(events), "events": events}

@router.post("/events")
def create_calendar_event(req: CalendarEventCreate, request: Request):
    """Admin creates a school calendar event."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO school_calendar_events (
            title, event_type, start_date, end_date, description, is_holiday, color
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        req.title, req.event_type, req.start_date, req.end_date,
        req.description, 1 if req.is_holiday else 0, req.color or "#1e3a8a"
    ))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "क्यालेन्डर कार्यक्रम सफलतापूर्वक थपियो।",
        "event_id": event_id
    }

@router.put("/events/{event_id}")
def update_calendar_event(event_id: int, req: CalendarEventCreate, request: Request):
    """Admin updates a school calendar event."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE school_calendar_events SET
            title = ?, event_type = ?, start_date = ?, end_date = ?,
            description = ?, is_holiday = ?, color = ?
        WHERE id = ?
    """, (
        req.title, req.event_type, req.start_date, req.end_date,
        req.description, 1 if req.is_holiday else 0, req.color or "#1e3a8a", event_id
    ))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="कार्यक्रम फेला परेन।")
    conn.commit()
    conn.close()
    return {"success": True, "message": "क्यालेन्डर कार्यक्रम अद्यावधिक भयो।"}

@router.get("/events/export")
def export_calendar_events_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC")
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_calendar_to_excel(events)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=calendar_events.xlsx"}
    )

@router.delete("/events/{event_id}")
def delete_calendar_event(event_id: int, request: Request):
    """Admin deletes a school calendar event."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM school_calendar_events WHERE id = ?", (event_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="कार्यक्रम फेला परेन।")

    conn.commit()
    conn.close()

    return {"success": True, "message": "क्यालेन्डर कार्यक्रम सफलतापूर्वक हटाइयो।"}

# Dedicated Calendar File Management (Prompt 10 Requirement)
@router.get("/file/latest")
def get_latest_calendar_file():
    """Retrieve the latest uploaded academic calendar file."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM academic_calendar_files ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return {"success": True, "calendar_file": dict(row) if row else None}

@router.post("/upload-file")
async def upload_calendar_file(
    request: Request,
    file: UploadFile = File(...),
    academic_year: str = Form("२०८३"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Upload official academic calendar file (PDF, image, doc) (SUPER_ADMIN, ADMIN, PRINCIPAL only)."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_CALENDAR_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य फाइल प्रकार ({ext})। केवल PDF, JPG, PNG, WebP वा Word (.docx) फाइलहरू अनुमति छ।"
        )

    contents = await file.read()
    if len(contents) > MAX_CALENDAR_SIZE:
        raise HTTPException(status_code=400, detail="फाइल साइज १५ MB भन्दा बढी हुन सक्दैन।")

    size_kb = len(contents) / 1024
    if size_kb > 1024:
        size_str = f"{size_kb/1024:.2f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"

    mime_map = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword"
    }
    file_mime = mime_map.get(ext, file.content_type or "application/octet-stream")

    clean_fn = "".join(c for c in file.filename if c.isalnum() or c in "._-").strip()
    unique_fn = f"calendar_{uuid.uuid4().hex[:8]}_{clean_fn}"
    local_path = UPLOAD_DIR / unique_fn
    try:
        with open(local_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass

    # For serverless durability, use base64 data URI if <= 4MB
    if len(contents) <= 4 * 1024 * 1024:
        file_url = f"data:{file_mime};base64,{base64.b64encode(contents).decode('ascii')}"
    else:
        file_url = f"/static/uploads/{unique_fn}"

    default_title = title or f"सहिद स्मृति आवासीय मा.वि. आधिकारिक वार्षिक शैक्षिक क्यालेण्डर {academic_year}"
    default_desc = description or f"वि.सं. {academic_year} सालको शैक्षिक सत्र, भर्ना, परीक्षा, सार्वजनिक बिदा तथा कार्यक्रम तालिका"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO academic_calendar_files (
            academic_year, title, file_url, file_name, file_type, file_size, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (academic_year, default_title, file_url, file.filename, file_mime, size_str, default_desc))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit("FILE_UPLOAD", "ACADEMIC_CALENDAR", record_id=str(new_id), new_value={"file_name": file.filename, "size": size_str}, user=user, request=request)

    return {
        "success": True,
        "message": "शैक्षिक क्यालेण्डर फाइल सफलतापूर्वक अपलोड गरियो।",
        "file": {
            "id": new_id,
            "title": default_title,
            "file_url": file_url,
            "file_name": file.filename,
            "file_size": size_str,
            "file_type": file_mime,
            "description": default_desc
        }
    }

@router.delete("/file/{file_id}")
def delete_calendar_file(file_id: int, request: Request):
    """Delete a calendar file (SUPER_ADMIN, ADMIN, PRINCIPAL only)."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM academic_calendar_files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "क्यालेण्डर फाइल मेटाइयो।"}
