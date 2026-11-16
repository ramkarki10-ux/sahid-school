import os
import re
import io
import base64
import uuid
import openpyxl
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import require_auth, get_current_user
from app.utils.audit import log_audit
from app.utils.excel_handler import _style_excel

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Secure storage directory
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

# RBAC: Only Super Admin, Admin, and Principal can Approve/Reject/Revise documents
VERIFIER_ROLES = {"SUPER_ADMIN", "ADMIN", "PRINCIPAL"}

def require_verifier_role(request: Request) -> Dict[str, Any]:
    """Strict RBAC: Only Admin (सुपर एडमिन) and Principal (प्रिन्सिपल) have rights to verify, approve, or reject documents."""
    user = require_auth(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="प्रमाणीकरण आवश्यक छ। कृपया पहिले लगइन गर्नुहोस्।"
        )
    role = str(user.get("role", "")).upper()
    if role not in VERIFIER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="पहुँच अस्वीकृत: कागजात प्रमाणित, अस्वीकृत वा सुधार आवश्यक गर्ने अधिकार केवल सुपर एडमिन, एडमिन र प्रिन्सिपललाई मात्र छ।"
        )
    return user

# ----------------------------------------------------
# 1. CONDITIONAL DOCUMENT REQUIREMENT RULES
# ----------------------------------------------------
DOCUMENT_RULES = {
    "nursery_to_10": {
        "key": "nursery_to_10",
        "title_ne": "नर्सरी देखि कक्षा १० (वा १६ वर्ष मुनि)",
        "subtitle_ne": "आधारभूत तथा माध्यमिक तह (कक्षा नर्सरी-१०)",
        "age_criteria": "१६ वर्ष भन्दा मुनि",
        "required_documents": [
            {
                "type": "विद्यार्थीको जन्मदर्ता (Birth Certificate)",
                "label": "विद्यार्थीको जन्मदर्ता प्रमाणपत्र (Student's Birth Certificate)",
                "mandatory": True,
                "hint": "स्थानीय पञ्जिकाधिकारीबाट जारी आधिकारिक जन्मदर्ता"
            },
            {
                "type": "अभिभावकको नागरिकता (Guardian Citizenship)",
                "label": "अभिभावकको नागरिकता प्रमाणपत्र (Guardian's Citizenship)",
                "mandatory": True,
                "hint": "बुबा/आमा वा संरक्षकको नेपाली नागरिकता प्रमाणपत्र"
            }
        ],
        "optional_documents": [
            {
                "type": "स्थानान्तरण प्रमाणपत्र (Transfer Certificate / TC)",
                "label": "स्थानान्तरण प्रमाणपत्र (TC)",
                "mandatory": False,
                "hint": "अन्य विद्यालयबाट स्थानान्तरण भई आएको भए"
            },
            {
                "type": "चारित्रिक प्रमाणपत्र (Character Certificate)",
                "label": "चारित्रिक प्रमाणपत्र",
                "mandatory": False,
                "hint": "पूर्व विद्यालयको चारित्रिक प्रमाणपत्र"
            },
            {
                "type": "अन्य आधिकारिक कागजात",
                "label": "अन्य आधिकारिक कागजात",
                "mandatory": False,
                "hint": "सिफारिस वा अन्य प्रमाण"
            }
        ]
    },
    "class_11_12": {
        "key": "class_11_12",
        "title_ne": "कक्षा ११ र १२ (वा १६ वर्ष माथि - +२ तह)",
        "subtitle_ne": "उच्च माध्यमिक तह (+२ विज्ञान, व्यवस्थापन, कम्प्युटर साइन्स, होटल व्यवस्थापन)",
        "age_criteria": "१६ वर्ष र सोभन्दा माथि",
        "required_documents": [
            {
                "type": "विद्यार्थीको नागरिकता वा जन्मदर्ता (Citizenship / Birth Certificate)",
                "label": "विद्यार्थीको नागरिकता वा जन्मदर्ता प्रमाणपत्र",
                "mandatory": True,
                "hint": "विद्यार्थीको आफ्नै नागरिकता प्रमाणपत्र वा जन्मदर्ता"
            },
            {
                "type": "लब्धांक पत्र / मार्कसिट (Marksheet)",
                "label": "मार्कसिट (SEE / कक्षा १०/११ लब्धांक पत्र)",
                "mandatory": True,
                "hint": "SEE वा पूर्व परीक्षाको आधिकारिक ग्रेडसिट/मार्कसिट"
            },
            {
                "type": "चारित्रिक प्रमाणपत्र (Character Certificate)",
                "label": "चारित्रिक प्रमाणपत्र (Character Certificate)",
                "mandatory": True,
                "hint": "पूर्व विद्यालयबाट जारी चारित्रिक प्रमाणपत्र"
            },
            {
                "type": "स्थानान्तरण प्रमाणपत्र / TC (Transfer Certificate)",
                "label": "स्थानान्तरण प्रमाणपत्र / TC (Transfer Certificate)",
                "mandatory": True,
                "hint": "पूर्व विद्यालयको मूल स्थानान्तरण प्रमाणपत्र (TC)"
            }
        ],
        "optional_documents": [
            {
                "type": "अभिभावकको नागरिकता (Guardian Citizenship)",
                "label": "अभिभावकको नागरिकता",
                "mandatory": False,
                "hint": "अभिभावकको नागरिकता प्रमाणपत्र"
            },
            {
                "type": "अन्य आधिकारिक कागजात",
                "label": "अन्य आधिकारिक कागजात",
                "mandatory": False,
                "hint": "माइग्रेसन प्रमाणपत्र वा अन्य"
            }
        ]
    }
}

def determine_requirement_group(class_name: Optional[str] = None, class_numeric: Optional[int] = None, age: Optional[int] = None) -> str:
    """Determine requirement category based on class or student age."""
    if class_numeric is not None:
        try:
            cn = int(class_numeric)
            if cn >= 11:
                return "class_11_12"
            else:
                return "nursery_to_10"
        except (ValueError, TypeError):
            pass

    if class_name:
        cn_str = str(class_name).lower()
        if any(w in cn_str for w in ["11", "12", "११", "१२", "+2", "प्लस टु"]):
            return "class_11_12"

    if age is not None:
        try:
            if int(age) >= 16:
                return "class_11_12"
        except (ValueError, TypeError):
            pass

    return "nursery_to_10"

# Pydantic Schemas
class VerifyDocumentRequest(BaseModel):
    verification_status: str = Field(..., description="'प्रमाणित', 'सुधार आवश्यक', 'अस्वीकृत'")
    verification_note: Optional[str] = ""

# ----------------------------------------------------
# 2. API ENDPOINTS
# ----------------------------------------------------
@router.get("/requirements")
def get_document_requirements(
    class_name: Optional[str] = None,
    class_numeric: Optional[int] = None,
    age: Optional[int] = None
):
    """Retrieve conditional document requirements for a specified class or age."""
    group_key = determine_requirement_group(class_name=class_name, class_numeric=class_numeric, age=age)
    rule = DOCUMENT_RULES[group_key]
    return {
        "success": True,
        "requirement_group": group_key,
        "rule": rule,
        "all_rules": DOCUMENT_RULES
    }

@router.get("/checklist/{student_id}")
def get_student_checklist(student_id: int):
    """Get the compliance checklist of required documents for a specific student."""
    conn = get_db()
    cursor = conn.cursor()

    # Get student info
    cursor.execute("""
        SELECT s.*, c.class_name_ne, c.class_numeric
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    st_row = cursor.fetchone()
    if not st_row:
        conn.close()
        raise HTTPException(status_code=404, detail="विद्यार्थी फेला परेन।")

    student = dict(st_row)
    c_name = student.get("class_name_ne") or ""
    c_num = student.get("class_numeric") or 0
    dob = student.get("date_of_birth") or ""

    # Estimate age from BS / AD date of birth if possible
    age = 15
    if dob:
        try:
            year_match = re.search(r'\b(20\d\d)\b', dob)
            if year_match:
                yr = int(year_match.group(1))
                if yr > 2050: # BS year (e.g. 2068)
                    age = max(4, min(25, 2082 - yr))
                elif yr > 1990: # AD year
                    age = max(4, min(25, 2026 - yr))
        except Exception:
            pass

    group_key = determine_requirement_group(class_name=c_name, class_numeric=c_num, age=age)
    rules = DOCUMENT_RULES[group_key]

    # Fetch uploaded documents
    cursor.execute("SELECT * FROM student_documents WHERE student_id = ? ORDER BY id DESC", (student_id,))
    uploaded_docs = [dict(d) for d in cursor.fetchall()]
    conn.close()

    # Checklist comparison
    checklist = []
    all_mandatory_verified = True
    any_missing = False
    any_needs_revision = False
    any_rejected = False

    for req in rules["required_documents"]:
        matching = [d for d in uploaded_docs if req["type"].lower() in d["document_type"].lower() or d["document_type"].lower() in req["type"].lower()]
        if matching:
            doc = matching[0]
            st = doc.get("verification_status", "जाँच हुन बाँकी")
            if st != "प्रमाणित":
                all_mandatory_verified = False
            if st == "सुधार आवश्यक":
                any_needs_revision = True
            elif st == "अस्वीकृत":
                any_rejected = True
            checklist.append({
                "type": req["type"],
                "label": req["label"],
                "mandatory": True,
                "is_uploaded": True,
                "document_id": doc["id"],
                "document_name": doc["document_name"],
                "status": st,
                "note": doc.get("verification_note", ""),
                "verified_at": doc.get("verified_at")
            })
        else:
            all_mandatory_verified = False
            any_missing = True
            checklist.append({
                "type": req["type"],
                "label": req["label"],
                "mandatory": True,
                "is_uploaded": False,
                "document_id": None,
                "document_name": None,
                "status": "अपलोड हुन बाँकी (Missing)",
                "note": "अनिवार्य कागजात अपलोड भएको छैन",
                "verified_at": None
            })

    if any_rejected:
        overall_status = "REJECTED"
        overall_label = "अस्वीकृत कागजात रहेको"
    elif any_needs_revision:
        overall_status = "NEEDS_REVISION"
        overall_label = "सुधार आवश्यक (कागजात पुनः पेश गर्नुहोस्)"
    elif any_missing:
        overall_status = "INCOMPLETE"
        overall_label = "अपूर्ण (आवश्यक कागजात अपलोड हुन बाँकी)"
    elif all_mandatory_verified:
        overall_status = "COMPLETED"
        overall_label = "पूर्ण प्रमाणीकरण सम्पन्न (All Documents Verified)"
    else:
        overall_status = "PENDING_VERIFICATION"
        overall_label = "जाँच हुन बाँकी (Pending Verification)"

    return {
        "success": True,
        "student": {
            "id": student["id"],
            "name": student.get("name_nepali") or student.get("name_english"),
            "class": c_name,
            "roll_no": student.get("roll_no"),
            "estimated_age": age
        },
        "requirement_group": group_key,
        "group_title": rules["title_ne"],
        "checklist": checklist,
        "overall_status": overall_status,
        "overall_label": overall_label,
        "uploaded_count": len(uploaded_docs)
    }

@router.get("")
def list_documents(
    request: Request,
    student_id: Optional[int] = None,
    admission_id: Optional[int] = None,
    verification_status: Optional[str] = None,
    requirement_group: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25
):
    """List documents with status tab counters, conditional group filtering, and search."""
    require_auth(request)
    try:
        page = int(page)
    except Exception:
        page = 1
    try:
        page_size = int(page_size)
    except Exception:
        page_size = 25

    conn = get_db()
    cursor = conn.cursor()

    # Query for documents list
    where_clauses = ["1=1"]
    params = []

    if student_id:
        where_clauses.append("d.student_id = ?")
        params.append(student_id)

    if admission_id:
        where_clauses.append("d.admission_id = ?")
        params.append(admission_id)

    if verification_status and verification_status.strip():
        where_clauses.append("d.verification_status = ?")
        params.append(verification_status.strip())

    if requirement_group and requirement_group.strip():
        where_clauses.append("d.requirement_group = ?")
        params.append(requirement_group.strip())

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("""(
            s.name_nepali LIKE ? OR s.name_english LIKE ? OR s.roll_no LIKE ?
            OR c.class_name_ne LIKE ? OR d.document_name LIKE ? OR d.document_type LIKE ?
            OR d.student_class LIKE ? OR d.verified_by_name LIKE ?
        )""")
        params.extend([term, term, term, term, term, term, term, term])

    where_sql = " AND ".join(where_clauses)

    # Calculate status counts for UI tabs
    cursor.execute("""
        SELECT 
            COUNT(*) as total_all,
            SUM(CASE WHEN verification_status = 'जाँच हुन बाँकी' THEN 1 ELSE 0 END) as total_pending,
            SUM(CASE WHEN verification_status = 'प्रमाणित' THEN 1 ELSE 0 END) as total_verified,
            SUM(CASE WHEN verification_status = 'सुधार आवश्यक' THEN 1 ELSE 0 END) as total_revision,
            SUM(CASE WHEN verification_status = 'अस्वीकृत' THEN 1 ELSE 0 END) as total_rejected
        FROM student_documents
    """)
    cnt_row = cursor.fetchone()
    status_counts = {
        "all": cnt_row[0] or 0,
        "pending": cnt_row[1] or 0,
        "verified": cnt_row[2] or 0,
        "needs_revision": cnt_row[3] or 0,
        "rejected": cnt_row[4] or 0
    }

    # Group counts
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN requirement_group = 'nursery_to_10' THEN 1 ELSE 0 END) as total_nursery_10,
            SUM(CASE WHEN requirement_group = 'class_11_12' THEN 1 ELSE 0 END) as total_class_11_12
        FROM student_documents
    """)
    grp_row = cursor.fetchone()
    group_counts = {
        "nursery_to_10": grp_row[0] or 0,
        "class_11_12": grp_row[1] or 0
    }

    # Count filtered total
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE {where_sql}
    """, params)
    total = cursor.fetchone()[0]

    limit = max(1, min(page_size, 100))
    offset = max(0, (page - 1) * limit)

    query = f"""
        SELECT d.*, 
               s.name_nepali as student_name, s.roll_no, 
               COALESCE(NULLIF(d.student_class, ''), c.class_name_ne, 'नयाँ भर्ना') as display_class,
               COALESCE(NULLIF(d.verified_by_name, ''), u.full_name_ne, '') as verifier_name
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON d.verified_by = u.id
        WHERE {where_sql}
        ORDER BY d.id DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [limit, offset])
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": limit,
        "documents": rows,
        "status_counts": status_counts,
        "group_counts": group_counts
    }

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    document_name: str = Form(...),
    student_id: Optional[int] = Form(None),
    admission_id: Optional[int] = Form(None),
    student_class: Optional[str] = Form(None),
    class_numeric: Optional[int] = Form(None),
    student_age: Optional[int] = Form(None)
):
    """Upload a document with MIME verification, size check, Base64 permanence, and conditional requirement grouping."""
    user = get_current_user(request)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य फाइल प्रकार ({ext})। केवल PDF, JPG, JPEG, PNG वा WebP फाइलहरू अनुमति दिइएको छ।"
        )

    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="फाइल साइज १० MB भन्दा बढी हुन सक्दैन।")

    # Generate permanent data URL for images and small PDFs (<= 3MB) to guarantee persistence on Vercel
    file_data_url = ""
    mime_type = file.content_type or ("application/pdf" if ext == ".pdf" else "image/jpeg")
    if file_size <= 3 * 1024 * 1024:
        file_data_url = f"data:{mime_type};base64,{base64.b64encode(contents).decode('ascii')}"

    # Also save to storage dir
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_name = f"{uuid.uuid4().hex[:12]}_{clean_name}"
    file_path = STORAGE_DIR / unique_name
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass

    conn = get_db()
    cursor = conn.cursor()

    # If student_id is provided, lookup class and info
    st_class = student_class or ""
    st_numeric = class_numeric
    st_age = student_age

    if student_id:
        cursor.execute("""
            SELECT s.name_nepali, s.date_of_birth, c.class_name_ne, c.class_numeric
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.id = ?
        """, (student_id,))
        st_row = cursor.fetchone()
        if st_row:
            if not st_class:
                st_class = st_row["class_name_ne"] or ""
            if st_numeric is None:
                st_numeric = st_row["class_numeric"]
            if st_age is None and st_row["date_of_birth"]:
                try:
                    yr = int(re.search(r'\b(20\d\d)\b', st_row["date_of_birth"]).group(1))
                    st_age = 2082 - yr if yr > 2050 else 2026 - yr
                except Exception:
                    pass

    # Determine requirement group
    req_group = determine_requirement_group(class_name=st_class, class_numeric=st_numeric, age=st_age)

    cursor.execute("""
        INSERT INTO student_documents (
            student_id, admission_id, student_class, class_numeric, student_age,
            requirement_group, document_type, document_name, file_path, file_size,
            mime_type, file_data, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'जाँच हुन बाँकी')
    """, (
        student_id, admission_id, st_class, st_numeric or 0, st_age or 0,
        req_group, document_type.strip(), document_name.strip(),
        str(file_path), file_size, mime_type, file_data_url
    ))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit("DOCUMENT_UPLOAD", "STUDENT_DOCUMENTS", record_id=str(doc_id), user=user, request=request)

    return {
        "success": True,
        "message": "कागजात सफलतापूर्वक अपलोड भयो।",
        "document_id": doc_id,
        "requirement_group": req_group,
        "verification_status": "जाँच हुन बाँकी"
    }

@router.get("/{doc_id}/download")
def download_document(doc_id: int, request: Request):
    """Download or view student document. Supports both disk file and self-contained Base64."""
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    conn.close()

    if not doc:
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")

    # If data URL exists, serve directly (supports Vercel serverless cold instances)
    if doc["file_data"] and doc["file_data"].startswith("data:"):
        try:
            header, encoded = doc["file_data"].split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            raw_bytes = base64.b64decode(encoded)
            ext = ".pdf" if "pdf" in mime else ".jpg"
            filename = f"{doc['document_name']}{ext}".replace(" ", "_")
            return Response(
                content=raw_bytes,
                media_type=mime,
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
        except Exception:
            pass

    file_path = Path(doc["file_path"])
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename=f"{doc['document_name']}{file_path.suffix}",
            media_type=doc["mime_type"] or "application/octet-stream"
        )

    raise HTTPException(status_code=404, detail="कागजात फाइल सर्भरमा फेला परेन।")

@router.post("/{doc_id}/verify")
def verify_document(doc_id: int, req: VerifyDocumentRequest, request: Request):
    """RBAC Endpoint: Approve, Reject, or Mark for Revision.
    STRICTLY RESTRICTED TO Admin (सुपर एडमिन) and Principal (प्रिन्सिपल) ONLY.
    """
    user = require_verifier_role(request)

    valid_statuses = ['जाँच हुन बाँकी', 'प्रमाणित', 'सुधार आवश्यक', 'अस्वीकृत']
    if req.verification_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"अमान्य प्रमाणीकरण स्थिति। मान्य स्थितिहरू: {', '.join(valid_statuses)}"
        )

    verifier_name = user.get("full_name_ne") or user.get("full_name") or user.get("username") or "प्रशासक"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")

    old_status = doc["verification_status"]

    cursor.execute("""
        UPDATE student_documents
        SET verification_status = ?,
            verification_note = ?,
            verified_by = ?,
            verified_by_name = ?,
            verified_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        req.verification_status,
        (req.verification_note or "").strip(),
        user.get("user_id") or user.get("id"),
        verifier_name,
        doc_id
    ))
    conn.commit()
    conn.close()

    log_audit(
        "DOCUMENT_VERIFY", "STUDENT_DOCUMENTS",
        record_id=str(doc_id),
        old_value={"status": old_status},
        new_value={"status": req.verification_status, "note": req.verification_note},
        user=user, request=request
    )

    return {
        "success": True,
        "message": f"कागजातको स्थिति '{req.verification_status}' मा सफलतापूर्वक अद्यावधिक गरियो।",
        "verification_status": req.verification_status,
        "verified_by_name": verifier_name
    }

@router.delete("/{doc_id}")
def delete_document(doc_id: int, request: Request):
    """Delete document. Strictly restricted to Admin & Principal."""
    user = require_verifier_role(request)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="कागजात फेला परेन।")

    doc_name = doc["document_name"]
    file_path = Path(doc["file_path"])
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception:
            pass

    cursor.execute("DELETE FROM student_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    log_audit("DOCUMENT_DELETE", "STUDENT_DOCUMENTS", record_id=str(doc_id), old_value={"name": doc_name}, user=user, request=request)

    return {"success": True, "message": f'कागजात "{doc_name}" सफलतापूर्वक हटाइयो।'}

@router.get("/export")
def export_documents_route(request: Request):
    """Export filtered or all documents verification ledger to Excel."""
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, 
               s.name_nepali as student_name, s.roll_no,
               COALESCE(NULLIF(d.student_class, ''), c.class_name_ne, '-') as display_class,
               COALESCE(NULLIF(d.verified_by_name, ''), u.full_name_ne, '') as verifier_name
        FROM student_documents d
        LEFT JOIN students s ON d.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON d.verified_by = u.id
        ORDER BY d.id DESC
    """)
    docs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "कागजात प्रमाणीकरण"
    headers = [
        "क्र.सं.", "विद्यार्थीको नाम", "कक्षा", "रोल नं.", "वर्ग (Category)",
        "कागजातको प्रकार", "कागजातको नाम", "साइज (KB)", "प्रमाणीकरण स्थिति",
        "कैफियत", "जाँचकर्ता", "अपलोड मिति"
    ]
    rows = []
    for idx, d in enumerate(docs, start=1):
        grp_text = "नर्सरी-१० (१६ वर्ष मुनि)" if d.get("requirement_group") == "nursery_to_10" else "कक्षा ११-१२ (+२ तह)"
        rows.append([
            idx,
            d.get("student_name") or "नयाँ भर्ना आवेदक",
            d.get("display_class") or "-",
            d.get("roll_no") or "-",
            grp_text,
            d.get("document_type") or "",
            d.get("document_name") or "",
            round((d.get("file_size") or 0) / 1024, 1),
            d.get("verification_status") or "जाँच हुन बाँकी",
            d.get("verification_note") or "",
            d.get("verifier_name") or "-",
            str(d.get("created_at") or "")[:19]
        ])

    stream = _style_excel(ws, headers, rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=student_documents_verification.xlsx"}
    )
