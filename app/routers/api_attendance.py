from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.audit import log_audit
from app.utils.excel_handler import export_attendance_to_excel

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

class AttendanceItem(BaseModel):
    student_id: int
    status: str  # PRESENT, ABSENT, LEAVE
    remark: Optional[str] = None
    remarks: Optional[str] = None

class BulkAttendanceSaveRequest(BaseModel):
    academic_year_id: Optional[int] = 1
    class_id: int
    section_id: Optional[int] = None
    attendance_date: str
    event_type: Optional[str] = "FIRST_PERIOD"  # FIRST_PERIOD, FINAL_ATTENDANCE
    send_sms_notification: Optional[bool] = True
    records: List[AttendanceItem]

@router.get("")
@router.get("/sheet")
def get_class_attendance_sheet(
    request: Request,
    class_id: int = Query(...),
    attendance_date: str = Query(...),
    section_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None)
):
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    
    # If teacher, verify authorization to access this class
    if user["role"] == "TEACHER" and user.get("teacher_id"):
        cursor.execute("""
            SELECT id FROM teacher_class_assignments
            WHERE teacher_id = ? AND class_id = ? AND (section_id = ? OR section_id IS NULL)
        """, (user["teacher_id"], class_id, section_id))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=403, detail="तपाईंलाई यो कक्षाको हाजिरी लिने अनुमति छैन।")
            
    if not academic_year_id:
        cursor.execute("SELECT active_academic_year_id FROM school_settings WHERE id = 1")
        row = cursor.fetchone()
        academic_year_id = row[0] if row else 1
        
    # Get students in this class/section
    q = """
        SELECT s.id as student_id, s.roll_no, s.name_nepali, s.name_english,
               s.address, s.guardian_name, s.guardian_phone,
               a.id as attendance_id, a.status as attendance_status, a.remark
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        WHERE s.class_id = ? AND s.status = 'सक्रिय'
    """
    params = [attendance_date, class_id]
    if section_id:
        q += " AND s.section_id = ?"
        params.append(section_id)
        
    q += " ORDER BY s.roll_no ASC"
    cursor.execute(q, params)
    students = [dict(r) for r in cursor.fetchall()]
    
    # Default status to 'PRESENT' if not recorded yet
    for s in students:
        if not s["attendance_status"]:
            s["attendance_status"] = "PRESENT"
            
    # Class metadata
    cursor.execute("SELECT class_name_ne, class_numeric FROM classes WHERE id = ?", (class_id,))
    c_info = cursor.fetchone()
    sec_info = None
    if section_id:
        cursor.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
        sec_info = cursor.fetchone()
        
    conn.close()
    return {
        "success": True,
        "class_name": c_info["class_name_ne"] if c_info else "",
        "section_name": sec_info["name"] if sec_info else "All",
        "attendance_date": attendance_date,
        "total_students": len(students),
        "students": students,
        "sheet": students
    }

@router.get("/export")
def export_attendance_route(
    request: Request,
    attendance_date: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    date_val = attendance_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT a.attendance_date, a.status, a.remark as remarks,
               s.name_nepali, s.roll_no, c.class_name_ne, sec.name as section_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        WHERE a.attendance_date = ?
    """
    params = [date_val]
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_attendance_to_excel(rows, date_val)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=attendance_{date_val}.xlsx"}
    )

@router.post("")
@router.post("/bulk")
def save_attendance(data: BulkAttendanceSaveRequest, request: Request):
    user = require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    
    # Teacher permission check
    if user["role"] == "TEACHER" and user.get("teacher_id"):
        cursor.execute("""
            SELECT id FROM teacher_class_assignments
            WHERE teacher_id = ? AND class_id = ? AND (section_id = ? OR section_id IS NULL)
        """, (user["teacher_id"], data.class_id, data.section_id))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=403, detail="तपाईंलाई यो कक्षाको हाजिरी लिने अनुमति छैन।")
            
    saved_count = 0
    present_count = 0
    absent_count = 0
    leave_count = 0
    sms_sent_count = 0
    sms_skipped_count = 0
    event_type = data.event_type or "FIRST_PERIOD"
    
    # Check SMS gateway status
    cursor.execute("SELECT is_enabled, balance FROM sms_gateway_settings WHERE id = 1")
    sms_row = cursor.fetchone()
    sms_enabled = sms_row and sms_row["is_enabled"] and (sms_row["balance"] or 0) > 0

    for r in data.records:
        cursor.execute("""
            INSERT INTO attendance (
                student_id, academic_year_id, attendance_date, class_id, section_id,
                status, remark, recorded_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                status = excluded.status,
                remark = excluded.remark,
                recorded_by = excluded.recorded_by,
                updated_at = CURRENT_TIMESTAMP
        """, (
            r.student_id, data.academic_year_id, data.attendance_date, data.class_id, data.section_id,
            r.status, (r.remark or r.remarks), user["user_id"]
        ))
        saved_count += 1
        if r.status == "PRESENT":
            present_count += 1
        elif r.status == "ABSENT":
            absent_count += 1
            # If SMS enabled and requested, handle absence notification
            if data.send_sms_notification:
                cursor.execute("SELECT name_nepali, guardian_phone, guardian_name FROM students WHERE id = ?", (r.student_id,))
                stu_info = cursor.fetchone()
                if stu_info and stu_info["guardian_phone"]:
                    g_phone = stu_info["guardian_phone"].strip()
                    # Check duplicate
                    cursor.execute("""
                        SELECT id FROM attendance_notifications
                        WHERE student_id = ? AND attendance_date = ? AND attendance_event = ? AND notification_type = 'ABSENCE_SMS'
                    """, (r.student_id, data.attendance_date, event_type))
                    if cursor.fetchone():
                        sms_skipped_count += 1
                    else:
                        sms_msg = f"आदरणीय अभिभावकज्यू, आज मिति {data.attendance_date} मा तपाईंको छोरा/छोरी {stu_info['name_nepali']} विद्यालयमा अनुपस्थित हुनुभएको जानकारी गराउँदछौँ। - सहिद स्मृति आ.मा.वि."
                        cursor.execute("""
                            INSERT INTO attendance_notifications (
                                student_id, attendance_date, attendance_event, notification_type,
                                recipient_phone, message_content, status, gateway_response
                            ) VALUES (?, ?, ?, 'ABSENCE_SMS', ?, ?, 'SENT', 'Simulated SMS Gateway Success: 200 OK')
                        """, (r.student_id, data.attendance_date, event_type, g_phone, sms_msg))
                        sms_sent_count += 1
                        # Deduct balance
                        cursor.execute("UPDATE sms_gateway_settings SET balance = MAX(0, balance - 1) WHERE id = 1")
        elif r.status == "LEAVE":
            leave_count += 1
            
    conn.commit()
    conn.close()
    
    log_audit("RECORD_ATTENDANCE", "ATTENDANCE", record_id=f"{data.class_id}_{data.attendance_date}_{event_type}", new_value={
        "date": data.attendance_date,
        "event_type": event_type,
        "class_id": data.class_id,
        "section_id": data.section_id,
        "present": present_count,
        "absent": absent_count,
        "leave": leave_count,
        "sms_sent": sms_sent_count
    }, user=user, request=request)
    
    return {
        "success": True,
        "message": "हाजिरी सफलतापूर्वक सुरक्षित भयो।",
        "event_type": event_type,
        "saved_count": saved_count,
        "present_count": present_count,
        "absent_count": absent_count,
        "leave_count": leave_count,
        "sms_sent_count": sms_sent_count,
        "sms_skipped_count": sms_skipped_count
    }

@router.get("/daily")
def get_daily_attendance_summary(
    request: Request,
    attendance_date: Optional[str] = Query(None)
):
    require_auth(request)
    if not attendance_date:
        attendance_date = date.today().isoformat()
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.id as class_id, c.class_name_ne, c.class_numeric,
            COUNT(DISTINCT s.id) as total_students,
            SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN a.status = 'LEAVE' THEN 1 ELSE 0 END) as leave_count
        FROM classes c
        JOIN students s ON c.id = s.class_id AND s.status = 'सक्रिय'
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        GROUP BY c.id
        ORDER BY c.class_numeric ASC
    """, (attendance_date,))
    classes_summary = [dict(r) for r in cursor.fetchall()]
    
    total_stu = sum(c["total_students"] for c in classes_summary)
    total_pres = sum(c["present_count"] or 0 for c in classes_summary)
    total_abs = sum(c["absent_count"] or 0 for c in classes_summary)
    total_leave = sum(c["leave_count"] or 0 for c in classes_summary)
    
    percentage = round((total_pres / total_stu * 100), 1) if total_stu > 0 else 0
    
    conn.close()
    return {
        "attendance_date": attendance_date,
        "total_students": total_stu,
        "total_present": total_pres,
        "total_absent": total_abs,
        "total_leave": total_leave,
        "percentage": percentage,
        "classes": classes_summary
    }

@router.get("/absent")
def get_absent_students_today(
    request: Request,
    attendance_date: Optional[str] = Query(None)
):
    """
    Section 33: Absent Student Screen
    Columns: विद्यार्थी, कक्षा, रोल नं., अभिभावक, सम्पर्क (private)
    """
    user = require_auth(request)
    if not attendance_date:
        attendance_date = date.today().isoformat()
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.student_id, s.roll_no, s.name_nepali, s.name_english,
               c.class_name_ne, sec.name as section_name,
               s.guardian_name, s.guardian_phone, s.residential_status,
               a.remark
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN classes c ON a.class_id = c.id
        LEFT JOIN sections sec ON a.section_id = sec.id
        WHERE a.attendance_date = ? AND a.status = 'ABSENT'
        ORDER BY c.class_numeric ASC, s.roll_no ASC
    """, (attendance_date,))
    absent_list = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "attendance_date": attendance_date,
        "total_absent": len(absent_list),
        "students": absent_list
    }

@router.get("/monthly")
def get_monthly_attendance_summary(
    request: Request,
    class_id: Optional[int] = Query(None),
    month_prefix: Optional[str] = Query(None)  # e.g., '2083-01' or '2026-10'
):
    require_auth(request)
    if not month_prefix:
        month_prefix = date.today().strftime("%Y-%m")
        
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT 
            s.id as student_id, s.roll_no, s.name_nepali, c.class_name_ne,
            SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END) as present_days,
            SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END) as absent_days,
            SUM(CASE WHEN a.status = 'LEAVE' THEN 1 ELSE 0 END) as leave_days,
            COUNT(a.id) as recorded_days
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date LIKE ?
        WHERE s.status = 'सक्रिय'
    """
    params = [f"{month_prefix}%"]
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
        
    query += " GROUP BY s.id ORDER BY s.roll_no ASC"
    cursor.execute(query, params)
    data = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "month": month_prefix,
        "records": data
    }

@router.get("/student/{id}")
def get_student_attendance_history(id: int, request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.attendance_date, a.status, a.remark, u.username as recorded_by_user
        FROM attendance a
        LEFT JOIN users u ON a.recorded_by = u.id
        WHERE a.student_id = ?
        ORDER BY a.attendance_date DESC LIMIT 100
    """, (id,))
    history = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"student_id": id, "history": history}
