from fastapi import APIRouter, Request, Response, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.audit import log_audit
from app.utils.excel_handler import (
    generate_student_template,
    validate_and_parse_student_excel,
    export_students_to_excel
)

router = APIRouter(prefix="/api/students", tags=["students"])

class StudentCreate(BaseModel):
    student_id: str
    admission_no: str
    registration_no: Optional[str] = None
    name_nepali: str
    name_english: str
    photo: Optional[str] = None
    gender: str
    date_of_birth: str
    class_id: int
    section_id: Optional[int] = None
    roll_no: int
    address: str
    district: Optional[str] = "सुनसरी"
    municipality: Optional[str] = "इटहरी उपमहानगरपालिका"
    ward: Optional[str] = "१९"
    tole: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    guardian_name: str
    guardian_relation: str
    guardian_phone: str
    emergency_contact: Optional[str] = None
    residential_status: Optional[str] = "दिवा"
    hostel_id: Optional[int] = None
    room_id: Optional[int] = None
    bed_no: Optional[str] = None
    bus_id: Optional[int] = None
    pickup_point: Optional[str] = None
    academic_year_id: int
    status: Optional[str] = "सक्रिय"
    remarks: Optional[str] = None

@router.get("")
def list_students(
    request: Request,
    class_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None),
    gender: Optional[str] = Query(None),
    residential_status: Optional[str] = Query(None),
    hostel_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0)
):
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT s.*, c.class_name_ne, c.class_numeric, sec.name as section_name,
               h.hostel_name, b.bus_number
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE 1=1
    """
    params = []
    
    # If teacher role, verify class restriction
    if user["role"] == "TEACHER" and user.get("teacher_id"):
        cursor.execute("""
            SELECT class_id, section_id FROM teacher_class_assignments
            WHERE teacher_id = ?
        """, (user["teacher_id"],))
        assignments = cursor.fetchall()
        if assignments:
            clauses = []
            for a in assignments:
                if a["section_id"]:
                    clauses.append("(s.class_id = ? AND s.section_id = ?)")
                    params.extend([a["class_id"], a["section_id"]])
                else:
                    clauses.append("(s.class_id = ?)")
                    params.append(a["class_id"])
            query += f" AND ({' OR '.join(clauses)})"
        else:
            return {"students": [], "total": 0}
            
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if section_id:
        query += " AND s.section_id = ?"
        params.append(section_id)
    if academic_year_id:
        query += " AND s.academic_year_id = ?"
        params.append(academic_year_id)
    if gender:
        query += " AND s.gender = ?"
        params.append(gender)
    if residential_status:
        query += " AND s.residential_status = ?"
        params.append(residential_status)
    if hostel_id:
        query += " AND s.hostel_id = ?"
        params.append(hostel_id)
    if status_filter:
        query += " AND s.status = ?"
        params.append(status_filter)
    if search:
        s_term = f"%{search.strip()}%"
        query += " AND (s.name_nepali LIKE ? OR s.name_english LIKE ? OR s.student_id LIKE ? OR s.admission_no LIKE ? OR s.roll_no LIKE ?)"
        params.extend([s_term, s_term, s_term, s_term, s_term])
        
    query += " ORDER BY c.class_numeric ASC, sec.name ASC, s.roll_no ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    students = [dict(row) for row in cursor.fetchall()]
    
    # For security: if viewer or unauthorized, hide private guardian contact
    if user["role"] not in ["SUPER_ADMIN", "PRINCIPAL", "TEACHER", "HOSTEL_WARDEN"]:
        for s in students:
            s["guardian_phone"] = "********* (गोप्य)"
            s["emergency_contact"] = None
            
    conn.close()
    return {"students": students, "total": len(students)}

@router.get("/template")
def download_student_template():
    excel_stream = generate_student_template()
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=student_import_template.xlsx"}
    )

@router.get("/export")
def export_students(
    request: Request,
    class_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None)
):
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT s.*, c.class_name_ne as class_name, sec.name as section_name,
               h.hostel_name, b.bus_number
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE 1=1
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if section_id:
        query += " AND s.section_id = ?"
        params.append(section_id)
    if academic_year_id:
        query += " AND s.academic_year_id = ?"
        params.append(academic_year_id)
        
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    students_data = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    excel_stream = export_students_to_excel(students_data)
    if user:
        log_audit("EXCEL_EXPORT", "STUDENTS", user=user, request=request)
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students_list.xlsx"}
    )

@router.post("/import")
async def import_students(
    request: Request,
    file: UploadFile = File(...),
    commit: bool = Form(False),
    academic_year_id: Optional[int] = Form(None)
):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "ADMIN")(request)
    content = await file.read()
    parse_result = validate_and_parse_student_excel(content)

    if not commit:
        # Return Validation Preview
        return {
            "success": parse_result["valid"],
            "preview": True,
            "total_rows": parse_result["total_rows"],
            "new_count": parse_result["new_count"],
            "duplicate_count": parse_result["duplicate_count"],
            "error_count": parse_result["error_count"],
            "valid_rows_count": parse_result["valid_rows_count"],
            "errors": parse_result["errors"],
            "warnings": parse_result["warnings"],
            "rows": parse_result["rows"][:100],
            "message": "फाइल प्रमाणीकरण सम्पन्न भयो।" if parse_result["valid"] else "फाइलमा केही त्रुटिहरू फेला परेका छन्।"
        }

    # Execute Import (commit=True)
    if not parse_result["valid"] and parse_result["error_count"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"त्रुटिहरू रहेका कारण आयात गर्न सकिँदैन: {parse_result['errors'][0]}"
        )

    conn = get_db()
    cursor = conn.cursor()
    if not academic_year_id:
        cursor.execute("SELECT active_academic_year_id FROM school_settings WHERE id = 1")
        row = cursor.fetchone()
        academic_year_id = row[0] if row else 1

    imported_new_count = 0
    updated_count = 0

    conn.execute("BEGIN TRANSACTION")
    try:
        for r in parse_result["rows"]:
            if r.get("errors"):
                continue

            class_id = r["class_id"]
            roll_no = r["roll_no"]
            full_name = r["full_name"]
            guardian_name = r.get("guardian_name") or "अभिभावक"
            guardian_phone = r.get("guardian_phone") or ""
            address = r.get("address") or "इटहरी-१९, सुनसरी"
            gender = r.get("gender") or "अन्य"
            stu_id = r.get("student_id") or f"STU-{class_id:02d}-{roll_no:03d}"
            adm_no = r.get("admission_no") or f"ADM-2083-{class_id:02d}-{roll_no:03d}"

            # Check if student exists by class and roll or student_id
            cursor.execute("""
                SELECT id FROM students WHERE (class_id = ? AND roll_no = ?) OR student_id = ?
            """, (class_id, roll_no, stu_id))
            existing = cursor.fetchone()

            if existing:
                # Update student details without losing attendance history
                cursor.execute("""
                    UPDATE students SET
                        name_nepali = ?, name_english = ?, guardian_name = ?,
                        guardian_phone = ?, address = ?, gender = ?, status = 'सक्रिय',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (full_name, full_name, guardian_name, guardian_phone, address, gender, existing["id"]))
                updated_count += 1
            else:
                # Insert new student
                cursor.execute("""
                    INSERT INTO students (
                        student_id, admission_no, registration_no, emis_code, name_nepali, name_english,
                        gender, date_of_birth, class_id, section_id, roll_no, address,
                        district, municipality, ward, guardian_name, guardian_relation,
                        guardian_phone, residential_status, academic_year_id, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '२०६६-०१-०१', ?, NULL, ?, ?, 'सुनसरी', 'इटहरी', '१९', ?, 'अभिभावक', ?, 'दिवा', ?, 'सक्रिय')
                """, (
                    stu_id, adm_no, f"REG-{class_id}-{roll_no}", f"0119{class_id:02d}{roll_no:03d}",
                    full_name, full_name, gender, class_id, roll_no, address,
                    guardian_name, guardian_phone, academic_year_id
                ))
                new_stu_db_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO student_class_history (student_id, academic_year_id, class_id, roll_no, promotion_status)
                    VALUES (?, ?, ?, ?, 'IMPORTED')
                """, (new_stu_db_id, academic_year_id, class_id, roll_no))
                imported_new_count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"डेटाबेस सुरक्षित गर्दा त्रुटि भयो: {str(e)}")

    conn.close()

    log_audit("EXCEL_IMPORT", "STUDENTS", new_value={"new_count": imported_new_count, "updated_count": updated_count}, user=user, request=request)
    return {
        "success": True,
        "message": f"विद्यार्थी विवरण सफलतापूर्वक आयात भयो। (नयाँ थपिएका: {imported_new_count} जना, अद्यावधिक: {updated_count} जना)",
        "new_count": imported_new_count,
        "updated_count": updated_count,
        "total_processed": imported_new_count + updated_count
    }

@router.get("/{id}")
def get_student(id: int, request: Request):
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.class_name_ne, c.class_numeric, sec.name as section_name,
               h.hostel_name, hr.room_number, b.bus_number, b.route as bus_route
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN hostels h ON s.hostel_id = h.id
        LEFT JOIN hostel_rooms hr ON s.room_id = hr.id
        LEFT JOIN buses b ON s.bus_id = b.id
        WHERE s.id = ?
    """, (id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="विद्यार्थी फेला परेन।")
        
    student_dict = dict(student)
    
    # Class history
    cursor.execute("""
        SELECT sch.*, ay.year_ne, c.class_name_ne, sec.name as section_name, st.name_ne as stream_name
        FROM student_class_history sch
        LEFT JOIN academic_years ay ON sch.academic_year_id = ay.id
        LEFT JOIN classes c ON sch.class_id = c.id
        LEFT JOIN sections sec ON sch.section_id = sec.id
        LEFT JOIN streams st ON sch.stream_id = st.id
        WHERE sch.student_id = ?
        ORDER BY ay.id DESC
    """, (id,))
    student_dict["class_history"] = [dict(r) for r in cursor.fetchall()]
    
    # Attendance summary
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM attendance
        WHERE student_id = ?
        GROUP BY status
    """, (id,))
    student_dict["attendance_stats"] = {r["status"]: r["count"] for r in cursor.fetchall()}
    
    conn.close()
    return student_dict

@router.post("")
def create_student(data: StudentCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    # Check duplicate
    cursor.execute("SELECT id FROM students WHERE student_id = ? OR admission_no = ?", (data.student_id, data.admission_no))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="यो Student ID वा Admission No पहिले नै दर्ता छ।")
        
    cursor.execute("""
        INSERT INTO students (
            student_id, admission_no, registration_no, name_nepali, name_english,
            photo, gender, date_of_birth, class_id, section_id, roll_no, address,
            district, municipality, ward, tole, father_name, mother_name,
            guardian_name, guardian_relation, guardian_phone, emergency_contact,
            residential_status, hostel_id, room_id, bed_no, bus_id, pickup_point,
            academic_year_id, status, remarks
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.student_id, data.admission_no, data.registration_no, data.name_nepali, data.name_english,
        data.photo, data.gender, data.date_of_birth, data.class_id, data.section_id, data.roll_no, data.address,
        data.district, data.municipality, data.ward, data.tole, data.father_name, data.mother_name,
        data.guardian_name, data.guardian_relation, data.guardian_phone, data.emergency_contact,
        data.residential_status, data.hostel_id, data.room_id, data.bed_no, data.bus_id, data.pickup_point,
        data.academic_year_id, data.status, data.remarks
    ))
    new_id = cursor.lastrowid
    
    # Create class history entry
    cursor.execute("""
        INSERT INTO student_class_history (student_id, academic_year_id, class_id, section_id, roll_no, promotion_status)
        VALUES (?, ?, ?, ?, ?, 'NEW_ADMISSION')
    """, (new_id, data.academic_year_id, data.class_id, data.section_id, data.roll_no))
    
    conn.commit()
    conn.close()
    
    log_audit("CREATE", "STUDENTS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "विद्यार्थी सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/{id}")
def update_student(id: int, data: StudentCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="विद्यार्थी फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("""
        UPDATE students SET
            student_id = ?, admission_no = ?, registration_no = ?, name_nepali = ?, name_english = ?,
            photo = ?, gender = ?, date_of_birth = ?, class_id = ?, section_id = ?, roll_no = ?,
            address = ?, district = ?, municipality = ?, ward = ?, tole = ?,
            father_name = ?, mother_name = ?, guardian_name = ?, guardian_relation = ?,
            guardian_phone = ?, emergency_contact = ?, residential_status = ?,
            hostel_id = ?, room_id = ?, bed_no = ?, bus_id = ?, pickup_point = ?,
            academic_year_id = ?, status = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.student_id, data.admission_no, data.registration_no, data.name_nepali, data.name_english,
        data.photo, data.gender, data.date_of_birth, data.class_id, data.section_id, data.roll_no,
        data.address, data.district, data.municipality, data.ward, data.tole,
        data.father_name, data.mother_name, data.guardian_name, data.guardian_relation,
        data.guardian_phone, data.emergency_contact, data.residential_status,
        data.hostel_id, data.room_id, data.bed_no, data.bus_id, data.pickup_point,
        data.academic_year_id, data.status, data.remarks, id
    ))
    conn.commit()
    conn.close()
    
    log_audit("UPDATE", "STUDENTS", record_id=str(id), old_value=old_val, new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "विद्यार्थी विवरण सफलतापूर्वक अद्यावधिक भयो।"}

@router.delete("/{id}")
def delete_student(id: int, request: Request):
    user = require_role("SUPER_ADMIN")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="विद्यार्थी फेला परेन।")
        
    old_val = dict(existing)
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    log_audit("DELETE", "STUDENTS", record_id=str(id), old_value=old_val, user=user, request=request)
    return {"success": True, "message": "विद्यार्थी सफलतापूर्वक मेटाइयो।"}
