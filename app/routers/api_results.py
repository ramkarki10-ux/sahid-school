from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.auth import require_auth, require_role
from app.utils.audit import log_audit
from app.utils.excel_handler import export_results_to_excel

router = APIRouter(prefix="/api/results", tags=["results"])

class ResultEntry(BaseModel):
    exam_id: int
    student_id: int
    subject_id: int
    theory_obtained: float
    practical_obtained: Optional[float] = 0.0
    remarks: Optional[str] = "नियमित"

def calculate_grade(total: float) -> tuple[str, float]:
    if total >= 90: return "A+", 4.0
    elif total >= 80: return "A", 3.6
    elif total >= 70: return "B+", 3.2
    elif total >= 60: return "B", 2.8
    elif total >= 50: return "C+", 2.4
    elif total >= 40: return "C", 2.0
    elif total >= 35: return "D", 1.6
    else: return "NG", 0.0

@router.get("/exams")
def list_exams():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    exams = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"exams": exams}

@router.get("/search")
def search_result(
    exam_id: int = Query(...),
    class_id: int = Query(...),
    query: str = Query(...)
):
    """
    Search student result by exam, class, and roll number or student_id.
    Returns complete marksheet data.
    """
    conn = get_db()
    cursor = conn.cursor()

    # 1. Verify exam exists
    cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        raise HTTPException(status_code=404, detail="परीक्षा फेला परेन।")
    exam_dict = dict(exam)

    # 2. Find matching student in class
    clean_q = query.strip()
    clean_q_int = None
    try:
        clean_q_int = int(clean_q)
    except ValueError:
        pass

    cursor.execute("""
        SELECT s.*, c.class_name_ne, sec.name as section_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        WHERE s.class_id = ? AND (
            s.student_id = ? OR 
            s.admission_no = ? OR 
            s.roll_no = ? OR 
            s.name_nepali LIKE ? OR 
            s.name_english LIKE ?
        ) LIMIT 1
    """, (class_id, clean_q, clean_q, clean_q_int, f"%{clean_q}%", f"%{clean_q}%"))
    
    student = cursor.fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail=f"कक्षामा रोल नं. वा आईडी '{clean_q}' भएको विद्यार्थी फेला परेन।")
    student_dict = dict(student)

    # 3. Fetch subjects and results
    cursor.execute("""
        SELECT r.id as result_id, r.theory_obtained, r.practical_obtained, r.total_obtained,
               r.grade, r.grade_point, r.remarks,
               s.id as subject_id, s.subject_name_ne, s.subject_name_en, s.subject_code,
               s.theory_marks, s.practical_marks,
               COALESCE(es.full_marks, 100) as full_marks,
               COALESCE(es.pass_marks, 35) as pass_marks
        FROM subjects s
        LEFT JOIN exam_subjects es ON es.exam_id = ? AND es.subject_id = s.id
        LEFT JOIN results r ON r.exam_id = ? AND r.student_id = ? AND r.subject_id = s.id
        WHERE s.class_id = ?
        ORDER BY s.id ASC
    """, (exam_id, exam_id, student_dict["id"], class_id))
    
    records = cursor.fetchall()
    conn.close()

    if not records:
        raise HTTPException(status_code=404, detail="यो विद्यार्थीको परीक्षा नतिजा प्रविष्टि फेला परेन।")

    subjects_data = []
    total_obtained_sum = 0.0
    total_full_marks = 0.0
    total_grade_points = 0.0
    has_failed = False
    graded_count = 0

    for r in records:
        d = dict(r)
        tot = d["total_obtained"]
        if tot is not None:
            total_obtained_sum += tot
            total_full_marks += d["full_marks"]
            gp = d["grade_point"] or 0.0
            total_grade_points += gp
            graded_count += 1
            if tot < d["pass_marks"] or d["grade"] == "NG":
                has_failed = True
        else:
            d["theory_obtained"] = 0.0
            d["practical_obtained"] = 0.0
            d["total_obtained"] = 0.0
            d["grade"] = "ABS"
            d["grade_point"] = 0.0
            has_failed = True

        subjects_data.append(d)

    overall_gpa = round(total_grade_points / graded_count, 2) if graded_count > 0 else 0.0
    percentage = round((total_obtained_sum / total_full_marks) * 100, 2) if total_full_marks > 0 else 0.0

    if overall_gpa >= 3.6: overall_grade = "A+"
    elif overall_gpa >= 3.2: overall_grade = "A"
    elif overall_gpa >= 2.8: overall_grade = "B+"
    elif overall_gpa >= 2.4: overall_grade = "B"
    elif overall_gpa >= 2.0: overall_grade = "C+"
    elif overall_gpa >= 1.6: overall_grade = "C"
    else: overall_grade = "D"

    status_text = "उत्तीर्ण (PASSED)" if not has_failed else "अनुत्तीर्ण (FAILED / NG)"

    return {
        "success": True,
        "student": {
            "id": student_dict["id"],
            "student_id": student_dict["student_id"],
            "roll_no": student_dict["roll_no"],
            "name_nepali": student_dict["name_nepali"],
            "name_english": student_dict["name_english"],
            "class_name_ne": student_dict["class_name_ne"],
            "section_name": student_dict.get("section_name", "A"),
            "gender": student_dict.get("gender", ""),
            "dob": student_dict.get("dob", ""),
            "guardian_name": student_dict.get("guardian_name", "")
        },
        "exam": {
            "id": exam_dict["id"],
            "name_ne": exam_dict["name_ne"],
            "term": exam_dict.get("term", "")
        },
        "subjects": subjects_data,
        "summary": {
            "total_obtained": round(total_obtained_sum, 1),
            "total_full_marks": round(total_full_marks, 1),
            "percentage": percentage,
            "gpa": overall_gpa,
            "overall_grade": overall_grade,
            "status": status_text,
            "is_passed": not has_failed
        }
    }

@router.get("/export")
def export_results_route(
    request: Request,
    exam_id: Optional[int] = Query(None),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT r.*, s.student_id as stu_code, s.roll_no, s.name_nepali,
               c.class_name_ne, sub.subject_name_ne,
               COALESCE(es.full_marks, 100) as full_marks,
               COALESCE(es.pass_marks, 35) as pass_marks
        FROM results r
        JOIN students s ON r.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        JOIN subjects sub ON r.subject_id = sub.id
        LEFT JOIN exam_subjects es ON es.exam_id = r.exam_id AND es.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if exam_id:
        query += " AND r.exam_id = ?"
        params.append(exam_id)
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)

    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC, sub.id ASC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    stream = export_results_to_excel(rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=exam_results_ledger.xlsx"}
    )

@router.post("")
def add_result(data: ResultEntry, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "TEACHER")(request)
    total = (data.theory_obtained or 0.0) + (data.practical_obtained or 0.0)
    grade, gp = calculate_grade(total)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO results (
            exam_id, student_id, subject_id, theory_obtained, practical_obtained,
            total_obtained, grade, grade_point, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.exam_id, data.student_id, data.subject_id, data.theory_obtained,
        data.practical_obtained, total, grade, gp, data.remarks
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "message": "नतिजा सफलतापूर्वक प्रविष्टि भयो।", "id": new_id}

@router.delete("/{id}")
def delete_result(id: int, request: Request):
    require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM results WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "नतिजा रेकर्ड हटाइयो।"}

