from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.auth import require_auth, get_current_user, require_role
from app.utils.excel_handler import export_leave_applications_to_excel

router = APIRouter(prefix="/api/leave-applications", tags=["leave"])

class LeaveApplicationCreate(BaseModel):
    student_id: Optional[int] = None
    student_name: str
    class_id: int
    section_id: Optional[int] = None
    roll_no: Optional[int] = None
    applicant_name: str
    applicant_phone: str
    reason: str
    start_date: str
    end_date: str
    total_days: Optional[int] = 1

class LeaveReviewRequest(BaseModel):
    status: str  # 'स्वीकृत', 'अस्वीकृत'
    review_remarks: Optional[str] = None

@router.get("")
def list_leave_applications(
    request: Request,
    class_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    student_id: Optional[int] = Query(None)
):
    """List leave applications with class and reviewer details."""
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT l.*, c.class_name_ne, c.class_numeric, s.name as section_name,
               u.full_name_ne as reviewer_name
        FROM leave_applications l
        JOIN classes c ON l.class_id = c.id
        LEFT JOIN sections s ON l.section_id = s.id
        LEFT JOIN users u ON l.reviewed_by = u.id
        WHERE 1=1
    """
    params = []

    if class_id:
        query += " AND l.class_id = ?"
        params.append(class_id)
    if status:
        query += " AND l.status = ?"
        params.append(status)
    if student_id:
        query += " AND l.student_id = ?"
        params.append(student_id)

    query += " ORDER BY l.id DESC"
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(items), "applications": items}

@router.post("")
def submit_leave_application(req: LeaveApplicationCreate, request: Request):
    """Public / Parent / Student submission of leave application."""
    conn = get_db()
    cursor = conn.cursor()

    # If student_id is not provided, try to find matching student
    student_id = req.student_id
    if not student_id and req.roll_no:
        cursor.execute("""
            SELECT id FROM students WHERE class_id = ? AND roll_no = ? AND status = 'सक्रिय' LIMIT 1
        """, (req.class_id, req.roll_no))
        row = cursor.fetchone()
        if row:
            student_id = row[0]

    cursor.execute("""
        INSERT INTO leave_applications (
            student_id, student_name, class_id, section_id, roll_no,
            applicant_name, applicant_phone, reason, start_date, end_date,
            total_days, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'विचाराधीन')
    """, (
        student_id, req.student_name, req.class_id, req.section_id, req.roll_no,
        req.applicant_name, req.applicant_phone, req.reason, req.start_date, req.end_date,
        req.total_days or 1
    ))
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "बिदा निवेदन सफलतापूर्वक दर्ता भयो। सम्बन्धित शिक्षक वा प्रशासनबाट समीक्षा गरिनेछ।",
        "application_id": app_id
    }

@router.post("/{app_id}/review")
def review_leave_application(app_id: int, req: LeaveReviewRequest, request: Request):
    """Teacher or Admin reviews (approves/rejects) leave application."""
    user = require_auth(request)
    if req.status not in ['स्वीकृत', 'अस्वीकृत']:
        raise HTTPException(status_code=400, detail="स्थिति 'स्वीकृत' वा 'अस्वीकृत' हुनुपर्दछ।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leave_applications
        SET status = ?,
            review_remarks = ?,
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (req.status, req.review_remarks, user["user_id"], app_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="बिदा निवेदन फेला परेन।")

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"बिदा निवेदन '{req.status}' गरियो।",
        "status": req.status
    }

@router.delete("/{id}")
def delete_leave_application(id: int, request: Request):
    require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leave_applications WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "बिदा निवेदन हटाइयो।"}

@router.get("/export")
def export_leaves_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, c.class_name_ne, c.class_numeric, s.name as section_name
        FROM leave_applications l
        JOIN classes c ON l.class_id = c.id
        LEFT JOIN sections s ON l.section_id = s.id
        ORDER BY l.id DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_leave_applications_to_excel(rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leave_applications.xlsx"}
    )

