import os
import json
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.excel_handler import export_homework_to_excel

router = APIRouter(prefix="/api/homework", tags=["homework"])

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    ATTACHMENTS_DIR = Path("/tmp/static/uploads/homework")
else:
    ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "homework"

try:
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

class HomeworkCreateRequest(BaseModel):
    class_id: int
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str
    title: str
    description: Optional[str] = ""
    assigned_date: Optional[str] = None
    due_date: str
    attachment: Optional[str] = None
    questions: Optional[List[str]] = []

class HomeworkUpdateRequest(BaseModel):
    class_id: Optional[int] = None
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_date: Optional[str] = None
    due_date: Optional[str] = None
    attachment: Optional[str] = None
    questions: Optional[List[str]] = None
    status: Optional[str] = None

@router.get("/subjects")
def get_subjects_by_class(class_id: Optional[int] = None):
    """Fetch curriculum subjects mapped for a selected class (Class 1 to 12)."""
    conn = get_db()
    cursor = conn.cursor()
    if class_id is not None:
        cursor.execute("""
            SELECT s.id, s.class_id, s.subject_name_ne, s.subject_code, c.class_name_ne, c.class_numeric
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            WHERE s.class_id = ?
            ORDER BY s.id ASC
        """, (class_id,))
    else:
        cursor.execute("""
            SELECT s.id, s.class_id, s.subject_name_ne, s.subject_code, c.class_name_ne, c.class_numeric
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            ORDER BY c.class_numeric ASC, s.id ASC
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "subjects": rows}

@router.get("")
def list_homework(
    request: Request,
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    subject_name: Optional[str] = None,
    assigned_date: Optional[str] = None,
    teacher_id: Optional[int] = None,
    is_today: Optional[bool] = None
):
    """Fetch homework items with rich filters."""
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT h.*, 
               c.class_name_ne, c.class_numeric,
               s.name as section_name,
               COALESCE(t.name_nepali, 'विषय शिक्षक') as teacher_name, t.phone as teacher_phone
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN sections s ON h.section_id = s.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        WHERE h.status = 'सक्रिय'
    """
    params = []

    if class_id is not None:
        query += " AND h.class_id = ?"
        params.append(class_id)
    if section_id is not None:
        query += " AND (h.section_id = ? OR h.section_id IS NULL)"
        params.append(section_id)
    if subject_name:
        query += " AND h.subject_name LIKE ?"
        params.append(f"%{subject_name}%")
    if teacher_id:
        query += " AND h.teacher_id = ?"
        params.append(teacher_id)
    if assigned_date:
        query += " AND h.assigned_date = ?"
        params.append(assigned_date)
    if is_today:
        today_str = date.today().isoformat()
        query += " AND h.assigned_date = ?"
        params.append(today_str)

    query += " ORDER BY h.assigned_date DESC, h.id DESC"
    cursor.execute(query, params)
    raw_items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    items = []
    for item in raw_items:
        q_raw = item.get("questions")
        if q_raw:
            try:
                item["question_list"] = json.loads(q_raw)
            except Exception:
                item["question_list"] = []
        else:
            item["question_list"] = []
        items.append(item)

    return {"success": True, "count": len(items), "homework": items}

@router.get("/export")
def export_homework_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.*, c.class_name_ne, t.name_nepali as teacher_name
        FROM homework h
        JOIN classes c ON h.class_id = c.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        ORDER BY h.assigned_date DESC
    """)
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_homework_to_excel(items)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=homework_data.xlsx"}
    )

@router.post("")
def create_homework(req: HomeworkCreateRequest, request: Request):
    """Teacher or Admin creates homework."""
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()

    teacher_id = user.get("teacher_id")
    if not teacher_id and user.get("role") in ["SUPER_ADMIN", "PRINCIPAL", "ADMIN", "TEACHER"]:
        cursor.execute("SELECT id FROM teachers WHERE email = ? OR phone = ? LIMIT 1", (user.get("username"), user.get("phone")))
        t_row = cursor.fetchone()
        if t_row:
            teacher_id = t_row[0]
        else:
            cursor.execute("SELECT id FROM teachers LIMIT 1")
            row = cursor.fetchone()
            teacher_id = row[0] if row else 103
    elif not teacher_id:
        conn.close()
        raise HTTPException(status_code=403, detail="केवल शिक्षक वा प्रशासकले गृहकार्य थप्न सक्दछन्।")

    assigned_date = req.assigned_date or date.today().isoformat()

    # Clean and JSON-encode questions
    cleaned_questions = [q.strip() for q in (req.questions or []) if q and q.strip()]
    questions_json = json.dumps(cleaned_questions, ensure_ascii=False) if cleaned_questions else None

    # Resolve subject_id if not given
    subject_id = req.subject_id
    if not subject_id:
        cursor.execute("SELECT id FROM subjects WHERE class_id = ? AND subject_name_ne = ? LIMIT 1", (req.class_id, req.subject_name))
        s_row = cursor.fetchone()
        if s_row:
            subject_id = s_row[0]

    cursor.execute("""
        INSERT INTO homework (
            academic_year_id, class_id, section_id, subject_id, subject_name,
            teacher_id, title, description, assigned_date, due_date, attachment, status, questions
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'सक्रिय', ?)
    """, (
        req.class_id, req.section_id, subject_id, req.subject_name,
        teacher_id, req.title, req.description or "", assigned_date, req.due_date,
        req.attachment, questions_json
    ))
    hw_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "गृहकार्य तथा प्रश्नावली सफलतापूर्वक सिर्जना गरियो।",
        "homework_id": hw_id
    }

@router.put("/{hw_id}")
def update_homework(hw_id: int, req: HomeworkUpdateRequest, request: Request):
    """Update homework title, description, questions or due date."""
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM homework WHERE id = ?", (hw_id,))
    hw = cursor.fetchone()
    if not hw:
        conn.close()
        raise HTTPException(status_code=404, detail="गृहकार्य फेला परेन।")

    # Teachers and Admins can edit
    if user.get("role") not in ["SUPER_ADMIN", "PRINCIPAL", "ADMIN", "TEACHER"]:
        conn.close()
        raise HTTPException(status_code=403, detail="तपाईंलाई यो गृहकार्य सम्पादन गर्ने अधिकार छैन।")

    class_id = req.class_id if req.class_id is not None else hw["class_id"]
    subject_name = req.subject_name if req.subject_name is not None else hw["subject_name"]
    title = req.title if req.title is not None else hw["title"]
    description = req.description if req.description is not None else hw["description"]
    assigned_date = req.assigned_date if req.assigned_date is not None else hw["assigned_date"]
    due_date = req.due_date if req.due_date is not None else hw["due_date"]
    attachment = req.attachment if req.attachment is not None else hw["attachment"]
    hw_status = req.status if req.status is not None else hw["status"]

    if req.questions is not None:
        cleaned_questions = [q.strip() for q in req.questions if q and q.strip()]
        questions_json = json.dumps(cleaned_questions, ensure_ascii=False) if cleaned_questions else None
    else:
        questions_json = hw["questions"]

    cursor.execute("""
        UPDATE homework
        SET class_id = ?, subject_name = ?, title = ?, description = ?,
            assigned_date = ?, due_date = ?, attachment = ?, status = ?, questions = ?
        WHERE id = ?
    """, (class_id, subject_name, title, description, assigned_date, due_date, attachment, hw_status, questions_json, hw_id))
    conn.commit()
    conn.close()

    return {"success": True, "message": "गृहकार्य तथा प्रश्नावली सफलतापूर्वक अद्यावधिक गरियो।"}

@router.delete("/{hw_id}")
def delete_homework(hw_id: int, request: Request):
    """Delete or deactivate homework."""
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM homework WHERE id = ?", (hw_id,))
    hw = cursor.fetchone()
    if not hw:
        conn.close()
        raise HTTPException(status_code=404, detail="गृहकार्य फेला परेन।")

    if user.get("role") not in ["SUPER_ADMIN", "PRINCIPAL", "ADMIN", "TEACHER"]:
        conn.close()
        raise HTTPException(status_code=403, detail="तपाईंलाई यो गृहकार्य मेटाउने अधिकार छैन।")

    cursor.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "गृहकार्य सफलतापूर्वक हटाइयो।"}
