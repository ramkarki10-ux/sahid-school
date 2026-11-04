import io
import re
from typing import List, Dict, Any, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.database import get_db

STUDENT_EXCEL_COLUMNS = [
    "Student ID",
    "Admission No",
    "Registration No",
    "EMIS Code",
    "Name Nepali",
    "Name English",
    "Class",
    "Section",
    "Roll No",
    "Gender",
    "Date of Birth",
    "Address",
    "District",
    "Municipality",
    "Ward",
    "Tole",
    "Father Name",
    "Mother Name",
    "Guardian Name",
    "Guardian Relation",
    "Guardian Contact",
    "Emergency Contact",
    "Residential Status",
    "Hostel",
    "Room",
    "Bed No",
    "Bus",
    "Pickup Point",
    "Status"
]

TEACHER_EXCEL_COLUMNS = [
    "Employee ID",
    "Name Nepali",
    "Name English",
    "Position",
    "Subject",
    "Level",
    "Qualification",
    "Experience",
    "Phone",
    "Email",
    "Appointment Date",
    "Employment Type",
    "Status"
]

def generate_student_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students Template"
    
    # Header styling
    header_fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center")
    
    ws.append(STUDENT_EXCEL_COLUMNS)
    for col in ws.iter_cols(min_row=1, max_row=1):
        for cell in col:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align
            
    # Sample row
    sample_row = [
        "STU-001", "ADM-2083-001", "REG-83-01", "0119010001", "सन्देश कार्की", "Sandesh Karki",
        "कक्षा १", "A", 1, "छात्र", "2076/05/15", "इटहरी-१९, सुनसरी", "सुनसरी",
        "इटहरी", "१९", "भवानीपुर", "राम बहादुर कार्की", "सीता कार्की", "राम बहादुर कार्की",
        "बुबा", "9842000001", "9842000002", "दिवा", "", "", "", "", "", "सक्रिय"
    ]
    ws.append(sample_row)
    
    # Auto column width
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_teacher_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Teachers Template"
    
    header_fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center")
    
    ws.append(TEACHER_EXCEL_COLUMNS)
    for col in ws.iter_cols(min_row=1, max_row=1):
        for cell in col:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align
            
    sample_row = [
        "EMP-001", "हरि प्रसाद अधिकारी", "Hari Prasad Adhikari", "मावि शिक्षक",
        "गणित", "माध्यमिक", "M.Sc. Mathematics", "१० वर्ष", "9842111111",
        "hari@shahidsmriti.edu.np", "2072/01/10", "स्थायी", "सक्रिय"
    ]
    ws.append(sample_row)
    
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def validate_and_parse_student_excel(file_bytes: bytes) -> Dict[str, Any]:
    """
    10-Step validation workflow as specified:
    Step 1: Read file
    Step 2: Validate headers
    Step 3: Validate rows
    Step 4: Detect duplicates
    Step 5: Validate Class
    Step 6: Validate Section
    Step 7: Validate Roll No
    Step 8: Validate phone
    Step 9: Validate date
    Step 10: Display Preview / Errors
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "rows": [],
        "total_rows": 0,
        "valid_rows_count": 0
    }
    
    try:
        # Step 1: Read file
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"फाइल पढ्न सकिएन: अमान्य Excel फाइल ({str(e)})")
        return result
        
    # Step 2: Validate headers
    headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
    missing_headers = [col for col in STUDENT_EXCEL_COLUMNS if col not in headers]
    if missing_headers:
        result["valid"] = False
        result["errors"].append(f"हेडर मिलेन! निम्न कोलमहरू छुटेका छन्: {', '.join(missing_headers)}")
        return result
        
    header_index = {h: idx for idx, h in enumerate(headers)}
    
    # Load class mapping
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes")
    classes_db = cursor.fetchall()
    class_name_map = {}
    for c in classes_db:
        class_name_map[str(c["class_numeric"])] = c["id"]
        class_name_map[f"कक्षा {c['class_numeric']}"] = c["id"]
        class_name_map[f"Class {c['class_numeric']}"] = c["id"]
        class_name_map[c["class_name_ne"]] = c["id"]

    cursor.execute("SELECT student_id, admission_no FROM students")
    existing_students = cursor.fetchall()
    existing_ids = {s["student_id"] for s in existing_students}
    existing_admissions = {s["admission_no"] for s in existing_students}
    conn.close()
    
    seen_file_ids = set()
    seen_file_admissions = set()
    
    # Process rows (Step 3 to 9)
    row_num = 1
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_num += 1
        if not any(row):
            continue  # empty row
            
        result["total_rows"] += 1
        row_dict = {}
        for col_name in STUDENT_EXCEL_COLUMNS:
            idx = header_index.get(col_name)
            val = row[idx] if idx is not None and idx < len(row) else ""
            row_dict[col_name] = str(val).strip() if val is not None else ""
            
        row_errors = []
        
        # Step 4: Duplicate checks
        stu_id = row_dict["Student ID"]
        adm_no = row_dict["Admission No"]
        
        if not stu_id:
            row_errors.append("Student ID खाली छ।")
        elif stu_id in existing_ids:
            row_errors.append(f"Student ID '{stu_id}' पहिले नै दर्ता छ।")
        elif stu_id in seen_file_ids:
            row_errors.append(f"Excel भित्र दोहोरिएको Student ID '{stu_id}'।")
        else:
            seen_file_ids.add(stu_id)
            
        if not adm_no:
            row_errors.append("Admission No खाली छ।")
        elif adm_no in existing_admissions:
            row_errors.append(f"Admission No '{adm_no}' पहिले नै दर्ता छ।")
        elif adm_no in seen_file_admissions:
            row_errors.append(f"Excel भित्र दोहोरिएको Admission No '{adm_no}'।")
        else:
            seen_file_admissions.add(adm_no)
            
        # Step 5: Validate Class
        cls_raw = row_dict["Class"]
        class_id = class_name_map.get(cls_raw)
        if not class_id:
            row_errors.append(f"अमान्य कक्षा: '{cls_raw}' (१ देखि १२ हुनुपर्दछ)")
        row_dict["class_id"] = class_id
        
        # Step 6: Validate Section
        sec_raw = row_dict["Section"].upper()
        if sec_raw and sec_raw not in ["A", "B", "C", "D"]:
            row_errors.append(f"अमान्य Section: '{sec_raw}'")
        row_dict["Section"] = sec_raw or "A"
        
        # Step 7: Validate Roll No
        roll_raw = row_dict["Roll No"]
        try:
            roll_int = int(float(roll_raw))
            if roll_int <= 0:
                row_errors.append("Roll No १ वा सो भन्दा बढी हुनुपर्छ।")
            row_dict["roll_no_clean"] = roll_int
        except Exception:
            row_errors.append(f"अमान्य Roll No: '{roll_raw}'")
            
        # Step 8: Validate Phone
        phone = row_dict["Guardian Contact"]
        clean_phone = re.sub(r'[^0-9]', '', phone)
        if not phone or len(clean_phone) < 9 or len(clean_phone) > 14:
            row_errors.append(f"Guardian Contact अमान्य फोन नम्बर: '{phone}'")
            
        # Step 9: Validate Date of Birth
        dob = row_dict["Date of Birth"]
        if not dob or len(dob) < 4:
            row_errors.append(f"जन्म मिति अमान्य: '{dob}'")
            
        # Required names
        if not row_dict["Name Nepali"]:
            row_errors.append("विद्यार्थीको नेपाली नाम अनिवार्य छ।")
        if not row_dict["Name English"]:
            row_errors.append("विद्यार्थीको अंग्रेजी नाम अनिवार्य छ।")
            
        row_dict["_row_number"] = row_num
        row_dict["_errors"] = row_errors
        
        if row_errors:
            result["valid"] = False
            for err in row_errors:
                result["errors"].append(f"पंक्ति (Row) {row_num}: {err}")
        else:
            result["valid_rows_count"] += 1
            
        result["rows"].append(row_dict)
        
    return result

def export_students_to_excel(students_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "विद्यार्थी विवरण"
    
    header_fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center")
    
    headers = [
        "क्र.सं.", "Student ID", "भर्ना नं.", "रोल नं.", "इमिस कोड (EMIS)", "विद्यार्थीको नाम", "English Name",
        "कक्षा", "Section", "लिङ्ग", "जन्म मिति", "अभिभावक", "सम्पर्क नं.", "ठेगाना",
        "आवासीय स्थिति", "छात्रावास", "बस", "स्थिति"
    ]
    ws.append(headers)
    for col in ws.iter_cols(min_row=1, max_row=1):
        for cell in col:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align
            
    for idx, s in enumerate(students_list, start=1):
        row = [
            idx,
            s.get("student_id", ""),
            s.get("admission_no", ""),
            s.get("roll_no", ""),
            s.get("emis_code", ""),
            s.get("name_nepali", ""),
            s.get("name_english", ""),
            s.get("class_name", ""),
            s.get("section_name", ""),
            s.get("gender", ""),
            s.get("date_of_birth", ""),
            s.get("guardian_name", ""),
            s.get("guardian_phone", ""),
            s.get("address", ""),
            s.get("residential_status", ""),
            s.get("hostel_name", ""),
            s.get("bus_number", ""),
            s.get("status", "")
        ]
        ws.append(row)
        
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def _style_excel(ws, headers: List[str], data_rows: List[List[Any]]) -> io.BytesIO:
    header_fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center")
    
    ws.append(headers)
    for col in ws.iter_cols(min_row=1, max_row=1):
        for cell in col:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align
            
    for row in data_rows:
        ws.append(row)
        
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    output = io.BytesIO()
    ws.parent.save(output)
    output.seek(0)
    return output

def export_teachers_to_excel(teachers_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "शिक्षक विवरण"
    headers = ["क्र.सं.", "Employee ID", "शिक्षकको नाम (नेपाली)", "Name (English)", "पद (Position)", "विषय (Subject)", "तह (Level)", "शैक्षिक योग्यता", "अनुभव", "फोन नं.", "इमेल", "नियुक्ति मिति", "प्रकार", "स्थिति"]
    rows = []
    for idx, t in enumerate(teachers_list, start=1):
        rows.append([
            idx, t.get("employee_id", ""), t.get("name_nepali", ""), t.get("name_english", ""),
            t.get("position", ""), t.get("subject", ""), t.get("level", ""), t.get("qualification", ""),
            t.get("experience", ""), t.get("phone", ""), t.get("email", ""), t.get("appointment_date", ""),
            t.get("employment_type", "स्थायी"), t.get("status", "सक्रिय")
        ])
    return _style_excel(ws, headers, rows)

def export_staff_to_excel(staff_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "कर्मचारी विवरण"
    headers = ["क्र.सं.", "Employee ID", "कर्मचारीको नाम (नेपाली)", "Name (English)", "पद (Position)", "शाखा (Department)", "शैक्षिक योग्यता", "सम्पर्क फोन", "इमेल", "नियुक्ति मिति", "प्रकार", "स्थिति"]
    rows = []
    for idx, s in enumerate(staff_list, start=1):
        rows.append([
            idx, s.get("employee_id", ""), s.get("name_nepali", ""), s.get("name_english", ""),
            s.get("position", ""), s.get("department", ""), s.get("qualification", ""),
            s.get("phone", ""), s.get("email", ""), s.get("appointment_date", ""),
            s.get("employment_type", "स्थायी"), s.get("status", "सक्रिय")
        ])
    return _style_excel(ws, headers, rows)

def export_admissions_to_excel(admissions_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "भर्ना आवेदनहरू"
    headers = ["क्र.सं.", "आवेदन मिति", "विद्यार्थीको नाम", "जन्म मिति", "लिङ्ग", "आवेदन कक्षा", "साविक विद्यालय", "अभिभावकको नाम", "सम्पर्क फोन", "इमेल", "ठेगाना", "स्थिति", "कैफियत"]
    rows = []
    for idx, a in enumerate(admissions_list, start=1):
        rows.append([
            idx, str(a.get("created_at", ""))[:10], a.get("student_name", ""), a.get("dob", ""),
            a.get("gender", ""), a.get("applying_class", ""), a.get("previous_school", ""),
            a.get("parent_name", ""), a.get("mobile", ""), a.get("email", ""), a.get("address", ""),
            a.get("status", "नयाँ"), a.get("remarks", "")
        ])
    return _style_excel(ws, headers, rows)

def export_notices_to_excel(notices_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "सूचना विवरण"
    headers = ["क्र.सं.", "शीर्षक (नेपाली)", "वर्ग (Category)", "प्रकाशित मिति", "म्याद सकिने मिति", "मुख्य/टिकर", "संलग्न फाइल", "स्थिति", "विवरण"]
    rows = []
    for idx, n in enumerate(notices_list, start=1):
        rows.append([
            idx, n.get("title_ne", ""), n.get("category", "सामान्य"), n.get("publish_date", ""),
            n.get("expiry_date", ""), "हो" if n.get("featured") else "होइन",
            n.get("attachment", ""), n.get("status", "सक्रिय"), n.get("description_ne", "")
        ])
    return _style_excel(ws, headers, rows)

def export_publications_to_excel(pubs_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "प्रकाशन विवरण"
    headers = ["क्र.सं.", "प्रकाशन शीर्षक", "वर्ग (Category)", "फाइल प्रकार", "फाइल लिङ्क", "प्रकाशित मिति", "स्थिति", "विवरण"]
    rows = []
    for idx, p in enumerate(pubs_list, start=1):
        rows.append([
            idx, p.get("title", ""), p.get("category", ""), p.get("file_type", "PDF"),
            p.get("file_url", ""), p.get("publish_date", ""), p.get("status", "सक्रिय"),
            p.get("description", "")
        ])
    return _style_excel(ws, headers, rows)

def export_homework_to_excel(hw_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "गृहकार्य विवरण"
    headers = ["क्र.सं.", "कक्षा", "विषय", "गृहकार्य शीर्षक", "शिक्षक", "तोकिएको मिति", "बुझाउने मिति", "स्थिति", "प्रश्नावली", "विस्तृत विवरण"]
    rows = []
    for idx, h in enumerate(hw_list, start=1):
        q_raw = h.get("questions")
        q_text = ""
        if q_raw:
            try:
                import json
                ql = json.loads(q_raw) if isinstance(q_raw, str) else q_raw
                q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(ql)])
            except Exception:
                q_text = str(q_raw)
        rows.append([
            idx, h.get("class_name_ne", ""), h.get("subject_name", ""), h.get("title", ""),
            h.get("teacher_name", ""), h.get("assigned_date", ""), h.get("due_date", ""),
            h.get("status", "सक्रिय"), q_text, h.get("description", "")
        ])
    return _style_excel(ws, headers, rows)

def export_calendar_to_excel(events_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "शैक्षिक क्यालेन्डर"
    headers = ["क्र.सं.", "कार्यक्रम शीर्षक", "प्रकार", "सुरु मिति", "अन्तिम मिति", "सार्वजनिक बिदा?", "विवरण"]
    rows = []
    for idx, e in enumerate(events_list, start=1):
        rows.append([
            idx, e.get("title", ""), e.get("event_type", ""), e.get("start_date", ""),
            e.get("end_date", ""), "हो" if e.get("is_holiday") else "होइन",
            e.get("description", "")
        ])
    return _style_excel(ws, headers, rows)

def export_attendance_to_excel(attendance_list: List[Dict[str, Any]], date_str: str = "") -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"हाजिरी_{date_str}"
    headers = ["क्र.सं.", "मिति", "कक्षा", "Section", "रोल नं.", "विद्यार्थीको नाम", "हाजिरी स्थिति", "कैफियत"]
    rows = []
    for idx, a in enumerate(attendance_list, start=1):
        rows.append([
            idx, a.get("attendance_date", date_str), a.get("class_name_ne", ""),
            a.get("section_name", ""), a.get("roll_no", ""), a.get("name_nepali", ""),
            a.get("status", "PRESENT"), a.get("remarks", "")
        ])
    return _style_excel(ws, headers, rows)

def export_transport_to_excel(buses_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "यातायात बस विवरण"
    headers = ["क्र.सं.", "बस नम्बर", "गाडी नम्बर (Vehicle No)", "रुट विवरण", "चालकको नाम", "चालक सम्पर्क", "सिट क्षमता", "स्थिति"]
    rows = []
    for idx, b in enumerate(buses_list, start=1):
        rows.append([
            idx, b.get("bus_number", ""), b.get("vehicle_number", ""), b.get("route_name", ""),
            b.get("driver_name", ""), b.get("driver_phone", ""), b.get("capacity", ""),
            b.get("status", "सक्रिय")
        ])
    return _style_excel(ws, headers, rows)

def export_hostels_to_excel(hostels_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "छात्रावास विवरण"
    headers = ["क्र.सं.", "छात्रावासको नाम", "English Name", "वर्ग (Gender)", "कुल क्षमता", "वार्डेनको नाम", "वार्डेन सम्पर्क", "स्थिति"]
    rows = []
    for idx, h in enumerate(hostels_list, start=1):
        rows.append([
            idx, h.get("name_ne", ""), h.get("name_en", ""), h.get("gender_type", ""),
            h.get("capacity", ""), h.get("warden_name", ""), h.get("warden_phone", ""),
            h.get("status", "सक्रिय")
        ])
    return _style_excel(ws, headers, rows)

def export_facilities_to_excel(facilities_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "विद्यालय सुविधाहरू"
    headers = ["क्र.सं.", "सुविधाको नाम", "क्रम", "आइकन", "तस्विर", "स्थिति", "विवरण"]
    rows = []
    for idx, f in enumerate(facilities_list, start=1):
        rows.append([
            idx, f.get("title", "") or f.get("title_ne", ""), f.get("display_order", "") or f.get("order_index", ""),
            f.get("icon", ""), f.get("image", ""), f.get("status", "सक्रिय"),
            f.get("description", "") or f.get("description_ne", "")
        ])
    return _style_excel(ws, headers, rows)

def export_committee_to_excel(members_list: List[Dict[str, Any]], title: str = "समिति विवरण") -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title
    headers = ["क्र.सं.", "नाम", "पद (Position)", "सम्पर्क फोन", "कार्यकाल", "क्रम", "स्थिति"]
    rows = []
    for idx, m in enumerate(members_list, start=1):
        rows.append([
            idx, m.get("name", ""), m.get("position", ""), m.get("phone", ""),
            m.get("term", ""), m.get("order_index", idx), m.get("status", "सक्रिय")
        ])
    return _style_excel(ws, headers, rows)


def export_news_to_excel(news_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "समाचार विवरण"
    headers = ["क्र.सं.", "शीर्षक", "वर्ग", "मिति", "तस्विर", "स्थिति", "पूर्ण विवरण"]
    rows = []
    for idx, n in enumerate(news_list, start=1):
        rows.append([
            idx, n.get("title_ne", ""), n.get("category", "कार्यक्रम"),
            n.get("publish_date", ""), n.get("image", ""), n.get("status", "सक्रिय"),
            n.get("content_ne", "")
        ])
    return _style_excel(ws, headers, rows)


def export_results_to_excel(results_list: List[Dict[str, Any]], exam_name: str = "परीक्षा नतिजा") -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "नतिजा लेजर"
    headers = ["क्र.सं.", "विद्यार्थी ID", "रोल नं.", "विद्यार्थीको नाम", "कक्षा", "विषय", "पूर्णाङ्क", "उत्तीर्णाङ्क", "सैद्धान्तिक", "प्रयोगात्मक", "कुल प्राप्ताङ्क", "ग्रेड", "ग्रेड पोइन्ट (GP)", "कैफियत"]
    rows = []
    for idx, r in enumerate(results_list, start=1):
        rows.append([
            idx, r.get("student_id", "") or r.get("stu_code", ""), r.get("roll_no", ""),
            r.get("name_nepali", "") or r.get("student_name", ""), r.get("class_name_ne", ""),
            r.get("subject_name_ne", ""), r.get("full_marks", 100), r.get("pass_marks", 35),
            r.get("theory_obtained", ""), r.get("practical_obtained", ""),
            r.get("total_obtained", ""), r.get("grade", ""), r.get("grade_point", ""),
            r.get("remarks", "")
        ])
    return _style_excel(ws, headers, rows)


def export_contact_messages_to_excel(messages_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "सम्पर्क सन्देशहरू"
    headers = ["क्र.सं.", "पठाउनेको नाम", "सम्पर्क फोन", "ईमेल", "विषय", "प्राप्त मिति", "सन्देश विवरण"]
    rows = []
    for idx, m in enumerate(messages_list, start=1):
        rows.append([
            idx, m.get("name", ""), m.get("phone", ""), m.get("email", ""),
            m.get("subject", ""), m.get("created_at", "")[:19] if m.get("created_at") else "",
            m.get("message", "")
        ])
    return _style_excel(ws, headers, rows)


def export_leave_applications_to_excel(leaves_list: List[Dict[str, Any]]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "बिदा निवेदनहरू"
    headers = ["क्र.सं.", "विद्यार्थीको नाम", "कक्षा", "रोल नं.", "निवेदकको नाम", "सम्पर्क फोन", "शुरु मिति", "अन्तिम मिति", "जम्मा दिन", "बिदाको कारण", "स्थिति", "कैफियत"]
    rows = []
    for idx, l in enumerate(leaves_list, start=1):
        rows.append([
            idx, l.get("student_name", ""), l.get("class_name_ne", ""), l.get("roll_no", ""),
            l.get("applicant_name", ""), l.get("applicant_phone", ""),
            l.get("start_date", ""), l.get("end_date", ""), l.get("total_days", 1),
            l.get("reason", ""), l.get("status", "विचाराधीन"), l.get("review_remarks", "")
        ])
    return _style_excel(ws, headers, rows)

