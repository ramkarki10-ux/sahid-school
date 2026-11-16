import os
import io
import re
import uuid
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Query, Body
from fastapi.responses import Response, FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from app.database import get_db
from app.auth import require_auth, require_role
from app.utils.audit import log_audit
from app.utils.excel_handler import export_admissions_to_excel

router = APIRouter(prefix="/api/admissions", tags=["admissions"])

# Storage configuration
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    STORAGE_DIR = Path("/tmp/uploads/documents")
else:
    STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"

try:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# RBAC: Only authorized Admin and Principal accounts have review and edit access
AUTHORIZED_ROLES = {"SUPER_ADMIN", "ADMIN", "PRINCIPAL"}

def require_admission_manager(request: Request) -> Dict[str, Any]:
    """Strict RBAC verification: Only Super Admin, Admin, and Principal have access."""
    user = require_auth(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="प्रमाणीकरण आवश्यक छ। कृपया पहिले लगइन गर्नुहोस्।"
        )
    role = str(user.get("role", "")).upper()
    if role not in AUTHORIZED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="पहुँच अस्वीकृत: भर्ना फाराम तथा संलग्न कागजातहरू केवल अधिकृत एडमिन र प्रिन्सिपलले मात्र हेर्न र सम्पादन गर्न सक्नुहुन्छ।"
        )
    return user


def _save_admission_doc(
    file: Any,
    adm_id: int,
    doc_type: str,
    doc_name: str,
    applying_class: str,
    conn
) -> Optional[Dict[str, Any]]:
    """Save an uploaded file both to storage and as Base64 in SQLite for serverless permanence."""
    if not file or not isinstance(file, UploadFile) or not getattr(file, "filename", None):
        return None
        
    contents = b""
    if hasattr(file, "file") and hasattr(file.file, "read"):
        try:
            file.file.seek(0)
            contents = file.file.read()
        except Exception:
            pass
    if not contents and hasattr(file, "read"):
        try:
            res = file.read()
            contents = res if isinstance(res, (bytes, bytearray)) else b""
        except Exception:
            pass

    if not contents or len(contents) == 0:
        return None

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य फाइल प्रकार: {ext}। केवल PDF, JPG, PNG फाइलहरू मान्य छन्।"
        )
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="फाइल साइज १० MB भन्दा कम हुनुपर्छ।"
        )

    clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(file.filename).stem)[:30]
    file_uuid = uuid.uuid4().hex[:8]
    filename = f"adm_{adm_id}_{clean_name}_{file_uuid}{ext}"
    dest_path = STORAGE_DIR / filename
    try:
        with open(dest_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass

    mime = file.content_type or ("application/pdf" if ext == ".pdf" else "image/jpeg")
    file_data = ""
    if len(contents) <= 3.5 * 1024 * 1024:
        b64 = base64.b64encode(contents).decode("utf-8")
        file_data = f"data:{mime};base64,{b64}"

    req_group = "class_11_12" if any(k in str(applying_class) for k in ["11", "12", "११", "१२"]) else "nursery_to_10"

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO student_documents (
            admission_id, student_class, requirement_group,
            document_type, document_name, file_path, file_size, mime_type,
            file_data, verification_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'जाँच हुन बाँकी', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        adm_id, applying_class, req_group,
        doc_type, doc_name or file.filename or doc_type,
        str(dest_path), len(contents), mime, file_data
    ))
    doc_id = cursor.lastrowid
    return {
        "id": doc_id,
        "document_type": doc_type,
        "document_name": doc_name or file.filename,
        "file_path": str(dest_path),
        "file_size": len(contents),
        "mime_type": mime,
        "download_url": f"/api/documents/{doc_id}/download"
    }


def _clean_str(val: Any) -> str:
    """Safely sanitize string inputs avoiding issues with FastAPI Form/File defaults."""
    if val is None or (hasattr(val, "__class__") and "params" in getattr(val.__class__, "__module__", "")):
        return ""
    return str(val).strip()

# ====================================================
# 1. PUBLIC ADMISSION SUBMISSION (Frontend Submission)
# ====================================================

@router.post("/apply")
def submit_admission_apply(
    student_name: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    applying_class: str = Form(...),
    parent_name: str = Form(...),
    mobile: str = Form(...),
    address: str = Form(...),
    previous_school: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    # Optional Document Uploads
    file_birth_cert: Optional[UploadFile] = File(None),
    file_citizenship: Optional[UploadFile] = File(None),
    file_marksheet: Optional[UploadFile] = File(None),
    file_character_cert: Optional[UploadFile] = File(None)
):
    """
    Public Admission Submission endpoint:
    - Accepts student personal and parent contact details.
    - All file upload fields (Birth Certificate, Citizenship, Marksheet & Character Certificate) are strictly OPTIONAL.
    - Attached documents and personal records remain strictly confidential and hidden from public view.
    """
    conn = get_db()
    cursor = conn.cursor()
    uploaded_docs = []

    try:
        # Insert core admission record
        cursor.execute("""
            INSERT INTO admission_applications (
                student_name, dob, gender, applying_class, previous_school,
                parent_name, guardian_name, mobile, email, address, message,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'नयाँ', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            _clean_str(student_name), _clean_str(dob), _clean_str(gender), _clean_str(applying_class),
            _clean_str(previous_school), _clean_str(parent_name), _clean_str(guardian_name),
            _clean_str(mobile), _clean_str(email), _clean_str(address), _clean_str(message)
        ))
        adm_id = cursor.lastrowid
        conn.commit()

        # Save optional documents if attached
        if file_birth_cert and isinstance(file_birth_cert, UploadFile) and getattr(file_birth_cert, "filename", None):
            doc = _save_admission_doc(
                file_birth_cert, adm_id,
                "विद्यार्थीको जन्मदर्ता (Birth Certificate)",
                f"{_clean_str(student_name)} - जन्मदर्ता",
                _clean_str(applying_class), conn
            )
            if doc:
                uploaded_docs.append(doc)
                cursor.execute("UPDATE admission_applications SET birth_certificate_url = ? WHERE id = ?", (doc["download_url"], adm_id))

        if file_citizenship and isinstance(file_citizenship, UploadFile) and getattr(file_citizenship, "filename", None):
            doc = _save_admission_doc(
                file_citizenship, adm_id,
                "अभिभावकको नागरिकता (Guardian Citizenship)",
                f"{_clean_str(parent_name)} - नागरिकता",
                _clean_str(applying_class), conn
            )
            if doc:
                uploaded_docs.append(doc)
                cursor.execute("UPDATE admission_applications SET citizenship_url = ? WHERE id = ?", (doc["download_url"], adm_id))

        if file_marksheet and isinstance(file_marksheet, UploadFile) and getattr(file_marksheet, "filename", None):
            doc = _save_admission_doc(
                file_marksheet, adm_id,
                "मार्कसिट (Mark Sheet / Transcript)",
                f"{_clean_str(student_name)} - मार्कसिट",
                _clean_str(applying_class), conn
            )
            if doc:
                uploaded_docs.append(doc)
                cursor.execute("UPDATE admission_applications SET marksheet_url = ? WHERE id = ?", (doc["download_url"], adm_id))

        if file_character_cert and isinstance(file_character_cert, UploadFile) and getattr(file_character_cert, "filename", None):
            doc = _save_admission_doc(
                file_character_cert, adm_id,
                "चारित्रिक प्रमाणपत्र (Character Certificate)",
                f"{_clean_str(student_name)} - चारित्रिक प्रमाणपत्र",
                _clean_str(applying_class), conn
            )
            if doc:
                uploaded_docs.append(doc)
                cursor.execute("UPDATE admission_applications SET character_cert_url = ? WHERE id = ?", (doc["download_url"], adm_id))

        conn.commit()
    except Exception as e:
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "message": "तपाईंको अनलाइन भर्ना आवेदन फाराम सफलतापूर्वक पेश भयो। विद्यालय प्रशासन शाखाबाट छिट्टै सम्पर्क गरिनेछ।",
        "id": adm_id,
        "documents_uploaded_count": len(uploaded_docs)
    }


# ====================================================
# 2. ADMIN REVIEW, EDIT & APPROVAL WORKFLOW ENDPOINTS
# Strictly restricted to SUPER_ADMIN, ADMIN, PRINCIPAL
# ====================================================

@router.get("")
def list_admissions_admin(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, alias="q")
):
    """List all admission applications with document counts and status for Admin/Principal."""
    require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM admission_applications WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        query += " AND (student_name LIKE ? OR parent_name LIKE ? OR mobile LIKE ? OR applying_class LIKE ?)"
        s = f"%{search.strip()}%"
        params.extend([s, s, s, s])

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    applications = [dict(r) for r in cursor.fetchall()]

    for app in applications:
        cursor.execute("""
            SELECT id, document_type, document_name, file_size, mime_type, verification_status
            FROM student_documents
            WHERE admission_id = ?
            ORDER BY id ASC
        """, (app["id"],))
        docs = [dict(d) for d in cursor.fetchall()]
        app["documents"] = docs
        app["doc_count"] = len(docs)

    conn.close()
    return {"success": True, "applications": applications, "total": len(applications)}


@router.get("/{id}")
def get_admission_detail_admin(id: int, request: Request):
    """Get single admission application with complete attached documents for Admin review."""
    require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admission_applications WHERE id = ?", (id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="भर्ना आवेदन फेला परेन।")

    app_dict = dict(app)

    cursor.execute("""
        SELECT id, admission_id, document_type, document_name, file_size, mime_type,
               verification_status, verification_note, verified_by_name, verified_at, created_at
        FROM student_documents
        WHERE admission_id = ?
        ORDER BY id ASC
    """, (id,))
    docs = [dict(d) for d in cursor.fetchall()]
    for d in docs:
        d["download_url"] = f"/api/documents/{d['id']}/download"

    app_dict["documents"] = docs
    conn.close()
    return {"success": True, "application": app_dict}


class AdmissionUpdatePayload(BaseModel):
    student_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    applying_class: Optional[str] = None
    previous_school: Optional[str] = None
    parent_name: Optional[str] = None
    guardian_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    message: Optional[str] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


@router.put("/{id}")
def update_admission_admin(id: int, payload: AdmissionUpdatePayload, request: Request):
    """
    Inline editing of candidate form data directly within the review panel
    to correct any typos or errors before approval.
    """
    user = require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admission_applications WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="भर्ना आवेदन फेला परेन।")

    fields_to_update = []
    values = []

    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            fields_to_update.append(f"{k} = ?")
            values.append(v)

    if not fields_to_update:
        conn.close()
        return {"success": True, "message": "कुनै परिवर्तन गरिएको छैन।"}

    fields_to_update.append("updated_at = CURRENT_TIMESTAMP")
    values.append(id)

    sql = f"UPDATE admission_applications SET {', '.join(fields_to_update)} WHERE id = ?"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()

    log_audit("UPDATE", "ADMISSIONS", record_id=str(id), new_value=payload.dict(exclude_unset=True), user=user, request=request)
    return {"success": True, "message": "उम्मेदवार विवरण सफलतापूर्वक सम्पादन तथा सुरक्षित भयो।"}


@router.post("/{id}/documents")
def upload_admission_document_admin(
    id: int,
    request: Request,
    document_type: str = Form(...),
    document_name: Optional[str] = Form(None),
    document_file: UploadFile = File(...),
    notes: Optional[str] = Form(None)
):
    """
    Ability to upload replacement or new documents directly from the admin verification panel
    before final approval.
    """
    user = require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT applying_class, student_name FROM admission_applications WHERE id = ?", (id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="भर्ना आवेदन फेला परेन।")

    doc = _save_admission_doc(
        document_file,
        id,
        document_type.strip(),
        (document_name or getattr(document_file, "filename", None) or document_type).strip(),
        app["applying_class"],
        conn
    )
    if not doc:
        conn.close()
        raise HTTPException(status_code=400, detail="कागजात फाइल खाली वा अमान्य छ।")

    if notes:
        cursor.execute("UPDATE student_documents SET verification_note = ? WHERE id = ?", (notes.strip(), doc["id"]))

    cursor.execute("UPDATE admission_applications SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    log_audit("UPLOAD_DOC", "ADMISSIONS", record_id=str(id), new_value={"doc_id": doc["id"], "type": document_type}, user=user, request=request)
    return {"success": True, "message": "नयाँ कागजात सफलतापूर्वक संलग्न गरियो।", "document": doc}


@router.delete("/{id}/documents/{doc_id}")
def delete_admission_document_admin(id: int, doc_id: int, request: Request):
    """
    Capability to remove/delete incorrect or unwanted uploaded documents directly from the review panel.
    """
    user = require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM student_documents WHERE id = ? AND admission_id = ?", (doc_id, id))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="हटाउन खोजिएको कागजात फेला परेन।")

    # Try removing file from disk if present
    try:
        fp = Path(doc["file_path"])
        if fp.exists():
            fp.unlink()
    except Exception:
        pass

    cursor.execute("DELETE FROM student_documents WHERE id = ? AND admission_id = ?", (doc_id, id))
    cursor.execute("UPDATE admission_applications SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    log_audit("DELETE_DOC", "ADMISSIONS", record_id=str(id), new_value={"deleted_doc_id": doc_id}, user=user, request=request)
    return {"success": True, "message": "कागजात सफलतापूर्वक हटाइयो।"}


@router.post("/{id}/approve")
def approve_admission_admin(id: int, request: Request, remarks: Optional[str] = Body(None, embed=True)):
    """
    Approve admission application and verify all attached documents.
    Strictly restricted to Admin and Principal.
    """
    user = require_admission_manager(request)
    verifier_name = user.get("full_name_ne") or user.get("full_name") or user.get("username") or "प्रशासक"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admission_applications WHERE id = ?", (id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="भर्ना आवेदन फेला परेन।")

    # Update application status
    cursor.execute("""
        UPDATE admission_applications
        SET status = 'स्वीकृत',
            remarks = COALESCE(?, remarks),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (remarks, id))

    # Mark all attached documents as verified ('प्रमाणित')
    cursor.execute("""
        UPDATE student_documents
        SET verification_status = 'प्रमाणित',
            verified_by = ?,
            verified_by_name = ?,
            verified_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE admission_id = ?
    """, (user.get("id"), verifier_name, id))

    conn.commit()
    conn.close()

    log_audit("APPROVE", "ADMISSIONS", record_id=str(id), user=user, request=request)
    return {
        "success": True,
        "message": f"विद्यार्थी '{app['student_name']}' को भर्ना आवेदन तथा सम्पूर्ण कागजातहरू सफलतापूर्वक स्वीकृत र प्रमाणित गरियो।"
    }


@router.post("/{id}/reject")
def reject_admission_admin(id: int, request: Request, reason: Optional[str] = Body(None, embed=True)):
    """Reject admission application with reason."""
    user = require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admission_applications WHERE id = ?", (id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="भर्ना आवेदन फेला परेन।")

    cursor.execute("""
        UPDATE admission_applications
        SET status = 'अस्वीकृत',
            remarks = COALESCE(?, remarks),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (reason, id))

    cursor.execute("""
        UPDATE student_documents
        SET verification_status = 'अस्वीकृत',
            verification_note = COALESCE(?, verification_note),
            updated_at = CURRENT_TIMESTAMP
        WHERE admission_id = ?
    """, (reason, id))

    conn.commit()
    conn.close()

    log_audit("REJECT", "ADMISSIONS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "भर्ना आवेदन अस्वीकृत गरियो।"}


@router.delete("/{id}")
def delete_admission_admin(id: int, request: Request):
    """Delete admission application along with all attached documents."""
    user = require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()

    # Delete documents
    cursor.execute("DELETE FROM student_documents WHERE admission_id = ?", (id,))
    cursor.execute("DELETE FROM admission_applications WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    log_audit("DELETE", "ADMISSIONS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "भर्ना आवेदन तथा सम्पूर्ण कागजातहरू सफलतापूर्वक हटाइयो।"}


@router.get("/export")
def export_admissions_excel(request: Request):
    """Export admission applications to Excel. Strictly authenticated."""
    require_admission_manager(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admission_applications ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    stream = export_admissions_to_excel(rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=admissions_data.xlsx"}
    )
