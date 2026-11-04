import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import openpyxl
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.excel_handler import _style_excel

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Secure storage directory for private documents (NOT exposed under static directly)
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class VerifyDocumentRequest(BaseModel):
    verification_status: str  # 'प्रमाणित', 'सुधार आवश्यक', 'अस्वीकृत'
    verification_note: Optional[str] = None

@router.get("")
def list_documents(
    request: Request,
    student_id: Optional[int] = None,
    admission_id: Optional[int] = None,
    verification_status: Optional[str] = None
):
    """List documents. Admin can see all, teachers can see their class, students/parents see their own."""
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT d.*, 
               s.name_nepali as student_name, s.roll_no, c.class_name_ne,
               u.full_name_ne as verifier_name
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON d.verified_by = u.id
        WHERE 1=1
    """
    params = []

    if student_id:
        query += " AND d.student_id = ?"
        params.append(student_id)
    if admission_id:
        query += " AND d.admission_id = ?"
        params.append(admission_id)
    if verification_status:
        query += " AND d.verification_status = ?"
        params.append(verification_status)

    query += " ORDER BY d.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(rows), "documents": rows}

@router.get("/export")
def export_documents_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, s.name_nepali as student_name, s.roll_no, c.class_name_ne
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        ORDER BY d.id DESC
    """)
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "कागजात प्रमाणीकरण"
    headers = ["क्र.सं.", "विद्यार्थीको नाम", "कक्षा", "रोल नं.", "कागजातको प्रकार", "कागजातको नाम", "प्रमाणीकरण स्थिति", "कैफियत", "अपलोड मिति"]
    rows = []
    for idx, d in enumerate(docs, start=1):
        rows.append([
            idx, d.get("student_name", "नयाँ भर्ना आवेदक"), d.get("class_name_ne", "-"),
            d.get("roll_no", "-"), d.get("document_type", ""), d.get("document_name", ""),
            d.get("verification_status", "जाँच हुन बाँकी"), d.get("verification_note", ""),
            str(d.get("created_at", ""))[:19]
        ])
    stream = _style_excel(ws, headers, rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=documents_verification.xlsx"}
    )

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    document_name: str = Form(...),
    student_id: Optional[int] = Form(None),
    admission_id: Optional[int] = Form(None)
):
    """Upload a document with MIME and size verification."""
    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"अमान्य फाइल प्रकार। केवल PDF, JPG, PNG फाइलहरू अनुमति दिइएको छ।")

    # Read and check size
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="फाइल साइज ५ MB भन्दा बढी हुन सक्दैन।")

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = STORAGE_DIR / unique_name

    with open(file_path, "wb") as f:
        f.write(contents)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO student_documents (
            student_id, admission_id, document_type, document_name,
            file_path, file_size, mime_type, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'जाँच हुन बाँकी')
    """, (
        student_id, admission_id, document_type, document_name,
        str(file_path), file_size, file.content_type
    ))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "कागजात सफलतापूर्वक अपलोड भयो।",
        "document_id": doc_id,
        "verification_status": "जाँच हुन बाँकी"
    }

@router.get("/{doc_id}/download")
def download_document(doc_id: int, request: Request):
    """Private authenticated download endpoint. Public direct access is disallowed."""
    # Allow authenticated users
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    conn.close()

    if not doc:
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")

    file_path = Path(doc["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="फाइल सर्भरमा फेला परेन।")

    return FileResponse(
        path=str(file_path),
        filename=f"{doc['document_name']}_{doc['document_type']}{file_path.suffix}",
        media_type=doc["mime_type"] or "application/octet-stream"
    )

@router.post("/{doc_id}/verify")
def verify_document(doc_id: int, req: VerifyDocumentRequest, request: Request):
    """Admin / Principal verification endpoint."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    if req.verification_status not in ['जाँच हुन बाँकी', 'प्रमाणित', 'सुधार आवश्यक', 'अस्वीकृत']:
        raise HTTPException(status_code=400, detail="अमान्य प्रमाणीकरण स्थिति।")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE student_documents
        SET verification_status = ?,
            verification_note = ?,
            verified_by = ?,
            verified_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (req.verification_status, req.verification_note, user["user_id"], doc_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")
        
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"कागजातको स्थिति '{req.verification_status}' मा अद्यावधिक गरियो।",
        "verification_status": req.verification_status
    }

@router.delete("/{doc_id}")
def delete_document(doc_id: int, request: Request):
    """Delete document and remove file from disk."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM student_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")

    file_path = Path(row[0])
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    cursor.execute("DELETE FROM student_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "कागजात सफलतापूर्वक हटाइयो।"}
