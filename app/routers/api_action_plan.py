from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import base64
import os
import uuid
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pathlib import Path

from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/action-plan", tags=["action-plan"])

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_DOC_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"}
MAX_DOC_SIZE = 15 * 1024 * 1024  # 15 MB

class SaveGridRequest(BaseModel):
    academic_year: Optional[str] = "२०८२/८३"
    title: Optional[str] = "सहिद स्मृति आवासीय माध्यमिक विद्यालय - वार्षिक कार्ययोजना (Academic Action Plan) २०८२/८३"
    grid_data: List[Dict[str, Any]]

@router.get("/latest")
def get_latest_action_plan():
    """Retrieve the latest annual action plan and its grid data."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM annual_action_plans ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"success": True, "plan": None, "grid_data": []}

    plan = dict(row)
    grid_data = []
    if plan.get("grid_data"):
        try:
            grid_data = json.loads(plan["grid_data"])
        except Exception:
            grid_data = []

    return {"success": True, "plan": plan, "grid_data": grid_data}

@router.post("/save-grid")
def save_action_plan_grid(req: SaveGridRequest, request: Request):
    """Save or update the interactive action plan grid (SUPER_ADMIN, ADMIN, PRINCIPAL only)."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    grid_json = json.dumps(req.grid_data, ensure_ascii=False)

    cursor.execute("SELECT id FROM annual_action_plans ORDER BY id DESC LIMIT 1")
    existing = cursor.fetchone()

    if existing:
        plan_id = existing["id"]
        cursor.execute("""
            UPDATE annual_action_plans SET
                academic_year = ?,
                title = ?,
                grid_data = ?,
                status = 'सक्रिय',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE id = ?
        """, (req.academic_year, req.title, grid_json, user.get("username", "ADMIN"), plan_id))
    else:
        cursor.execute("""
            INSERT INTO annual_action_plans (
                academic_year, title, grid_data, status, updated_by
            ) VALUES (?, ?, ?, 'सक्रिय', ?)
        """, (req.academic_year, req.title, grid_json, user.get("username", "ADMIN")))
        plan_id = cursor.lastrowid

    conn.commit()
    conn.close()

    log_audit("UPDATE", "ANNUAL_ACTION_PLAN", record_id=str(plan_id), new_value={"rows_count": len(req.grid_data)}, user=user, request=request)
    return {
        "success": True,
        "message": "वार्षिक कार्ययोजना तालिका सफलतापूर्वक सुरक्षित गरियो।",
        "rows_count": len(req.grid_data),
        "plan_id": plan_id
    }

@router.post("/upload-file")
async def upload_action_plan_file(
    request: Request,
    file: UploadFile = File(...),
    academic_year: str = Form("२०८२/८३"),
    title: Optional[str] = Form(None)
):
    """Upload official action plan file: Doc, Excel, or PDF (SUPER_ADMIN, ADMIN, PRINCIPAL only)."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य फाइल प्रकार ({ext})। केवल PDF, Word (.docx), Excel (.xlsx) वा तस्वीरहरू अनुमति छ।"
        )

    contents = await file.read()
    if len(contents) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="फाइल साइज १५ MB भन्दा बढी हुन सक्दैन।")

    # Format human size
    size_kb = len(contents) / 1024
    if size_kb > 1024:
        size_str = f"{size_kb/1024:.2f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"

    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    file_mime = mime_map.get(ext, file.content_type or "application/octet-stream")

    # Save to disk as well
    clean_fn = "".join(c for c in file.filename if c.isalnum() or c in "._-").strip()
    unique_fn = f"action_plan_{uuid.uuid4().hex[:8]}_{clean_fn}"
    local_path = UPLOAD_DIR / unique_fn
    try:
        with open(local_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass

    # For serverless resilience, store base64 data URL if size <= 4MB, otherwise static URL
    if len(contents) <= 4 * 1024 * 1024:
        file_url = f"data:{file_mime};base64,{base64.b64encode(contents).decode('ascii')}"
    else:
        file_url = f"/static/uploads/{unique_fn}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM annual_action_plans ORDER BY id DESC LIMIT 1")
    existing = cursor.fetchone()

    default_title = title or "सहिद स्मृति आवासीय मा.वि. वार्षिक कार्ययोजना २०८२/८३"

    if existing:
        plan_id = existing["id"]
        cursor.execute("""
            UPDATE annual_action_plans SET
                academic_year = ?,
                title = COALESCE(?, title),
                file_url = ?,
                file_name = ?,
                file_type = ?,
                file_size = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE id = ?
        """, (academic_year, default_title, file_url, file.filename, file_mime, size_str, user.get("username", "ADMIN"), plan_id))
    else:
        cursor.execute("""
            INSERT INTO annual_action_plans (
                academic_year, title, file_url, file_name, file_type, file_size, status, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, 'सक्रिय', ?)
        """, (academic_year, default_title, file_url, file.filename, file_mime, size_str, user.get("username", "ADMIN")))
        plan_id = cursor.lastrowid

    conn.commit()
    conn.close()

    log_audit("FILE_UPLOAD", "ANNUAL_ACTION_PLAN", record_id=str(plan_id), new_value={"file_name": file.filename, "size": size_str}, user=user, request=request)

    return {
        "success": True,
        "message": "वार्षिक कार्ययोजना फाइल सफलतापूर्वक अपलोड गरियो।",
        "file_url": file_url,
        "file_name": file.filename,
        "file_size": size_str,
        "file_type": file_mime
    }

@router.delete("/file")
def delete_action_plan_file(request: Request):
    """Remove the uploaded action plan file (SUPER_ADMIN, ADMIN, PRINCIPAL only)."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM annual_action_plans ORDER BY id DESC LIMIT 1")
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE annual_action_plans SET
                file_url = NULL,
                file_name = NULL,
                file_type = NULL,
                file_size = NULL,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE id = ?
        """, (user.get("username", "ADMIN"), existing["id"]))
        conn.commit()
    conn.close()
    return {"success": True, "message": "फाइल हटाइयो।"}

@router.get("/export")
def export_action_plan_excel():
    """Export the annual action plan grid to an Excel spreadsheet."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM annual_action_plans ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    grid_data = []
    academic_year = "२०८२/८३"
    title = "वार्षिक कार्ययोजना"
    if row:
        academic_year = row["academic_year"] or "२०८२/८३"
        title = row["title"] or "वार्षिक कार्ययोजना"
        if row["grid_data"]:
            try:
                grid_data = json.loads(row["grid_data"])
            except Exception:
                grid_data = []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "वार्षिक कार्ययोजना"

    # Header styling
    title_font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
    sub_font = Font(name="Arial", size=10, italic=True, color="475569")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    border_thin = Side(border_style="thin", color="CBD5E1")
    box_border = Border(top=border_thin, left=border_thin, right=border_thin, bottom=border_thin)

    # Title rows
    ws.merge_cells("A1:G1")
    ws["A1"] = f"सहिद स्मृति आवासीय माध्यमिक विद्यालय - {title}"
    ws["A1"].font = title_font
    ws["A1"].alignment = center_align

    ws.merge_cells("A2:G2")
    ws["A2"] = f"शैक्षिक सत्र: {academic_year} | इटहरी-१९, सुनसरी, कोशी प्रदेश, नेपाल"
    ws["A2"].font = sub_font
    ws["A2"].alignment = center_align

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    headers = [
        "क्र.सं.", "महिना", "प्रमुख क्रियाकलाप / कार्यक्रम",
        "लक्षित समूह / कक्षा", "जिम्मेवार व्यक्ति / समिति",
        "अपेक्षित उपलब्धि / सूचक", "कैफियत / स्थिति"
    ]
    col_widths = [8, 12, 38, 24, 26, 32, 14]

    for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = box_border
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = w

    ws.row_dimensions[4].height = 26

    current_row = 5
    for idx, item in enumerate(grid_data, start=1):
        ws.cell(row=current_row, column=1, value=item.get("sn", idx)).alignment = center_align
        ws.cell(row=current_row, column=2, value=item.get("month", "")).alignment = center_align
        ws.cell(row=current_row, column=3, value=item.get("activity", "")).alignment = left_align
        ws.cell(row=current_row, column=4, value=item.get("target_group", "")).alignment = left_align
        ws.cell(row=current_row, column=5, value=item.get("responsible", "")).alignment = left_align
        ws.cell(row=current_row, column=6, value=item.get("outcome", "")).alignment = left_align
        ws.cell(row=current_row, column=7, value=item.get("remarks", "")).alignment = center_align

        for col_idx in range(1, 8):
            c = ws.cell(row=current_row, column=col_idx)
            c.border = box_border
            c.font = Font(name="Arial", size=9)

        ws.row_dimensions[current_row].height = 24
        current_row += 1

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = "Annual_Action_Plan.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
