import urllib.parse
from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
from app.database import get_db
from app.auth import require_auth, require_role, get_current_user
from app.utils.audit import log_audit
from app.utils.excel_handler import (
    export_attendance_to_excel,
    export_daily_attendance_excel,
    export_monthly_attendance_excel,
    export_quarterly_attendance_excel,
    export_annual_attendance_excel
)

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

class AttendanceCorrectionRequest(BaseModel):
    student_id: int
    attendance_date: str
    new_status: str  # PRESENT, ABSENT, LEAVE
    reason: str

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
    if hasattr(section_id, 'default'):
        section_id = None
    if hasattr(academic_year_id, 'default'):
        academic_year_id = None
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
    if hasattr(section_id, 'default'):
        section_id = None
    if hasattr(academic_year_id, 'default'):
        academic_year_id = None
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

@router.get("/check-class-status")
def check_class_attendance_status(
    class_id: int = Query(...),
    attendance_date: str = Query(...)
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.status, a.recorded_by, a.created_at, a.updated_at,
               u.username, u.full_name_ne as full_name
        FROM attendance a
        LEFT JOIN users u ON a.recorded_by = u.id
        WHERE a.class_id = ? AND a.attendance_date = ?
    """, (class_id, attendance_date))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return {"submitted": False, "count": 0}
        
    present = sum(1 for r in rows if r["status"] == "PRESENT")
    absent = sum(1 for r in rows if r["status"] == "ABSENT")
    leave = sum(1 for r in rows if r["status"] == "LEAVE")
    recorder = rows[0].get("full_name") or rows[0].get("username") or "शिक्षक"
    submitted_at = rows[0].get("created_at") or rows[0].get("updated_at") or ""
    
    return {
        "submitted": True,
        "count": len(rows),
        "present": present,
        "absent": absent,
        "leave": leave,
        "recorder": recorder,
        "submitted_at": submitted_at
    }

@router.post("/correct")
def correct_student_attendance(data: AttendanceCorrectionRequest, request: Request):
    user = require_auth(request)
    if user["role"] not in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        raise HTTPException(status_code=403, detail="हाजिरी सच्याउने अधिकार केवल Admin लाई मात्र छ।")
    
    if not data.reason or not data.reason.strip():
        raise HTTPException(status_code=400, detail="हाजिरी सच्याउनुको कारण (Reason) अनिवार्य छ।")

    conn = get_db()
    cursor = conn.cursor()
    
    # Check existing attendance record
    cursor.execute("""
        SELECT id, status, class_id FROM attendance
        WHERE student_id = ? AND attendance_date = ?
    """, (data.student_id, data.attendance_date))
    att_row = cursor.fetchone()
    
    previous_status = "UNMARKED"
    attendance_id = None
    
    if att_row:
        attendance_id = att_row["id"]
        previous_status = att_row["status"]
        cursor.execute("""
            UPDATE attendance
            SET status = ?, remark = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (data.new_status, f"सच्याइएको ({data.reason})", attendance_id))
    else:
        # Get student class and academic year
        cursor.execute("SELECT class_id, academic_year_id FROM students WHERE id = ?", (data.student_id,))
        stu_row = cursor.fetchone()
        class_id = stu_row["class_id"] if stu_row else 1
        academic_year_id = stu_row["academic_year_id"] if stu_row and stu_row["academic_year_id"] else 1
        cursor.execute("""
            INSERT INTO attendance (student_id, academic_year_id, attendance_date, class_id, status, remark, recorded_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (data.student_id, academic_year_id, data.attendance_date, class_id, data.new_status, f"सच्याइएको ({data.reason})", user["user_id"]))
        attendance_id = cursor.lastrowid

    # Log into attendance_audit_logs
    mod_user_id = user.get("user_id") or user.get("id") or 1
    cursor.execute("""
        INSERT INTO attendance_audit_logs (
            attendance_id, student_id, attendance_date, previous_status, new_status, modified_by, modified_at, reason
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (attendance_id, data.student_id, data.attendance_date, previous_status, data.new_status, mod_user_id, data.reason))
    
    conn.commit()
    conn.close()
    
    log_audit("ATTENDANCE_CORRECTION", "ATTENDANCE", record_id=str(attendance_id), new_value={
        "student_id": data.student_id,
        "date": data.attendance_date,
        "previous_status": previous_status,
        "new_status": data.new_status,
        "reason": data.reason
    }, user=user, request=request)
    
    return {
        "success": True,
        "message": f"हाजिरी सफलतापूर्वक सच्याइयो ({previous_status} -> {data.new_status})।"
    }

@router.get("/audit-logs")
def get_attendance_audit_logs(request: Request, limit: int = 50):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, s.name_nepali as student_name, s.roll_no, c.class_name_ne,
               COALESCE(u.full_name_ne, u.username, 'प्रशासक') as modifier_name
        FROM attendance_audit_logs l
        LEFT JOIN students s ON l.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        LEFT JOIN users u ON l.modified_by = u.id
        ORDER BY l.id DESC LIMIT ?
    """, (limit,))
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"logs": logs}

@router.get("/export-daily")
def export_daily_attendance_route(
    request: Request,
    attendance_date: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    date_val = attendance_date or date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT s.roll_no, s.name_nepali as first_name, '' as last_name,
               c.class_name_ne as class_name, a.status,
               COALESCE(u.full_name_ne, u.username) as teacher_name, a.updated_at as submit_time, a.remark
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = ?
        LEFT JOIN users u ON a.recorded_by = u.id
        WHERE s.status = 'सक्रिय'
    """
    params = [date_val]
    class_name = "सबै कक्षा"
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
        cursor.execute("SELECT class_name_ne FROM classes WHERE id = ?", (class_id,))
        c_row = cursor.fetchone()
        if c_row:
            class_name = c_row["class_name_ne"]
            
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    raw_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # Process rows for exporter
    processed_rows = []
    for r in raw_rows:
        full_name = r["first_name"] or ""
        parts = full_name.strip().split()
        fn = parts[0] if parts else ""
        ln = " ".join(parts[1:]) if len(parts) > 1 else ""
        processed_rows.append({
            "roll_no": r["roll_no"],
            "first_name": fn,
            "last_name": ln,
            "class_name": r["class_name"],
            "status": r["status"] or "UNMARKED",
            "teacher_name": r["teacher_name"] or "विद्यालय प्रशासन",
            "submit_time": r["submit_time"] or "-",
            "remark": r["remark"] or ""
        })
        
    stream = export_daily_attendance_excel(processed_rows, date_val, class_name)
    filename = f"Attendance_Daily_{date_val}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{urllib.parse.quote(filename)}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )

@router.get("/export-monthly")
def export_monthly_attendance_route(
    request: Request,
    year_month: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    ym = year_month or date.today().strftime("%Y-%m")
    conn = get_db()
    cursor = conn.cursor()
    
    class_name = "सबै कक्षा"
    query = """
        SELECT s.id, s.roll_no, s.name_nepali as first_name, '' as last_name,
               c.class_name_ne as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
        cursor.execute("SELECT class_name_ne FROM classes WHERE id = ?", (class_id,))
        c_row = cursor.fetchone()
        if c_row:
            class_name = c_row["class_name_ne"]
            
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    # Fetch all attendance for this month prefix
    cursor.execute("""
        SELECT student_id, attendance_date, status
        FROM attendance
        WHERE attendance_date LIKE ?
    """, (f"{ym}%",))
    att_records = cursor.fetchall()
    conn.close()
    
    # Map attendance by student_id and day
    # day -> '2026-11-05' -> int 5
    stu_att = {}
    for r in att_records:
        sid = r["student_id"]
        dt = r["attendance_date"]
        try:
            day_num = int(dt.split("-")[-1])
        except Exception:
            day_num = 1
        if sid not in stu_att:
            stu_att[sid] = {}
        stu_att[sid][day_num] = r["status"]
        
    students_matrix = []
    for s in student_rows:
        sid = s["id"]
        full_name = s["first_name"] or ""
        parts = full_name.strip().split()
        fn = parts[0] if parts else ""
        ln = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        day_map = stu_att.get(sid, {})
        pres = sum(1 for st in day_map.values() if st == "PRESENT")
        ab = sum(1 for st in day_map.values() if st == "ABSENT")
        lv = sum(1 for st in day_map.values() if st == "LEAVE")
        tot_days = pres + ab + lv
        pct = round((pres / tot_days * 100), 1) if tot_days > 0 else 0.0
        
        students_matrix.append({
            "roll_no": s["roll_no"],
            "first_name": fn,
            "last_name": ln,
            "class_name": s["class_name"],
            "days": day_map,
            "present_days": pres,
            "absent_days": ab,
            "leave_days": lv,
            "attendance_pct": pct
        })
        
    parts = ym.split("-")
    year_str = parts[0] if parts else "२०८३"
    month_name = parts[1] if len(parts) > 1 else "मंसिर"
    stream = export_monthly_attendance_excel(students_matrix, month_name, year_str, class_name, days_count=31)
    filename = f"Attendance_Monthly_{ym}_Class_{class_id or 'all'}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{urllib.parse.quote(filename)}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )

@router.get("/export-quarterly")
def export_quarterly_attendance_route(
    request: Request,
    quarter: int = Query(1),
    year_label: str = Query("२०८३"),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    
    class_name = "सबै कक्षा"
    query = """
        SELECT s.id, s.roll_no, s.name_nepali as first_name, '' as last_name,
               c.class_name_ne as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
        cursor.execute("SELECT class_name_ne FROM classes WHERE id = ?", (class_id,))
        c_row = cursor.fetchone()
        if c_row:
            class_name = c_row["class_name_ne"]
            
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    # Calculate attendance per student
    cursor.execute("""
        SELECT student_id,
               SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as pres,
               SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as abs,
               SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as lev
        FROM attendance
        GROUP BY student_id
    """)
    att_map = {r["student_id"]: r for r in cursor.fetchall()}
    conn.close()
    
    q_names = {1: "प्रथम त्रैमासिक (First Quarter)", 2: "दोस्रो त्रैमासिक (Second Quarter)", 3: "तेस्रो त्रैमासिक (Third Quarter)", 4: "चौथो त्रैमासिक (Fourth Quarter)"}
    q_name = q_names.get(quarter, f"त्रैमासिक {quarter}")
    
    students_data = []
    for s in student_rows:
        sid = s["id"]
        full_name = s["first_name"] or ""
        parts = full_name.strip().split()
        fn = parts[0] if parts else ""
        ln = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        stat = att_map.get(sid, {"pres": 0, "abs": 0, "lev": 0})
        pres = stat["pres"] or 0
        ab = stat["abs"] or 0
        lv = stat["lev"] or 0
        working = pres + ab + lv
        if working == 0:
            working = 60
        pct = round((pres / working * 100), 1) if working > 0 else 0.0
        
        students_data.append({
            "roll_no": s["roll_no"],
            "first_name": fn,
            "last_name": ln,
            "class_name": s["class_name"],
            "working_days": working,
            "present_days": pres,
            "absent_days": ab,
            "leave_days": lv,
            "attendance_pct": pct
        })
        
    stream = export_quarterly_attendance_excel(students_data, q_name, year_label, class_name)
    filename = f"Attendance_Quarter_{quarter}_Class_{class_id or 'all'}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{urllib.parse.quote(filename)}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )

@router.get("/export-annual")
def export_annual_attendance_route(
    request: Request,
    year_label: str = Query("२०८३"),
    class_id: Optional[int] = Query(None)
):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    
    class_name = "सबै कक्षा"
    query = """
        SELECT s.id, s.roll_no, s.name_nepali as first_name, '' as last_name,
               c.class_name_ne as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.status = 'सक्रिय'
    """
    params = []
    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
        cursor.execute("SELECT class_name_ne FROM classes WHERE id = ?", (class_id,))
        c_row = cursor.fetchone()
        if c_row:
            class_name = c_row["class_name_ne"]
            
    query += " ORDER BY c.class_numeric ASC, s.roll_no ASC"
    cursor.execute(query, params)
    student_rows = [dict(r) for r in cursor.fetchall()]
    
    # Calculate attendance
    cursor.execute("""
        SELECT student_id,
               SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as pres,
               SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as abs,
               SUM(CASE WHEN status = 'LEAVE' THEN 1 ELSE 0 END) as lev
        FROM attendance
        GROUP BY student_id
    """)
    att_map = {r["student_id"]: r for r in cursor.fetchall()}
    conn.close()
    
    students_data = []
    for s in student_rows:
        sid = s["id"]
        full_name = s["first_name"] or ""
        parts = full_name.strip().split()
        fn = parts[0] if parts else ""
        ln = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        stat = att_map.get(sid, {"pres": 0, "abs": 0, "lev": 0})
        pres = stat["pres"] or 0
        ab = stat["abs"] or 0
        lv = stat["lev"] or 0
        working = pres + ab + lv
        if working == 0:
            working = 220
        pct = round((pres / working * 100), 1) if working > 0 else 0.0
        
        students_data.append({
            "roll_no": s["roll_no"],
            "first_name": fn,
            "last_name": ln,
            "class_name": s["class_name"],
            "working_days": working,
            "present_days": pres,
            "absent_days": ab,
            "leave_days": lv,
            "attendance_pct": pct
        })
        
    stream = export_annual_attendance_excel(students_data, year_label, class_name)
    filename = f"Attendance_Annual_Class_{class_id or 'all'}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{urllib.parse.quote(filename)}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    )
