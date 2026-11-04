from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.excel_handler import export_calendar_to_excel

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

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
