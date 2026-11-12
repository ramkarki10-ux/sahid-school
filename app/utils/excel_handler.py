import io
import re
from typing import List, Dict, Any, Tuple, Optional
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

NP_TO_EN_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def parse_int_nepali(val: Any) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip().translate(NP_TO_EN_DIGITS)
    m = re.search(r'\d+', s)
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            return None
    return None

def normalize_header_key(h: str) -> str:
    h = (h or "").strip().lower().translate(NP_TO_EN_DIGITS)
    return re.sub(r'[\s_\-\.\(\)\,\/]+', '', h)

SMART_STUDENT_TEMPLATE_COLUMNS = [
    "S.N.",
    "विद्यार्थीको नाम",
    "थर",
    "कक्षा",
    "रोल नम्बर",
    "लिङ्ग",
    "अभिभावकको नाम",
    "सम्पर्क फोन",
    "ठेगाना"
]

def generate_student_template() -> io.BytesIO:
    """
    Generates standard Excel Template for Student Import.
    Mandatory columns: विद्यार्थीको नाम, थर, कक्षा (१-१२), रोल नम्बर.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student_Import_Template"
    
    # Title Banner
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = "सहिद स्मृति आवासीय माध्यमिक विद्यालय — विद्यार्थी विवरण आयात ढाँचा (Student Import Template)"
    title_cell.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    title_cell.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    # Instruction row
    ws.merge_cells("A2:I2")
    info_cell = ws["A2"]
    info_cell.value = "* अनिवार्य स्तम्भहरू: विद्यार्थीको नाम, थर, कक्षा (१ देखि १२) र रोल नम्बर ।"
    info_cell.fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")
    info_cell.font = Font(name="Segoe UI", size=10, italic=True, color="92400E")
    info_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 22

    # Headers
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.append(SMART_STUDENT_TEMPLATE_COLUMNS)
    ws.row_dimensions[3].height = 28
    for col in ws.iter_cols(min_row=3, max_row=3):
        for cell in col:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align

    # Sample rows specified by user
    sample_data = [
        [1, "राम", "काफ्ले", 1, 1, "छात्र", "हरि काफ्ले", "9842000001", "इटहरी-१९, सुनसरी"],
        [2, "सीता", "कार्की", 1, 2, "छात्रा", "राम बहादुर कार्की", "9842000002", "इटहरी-१९, सुनसरी"],
        [3, "हरि", "पोखरेल", 2, 1, "छात्र", "गणेश पोखरेल", "9842000003", "इटहरी-१९, सुनसरी"],
        [4, "अनिता", "राई", 8, 5, "छात्रा", "धन बहादुर राई", "9842000004", "इटहरी-१९, सुनसरी"],
        [5, "रोहित", "कार्की", 10, 12, "छात्र", "राम बहादुर कार्की", "9842000005", "इटहरी-१९, सुनसरी"]
    ]

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for row_vals in sample_data:
        ws.append(row_vals)
        r_idx = ws.max_row
        ws.row_dimensions[r_idx].height = 22
        for c_idx in range(1, len(row_vals) + 1):
            c = ws.cell(row=r_idx, column=c_idx)
            c.border = border_thin
            c.font = Font(name="Segoe UI", size=10)
            if c_idx in (1, 4, 5):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 20, 16, 12, 14, 12, 24, 18, 26]
    for idx, w in enumerate(widths, start=1):
        col_letter = openpyxl.utils.get_column_letter(idx)
        ws.column_dimensions[col_letter].width = w

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
            
    # Sample Row
    ws.append([
        "TCH-001",
        "राम प्रसाद अधिकारी",
        "Ram Prasad Adhikari",
        "माध्यमिक शिक्षक",
        "गणित",
        "माध्यमिक",
        "M.Sc. Mathematics",
        "१० वर्ष",
        "9841234567",
        "ram.adhikari@school.edu.np",
        "२०७०-०१-१५",
        "स्थायी",
        "सक्रिय"
    ])
    
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def validate_and_parse_student_excel(file_bytes: bytes) -> Dict[str, Any]:
    """
    Validates and parses uploaded student Excel file.
    Supports both:
    1) Simple 5-column format: S.N., विद्यार्थीको नाम, थर, कक्षा, रोल नम्बर
    2) Full comprehensive format with English or Nepali headers
    Returns preview data with categorized counts (Total, New, Existing/Duplicate, Errors).
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "rows": [],
        "total_rows": 0,
        "new_count": 0,
        "duplicate_count": 0,
        "error_count": 0,
        "valid_rows_count": 0
    }

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Excel फाइल खोल्न सकिएन। कृपया मान्य .xlsx वा .xls ढाँचाको फाइल प्रयोग गर्नुहोस् ({str(e)})")
        return result

    # Find the header row (skip title banners if any)
    header_row_idx = None
    headers_raw = []
    
    for r_idx, row in enumerate(ws.iter_rows(max_row=6, values_only=True), start=1):
        vals = [str(c).strip() for c in row if c is not None and str(c).strip()]
        normalized = [normalize_header_key(v) for v in vals]
        # Check if this row looks like header
        if any("कक्षा" in v or "class" in v or "grade" in v for v in normalized) and \
           any("नाम" in v or "name" in v for v in normalized):
            header_row_idx = r_idx
            headers_raw = [str(c).strip() if c is not None else "" for c in row]
            break

    if not header_row_idx:
        # Default to first row
        header_row_idx = 1
        headers_raw = [str(cell.value).strip() if cell.value is not None else "" for cell in ws[1]]

    # Map headers to standard keys
    key_map = {}
    for idx, h in enumerate(headers_raw):
        nk = normalize_header_key(h)
        if any(w in nk for w in ["विद्यार्थीकोनाम", "पहिलोनाम", "नाम", "firstname", "namenepali", "studentname"]):
            key_map.setdefault("first_name", idx)
        elif any(w in nk for w in ["थर", "lastname", "surname"]):
            key_map.setdefault("last_name", idx)
        elif any(w in nk for w in ["कक्षा", "class", "grade"]):
            key_map.setdefault("class", idx)
        elif any(w in nk for w in ["रोलनम्बर", "रोलनं", "रोलन", "rollno", "rollnumber", "roll"]):
            key_map.setdefault("roll_no", idx)
        elif any(w in nk for w in ["क्रसं", "sn", "sno", "sn"]):
            key_map.setdefault("sn", idx)
        elif any(w in nk for w in ["लिङ्ग", "gender", "sex"]):
            key_map.setdefault("gender", idx)
        elif any(w in nk for w in ["अभिभावककोनाम", "अभिभावक", "guardianname", "guardian", "fathername", "बुबाकोनाम"]):
            key_map.setdefault("guardian_name", idx)
        elif any(w in nk for w in ["सम्पर्कफोन", "सम्पर्क", "फोन", "मोबाइल", "guardiancontact", "guardianphone", "phone", "mobile"]):
            key_map.setdefault("guardian_phone", idx)
        elif any(w in nk for w in ["ठेगाना", "address"]):
            key_map.setdefault("address", idx)
        elif any(w in nk for w in ["studentid", "विद्यार्थीआइडी", "student_id"]):
            key_map.setdefault("student_id", idx)
        elif any(w in nk for w in ["admissionno", "भर्नानं", "admission_no"]):
            key_map.setdefault("admission_no", idx)
        elif any(w in nk for w in ["section", "सेक्सन"]):
            key_map.setdefault("section", idx)

    # Validate essential headers: Name, Class, Roll No
    missing_critical = []
    if "first_name" not in key_map:
        missing_critical.append("विद्यार्थीको नाम (First Name)")
    if "class" not in key_map:
        missing_critical.append("कक्षा (Class)")
    if "roll_no" not in key_map:
        missing_critical.append("रोल नम्बर (Roll Number)")

    if missing_critical:
        result["valid"] = False
        result["errors"].append(f"Excel मा अनिवार्य कोलमहरू फेला परेनन्: {', '.join(missing_critical)}। कृपया उपलब्ध Template प्रयोग गर्नुहोस्।")
        return result

    # Load classes from DB
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_name_ne, class_numeric FROM classes")
    classes_db = cursor.fetchall()
    class_num_to_id = {}
    class_num_to_name = {}
    for c in classes_db:
        num = c["class_numeric"]
        class_num_to_id[num] = c["id"]
        class_num_to_name[num] = c["class_name_ne"]

    # Load existing students to check duplicates
    cursor.execute("SELECT id, student_id, admission_no, name_nepali, class_id, roll_no FROM students WHERE status = 'सक्रिय'")
    existing_students = cursor.fetchall()
    conn.close()

    existing_by_class_roll = {}
    for s in existing_students:
        key = (s["class_id"], s["roll_no"])
        existing_by_class_roll[key] = dict(s)

    seen_in_file = set()
    row_num = header_row_idx

    for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
        row_num += 1
        if not any(row):
            continue

        result["total_rows"] += 1
        row_errors = []

        # Extract values
        def get_val(k):
            idx = key_map.get(k)
            if idx is not None and idx < len(row) and row[idx] is not None:
                return str(row[idx]).strip()
            return ""

        first_name = get_val("first_name")
        last_name = get_val("last_name")
        class_raw = get_val("class")
        roll_raw = get_val("roll_no")
        gender_raw = get_val("gender") or "अन्य"
        guardian_name = get_val("guardian_name")
        guardian_phone = get_val("guardian_phone")
        address = get_val("address") or "इटहरी-१९, सुनसरी"
        section = get_val("section") or "A"
        stu_id_given = get_val("student_id")
        adm_no_given = get_val("admission_no")

        # 1. Name validation
        if not first_name:
            row_errors.append("विद्यार्थीको नाम अनिवार्य छ।")
        
        # Build full name
        if last_name:
            full_name = f"{first_name} {last_name}".strip()
        else:
            full_name = first_name

        # 2. Class validation (1 to 12)
        class_numeric = parse_int_nepali(class_raw)
        class_id = None
        class_name = f"कक्षा {class_raw}"
        if class_numeric is None or class_numeric < 1 or class_numeric > 12:
            row_errors.append(f"कक्षा १ देखि १२ सम्म मात्र हुनुपर्दछ (प्रविष्ट: '{class_raw}')")
        else:
            class_id = class_num_to_id.get(class_numeric)
            class_name = class_num_to_name.get(class_numeric, f"कक्षा {class_numeric}")

        # 3. Roll Number validation
        roll_no = parse_int_nepali(roll_raw)
        if roll_no is None or roll_no <= 0:
            row_errors.append(f"रोल नम्बर अमान्य: '{roll_raw}' (१ वा सो भन्दा बढी हुनुपर्छ)")

        # 4. Duplicate within this uploaded file check
        file_dup_key = (class_numeric, roll_no)
        if class_numeric and roll_no:
            if file_dup_key in seen_in_file:
                row_errors.append(f"Excel फाइलभित्रै कक्षा {class_numeric} मा रोल नम्बर {roll_no} दोहोरिएको छ!")
            else:
                seen_in_file.add(file_dup_key)

        # 5. Check against existing database
        row_status = "NEW"
        existing_info = None
        if class_id and roll_no:
            db_match = existing_by_class_roll.get((class_id, roll_no))
            if db_match:
                existing_info = db_match
                if db_match["name_nepali"].strip() == full_name.strip():
                    row_status = "EXISTING"
                else:
                    row_status = "DUPLICATE_ROLL"
                    result["warnings"].append(
                        f"पंक्ति {row_num}: कक्षा {class_name} मा रोल नं. {roll_no} मा पहिले नै '{db_match['name_nepali']}' दर्ता छ। आयात गरेमा अद्यावधिक हुनेछ।"
                    )

        # Permanent IDs
        clean_class_num = class_numeric or 0
        clean_roll = roll_no or 0
        final_stu_id = stu_id_given or (existing_info["student_id"] if existing_info else f"STU-{clean_class_num:02d}-{clean_roll:03d}")
        final_adm_no = adm_no_given or (existing_info["admission_no"] if existing_info else f"ADM-2083-{clean_class_num:02d}-{clean_roll:03d}")

        if row_errors:
            row_status = "ERROR"
            result["error_count"] += 1
            result["valid"] = False
            for err in row_errors:
                result["errors"].append(f"पंक्ति {row_num} ({full_name or 'विद्यार्थी'}): {err}")
        elif row_status == "NEW":
            result["new_count"] += 1
            result["valid_rows_count"] += 1
        else:
            result["duplicate_count"] += 1
            result["valid_rows_count"] += 1

        parsed_row = {
            "row_number": row_num,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "name_nepali": full_name,
            "name_english": full_name,
            "class_raw": class_raw,
            "class_numeric": class_numeric,
            "class_name": class_name,
            "class_id": class_id,
            "section": section,
            "roll_no": roll_no,
            "gender": gender_raw,
            "guardian_name": guardian_name or "अभिभावक",
            "guardian_phone": guardian_phone or "",
            "address": address,
            "student_id": final_stu_id,
            "admission_no": final_adm_no,
            "status": row_status,
            "errors": row_errors,
            "is_valid": len(row_errors) == 0
        }
        result["rows"].append(parsed_row)

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


def export_daily_attendance_excel(attendance_rows: List[Dict[str, Any]], date_str: str, class_name: str = "सबै कक्षा") -> io.BytesIO:
    """
    Exports comprehensive daily student attendance to Excel with colors and styling.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Daily_{date_str}"

    # Title Banner
    ws.merge_cells("A1:J1")
    t1 = ws["A1"]
    t1.value = "सहिद स्मृति आवासीय माध्यमिक विद्यालय — दैनिक विद्यार्थी हाजिरी विवरण"
    t1.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    t1.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # Sub-header info
    ws.merge_cells("A2:J2")
    t2 = ws["A2"]
    t2.value = f"हाजिरी मिति: {date_str}   |   कक्षा: {class_name}   |   जम्मा रेकर्ड: {len(attendance_rows)} जना"
    t2.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    t2.font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    headers = [
        "क्र.सं.", "मिति", "कक्षा", "रोल नं.", "विद्यार्थीको नाम", "थर",
        "हाजिरी स्थिति", "शिक्षक / रेकर्डर", "दर्ता समय", "कैफियत"
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 26

    h_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    h_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.fill = h_fill
        cell.font = h_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    fill_present = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    font_present = Font(name="Segoe UI", size=10, bold=True, color="166534")

    fill_absent = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_absent = Font(name="Segoe UI", size=10, bold=True, color="991B1B")

    fill_leave = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    font_leave = Font(name="Segoe UI", size=10, bold=True, color="92400E")

    for idx, a in enumerate(attendance_rows, start=1):
        full_name = a.get("name_nepali") or a.get("student_name") or ""
        parts = full_name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        raw_st = (a.get("status") or "PRESENT").upper()
        if raw_st in ("PRESENT", "उपस्थित"):
            disp_st = "उपस्थित (Present)"
            st_fill = fill_present
            st_font = font_present
        elif raw_st in ("ABSENT", "अनुपस्थित"):
            disp_st = "अनुपस्थित (Absent)"
            st_fill = fill_absent
            st_font = font_absent
        else:
            disp_st = "बिदा (Leave)"
            st_fill = fill_leave
            st_font = font_leave

        row_vals = [
            idx,
            a.get("attendance_date", date_str),
            a.get("class_name_ne") or a.get("class_name") or class_name,
            a.get("roll_no", ""),
            first_name,
            last_name,
            disp_st,
            a.get("recorded_by_name") or a.get("teacher_name") or "शिक्षक",
            str(a.get("created_at") or "")[:19],
            a.get("remark") or a.get("remarks") or ""
        ]
        ws.append(row_vals)
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 20

        for c_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_num, column=c_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if c_idx in (1, 2, 4):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c_idx == 7:
                cell.fill = st_fill
                cell.font = st_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 14, 14, 10, 18, 16, 20, 22, 20, 24]
    for c_idx, w in enumerate(widths, start=1):
        col_letter = openpyxl.utils.get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_monthly_attendance_excel(
    matrix_rows: List[Dict[str, Any]],
    month_name: str,
    year_str: str,
    class_name: str,
    days_count: int = 30
) -> io.BytesIO:
    """
    Exports monthly student attendance matrix with daily columns (Day 1 to 30/31).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Monthly_{month_name}"

    total_cols = 3 + days_count + 4  # SN, Roll, Name + Days + Present, Absent, Leave, %

    # Title
    last_col_letter = openpyxl.utils.get_column_letter(total_cols)
    ws.merge_cells(f"A1:{last_col_letter}1")
    t1 = ws["A1"]
    t1.value = f"सहिद स्मृति आवासीय माध्यमिक विद्यालय — मासिक विद्यार्थी हाजिरी लेजर (महिना: {month_name} {year_str})"
    t1.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    t1.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # Subtitle
    ws.merge_cells(f"A2:{last_col_letter}2")
    t2 = ws["A2"]
    t2.value = f"कक्षा: {class_name}   |   महिना: {month_name}   |   शैक्षिक सत्र: {year_str}   |   जम्मा विद्यार्थी: {len(matrix_rows)} जना"
    t2.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    t2.font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    headers = ["क्र.सं.", "रोल नं.", "विद्यार्थीको पूरा नाम"]
    for d in range(1, days_count + 1):
        headers.append(str(d))
    headers.extend(["उपस्थित", "अनुपस्थित", "बिदा", "हाजिरी %"])

    ws.append(headers)
    ws.row_dimensions[3].height = 26

    h_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    h_font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
    for c_idx in range(1, total_cols + 1):
        cell = ws.cell(row=3, column=c_idx)
        cell.fill = h_fill
        cell.font = h_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    fill_p = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    fill_a = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    fill_l = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    for idx, s in enumerate(matrix_rows, start=1):
        row_vals = [
            idx,
            s.get("roll_no", ""),
            s.get("name_nepali") or s.get("student_name") or ""
        ]
        daily_map = s.get("daily_status", {})
        for d in range(1, days_count + 1):
            st = daily_map.get(d, "-")
            row_vals.append(st)

        p_days = s.get("present_days", 0)
        a_days = s.get("absent_days", 0)
        l_days = s.get("leave_days", 0)
        total_open = p_days + a_days + l_days
        pct = round((p_days / total_open * 100), 1) if total_open > 0 else 0

        row_vals.extend([p_days, a_days, l_days, f"{pct}%"])
        ws.append(row_vals)
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 20

        for c_idx in range(1, total_cols + 1):
            cell = ws.cell(row=r_num, column=c_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if c_idx in (1, 2):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c_idx == 3:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif 4 <= c_idx <= 3 + days_count:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                val_str = str(cell.value or "")
                if val_str == "P":
                    cell.fill = fill_p
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="166534")
                elif val_str == "A":
                    cell.fill = fill_a
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="991B1B")
                elif val_str == "L":
                    cell.fill = fill_l
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color="92400E")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Segoe UI", size=9, bold=True)

    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 24
    for d in range(1, days_count + 1):
        c_letter = openpyxl.utils.get_column_letter(3 + d)
        ws.column_dimensions[c_letter].width = 4.5
    ws.column_dimensions[openpyxl.utils.get_column_letter(total_cols - 3)].width = 10
    ws.column_dimensions[openpyxl.utils.get_column_letter(total_cols - 2)].width = 10
    ws.column_dimensions[openpyxl.utils.get_column_letter(total_cols - 1)].width = 10
    ws.column_dimensions[openpyxl.utils.get_column_letter(total_cols)].width = 12

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_quarterly_attendance_excel(
    records: List[Dict[str, Any]],
    quarter_name: str,
    year_str: str,
    class_name: str,
    working_days: int = 60
) -> io.BytesIO:
    """
    Exports quarterly student attendance summary to Excel.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Quarterly_{quarter_name}"

    ws.merge_cells("A1:I1")
    t1 = ws["A1"]
    t1.value = f"सहिद स्मृति आवासीय माध्यमिक विद्यालय — त्रैमासिक हाजिरी प्रतिवेदन ({quarter_name})"
    t1.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    t1.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:I2")
    t2 = ws["A2"]
    t2.value = f"त्रैमासिक अवधि: {quarter_name}   |   सत्र: {year_str}   |   कक्षा: {class_name}   |   विद्यालय खुलेका दिन: {working_days} दिन"
    t2.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    t2.font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    headers = [
        "क्र.सं.", "रोल नं.", "विद्यार्थीको नाम", "कक्षा",
        "कुल विद्यालय खुलेका दिन", "उपस्थित दिन", "अनुपस्थित दिन", "बिदा दिन", "हाजिरी प्रतिशत (%)"
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 26

    h_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    h_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    for c_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=c_idx)
        cell.fill = h_fill
        cell.font = h_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for idx, r in enumerate(records, start=1):
        p = r.get("present_days", 0)
        a = r.get("absent_days", 0)
        l = r.get("leave_days", 0)
        tot_days = working_days or (p + a + l) or 1
        pct = round((p / tot_days * 100), 1)

        row_vals = [
            idx,
            r.get("roll_no", ""),
            r.get("name_nepali") or r.get("student_name") or "",
            r.get("class_name_ne") or class_name,
            tot_days,
            p,
            a,
            l,
            f"{pct}%"
        ]
        ws.append(row_vals)
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 20

        for c_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_num, column=c_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if c_idx in (1, 2, 4, 5, 6, 7, 8, 9):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 12, 26, 16, 22, 14, 14, 12, 20]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_annual_attendance_excel(
    records: List[Dict[str, Any]],
    year_str: str,
    class_name: str,
    total_school_days: int = 220
) -> io.BytesIO:
    """
    Exports full academic year attendance summary to Excel.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Annual_{year_str}"

    ws.merge_cells("A1:I1")
    t1 = ws["A1"]
    t1.value = f"सहिद स्मृति आवासीय माध्यमिक विद्यालय — वार्षिक हाजिरी प्रतिवेदन (शैक्षिक वर्ष: {year_str})"
    t1.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    t1.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:I2")
    t2 = ws["A2"]
    t2.value = f"कक्षा: {class_name}   |   वार्षिक सत्र: {year_str}   |   कुल विद्यालय खुलेका दिन: {total_school_days} दिन"
    t2.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    t2.font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    headers = [
        "क्र.सं.", "रोल नं.", "विद्यार्थीको पूरा नाम", "कक्षा",
        "कुल खुलेका दिन", "वार्षिक उपस्थित दिन", "वार्षिक अनुपस्थित दिन", "वार्षिक बिदा दिन", "वार्षिक हाजिरी %"
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 26

    h_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    h_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    for c_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=c_idx)
        cell.fill = h_fill
        cell.font = h_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for idx, r in enumerate(records, start=1):
        p = r.get("present_days", 0)
        a = r.get("absent_days", 0)
        l = r.get("leave_days", 0)
        tot_days = total_school_days or (p + a + l) or 1
        pct = round((p / tot_days * 100), 1)

        row_vals = [
            idx,
            r.get("roll_no", ""),
            r.get("name_nepali") or r.get("student_name") or "",
            r.get("class_name_ne") or class_name,
            tot_days,
            p,
            a,
            l,
            f"{pct}%"
        ]
        ws.append(row_vals)
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 20

        for c_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_num, column=c_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if c_idx in (1, 2, 4, 5, 6, 7, 8, 9):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 12, 26, 16, 20, 18, 18, 16, 18]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output



# ====================================================================
# ALUMNI (पूर्व विद्यार्थी) EXCEL TEMPLATE, PARSING & EXPORT HANDLERS
# ====================================================================

def generate_alumni_template() -> io.BytesIO:
    """
    Generates standard Excel Template for Alumni (पुर्व विद्यार्थी) Import.
    Columns: क्र.सं., विद्यार्थीको नाम, थर, पास आउट कक्षा (कक्षा १० वा कक्षा १२), पास आउट वर्ष (वि.सं.), ठेगाना, सम्पर्क नम्बर, सिम्बोल/रजिस्ट्रेसन नं., हालको पेशा/अध्ययन, कैफियत
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Alumni_Template"
    
    # Title Banner
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = "सहिद स्मृति आवासीय माध्यमिक विद्यालय — पूर्व विद्यार्थी (Alumni) विवरण आयात ढाँचा"
    title_cell.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    title_cell.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Subtitle note
    ws.merge_cells("A2:I2")
    sub_cell = ws["A2"]
    sub_cell.value = "निर्देशन: कक्षा १० र कक्षा १२ का पास आउट विद्यार्थीहरूको विवरण भरी सिट अपलोड गर्नुहोस्। अनिवार्य कोलमहरू: नाम थर, पास आउट कक्षा, पास आउट वर्ष।"
    sub_cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    sub_cell.font = Font(name="Segoe UI", size=10, italic=True, color="92400E")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24

    headers = [
        "क्र.सं.",
        "विद्यार्थीको पूरा नाम, थर *",
        "पास आउट कक्षा (कक्षा १० / कक्षा १२) *",
        "पास आउट वर्ष (वि.सं.) *",
        "ठेगाना",
        "सम्पर्क नम्बर",
        "सिम्बोल / रजिस्ट्रेसन नं.",
        "हालको अवस्था / पेशा / अध्ययन",
        "कैफियत"
    ]
    ws.append(headers)
    ws.row_dimensions[3].height = 26

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.fill = PatternFill(start_color="1D427B", end_color="1D427B", fill_type="solid")
        cell.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    # Sample rows
    samples = [
        (1, "रोहित कार्की", "कक्षा १०", "२०७९", "इटहरी-१९, सुनसरी", "९८४२०१११२२", "SEE-2079-012", "कक्षा ११ विज्ञान अध्ययनरत", "प्रथम श्रेणी"),
        (2, "अस्मिता अधिकारी", "कक्षा १२", "२०८०", "धरान-१२, सुनसरी", "९८५२०३३३४४", "HSEB-80-451", "बि.एस.सी. नर्सिङ अध्ययनरत", "विशिष्ट श्रेणी (GPA 3.75)"),
        (3, "सुरेश पौडेल", "कक्षा १०", "२०७८", "खनार, सुनसरी", "९८१२३४५६७०", "SEE-2078-089", "डिप्लोमा सिभिल इन्जिनियरिङ", "प्रथम श्रेणी"),
    ]
    for row in samples:
        ws.append(list(row))
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 22
        for col_idx in range(1, len(row) + 1):
            cell = ws.cell(row=r_num, column=col_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if col_idx in (1, 3, 4, 6, 7):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 26, 26, 18, 24, 18, 22, 28, 18]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def parse_alumni_excel(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses uploaded Excel sheet for alumni data.
    Returns (valid_alumni_list, error_messages).
    """
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["Excel फाइल खाली छ।"]

    # Locate header row (looking for row with multiple columns having 'नाम' or 'name' and 'कक्षा' or 'class')
    header_row_idx = -1
    for idx, row in enumerate(rows):
        non_empty = [c for c in row if c is not None and str(c).strip() != ""]
        if len(non_empty) < 3:
            continue
        row_str = " ".join([str(c) for c in non_empty]).lower()
        if "नाम" in row_str or "name" in row_str:
            if any(k in row_str for k in ["कक्षा", "class", "वर्ष", "year"]):
                header_row_idx = idx
                break

    if header_row_idx == -1:
        # Fallback to row index 2 (row 3 in 1-based) or row 0
        header_row_idx = 2 if len(rows) > 2 else 0

    headers = [str(c).strip() if c is not None else "" for c in rows[header_row_idx]]
    
    # Map header indices
    col_map = {}
    for idx, h in enumerate(headers):
        hk = normalize_header_key(h)
        if any(k in hk for k in ["नाम", "विद्यार्थीकोनाम", "fullname", "name", "studentname"]):
            col_map["full_name"] = idx
        elif any(k in hk for k in ["कक्षा", "पासआउटकक्षा", "class", "passedclass"]):
            col_map["passed_class"] = idx
        elif any(k in hk for k in ["वर्ष", "पासआउटवर्ष", "year", "passoutyear", "passyear"]):
            col_map["pass_out_year"] = idx
        elif any(k in hk for k in ["ठेगाना", "address", "location"]):
            col_map["address"] = idx
        elif any(k in hk for k in ["सम्पर्क", "फोन", "phone", "contact", "mobile"]):
            col_map["phone"] = idx
        elif any(k in hk for k in ["सिम्बोल", "रजिस्ट्रेसन", "symbol", "regno"]):
            col_map["symbol_no"] = idx
        elif any(k in hk for k in ["हालकोअवस्था", "पेशा", "अध्ययन", "status", "currentstatus", "profession"]):
            col_map["current_status"] = idx
        elif any(k in hk for k in ["कैफियत", "remarks", "note"]):
            col_map["remarks"] = idx

    # If critical columns not found by name, fallback to standard column positions
    if "full_name" not in col_map and len(headers) > 1:
        col_map["full_name"] = 1
    if "passed_class" not in col_map and len(headers) > 2:
        col_map["passed_class"] = 2
    if "pass_out_year" not in col_map and len(headers) > 3:
        col_map["pass_out_year"] = 3

    valid_alumni = []
    errors = []

    for r_idx in range(header_row_idx + 1, len(rows)):
        row = rows[r_idx]
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        def get_val(key):
            if key in col_map and col_map[key] < len(row):
                v = row[col_map[key]]
                return str(v).strip() if v is not None else ""
            return ""

        name = get_val("full_name")
        cls_raw = get_val("passed_class")
        yr_raw = get_val("pass_out_year")

        if not name:
            errors.append(f"पंक्ति {r_idx + 1}: विद्यार्थीको नाम खाली छ।")
            continue

        # Normalize class (१० or १२)
        cls_clean = "कक्षा १०"
        if "12" in cls_raw or "१२" in cls_raw or "hseb" in cls_raw.lower() or "+2" in cls_raw:
            cls_clean = "कक्षा १२"
        elif "10" in cls_raw or "१०" in cls_raw or "see" in cls_raw.lower() or "slc" in cls_raw.lower():
            cls_clean = "कक्षा १०"
        elif cls_raw:
            cls_clean = cls_raw

        # Normalize year (e.g. 2080 or २०८०)
        yr_clean = yr_raw if yr_raw else "२०८१"

        alumni_item = {
            "full_name": name,
            "passed_class": cls_clean,
            "pass_out_year": yr_clean,
            "address": get_val("address"),
            "phone": get_val("phone"),
            "symbol_no": get_val("symbol_no"),
            "current_status": get_val("current_status"),
            "remarks": get_val("remarks")
        }
        valid_alumni.append(alumni_item)

    return valid_alumni, errors

def export_alumni_to_excel(alumni_list: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Exports alumni list to a styled Excel sheet.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Alumni_List"

    # Title Banner
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "सहिद स्मृति आवासीय माध्यमिक विद्यालय — पूर्व विद्यार्थी (Alumni) विवरण"
    title_cell.fill = PatternFill(start_color="15305B", end_color="15305B", fill_type="solid")
    title_cell.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    headers = [
        "क्र.सं.",
        "विद्यार्थीको पूरा नाम, थर",
        "पास आउट कक्षा",
        "पास आउट वर्ष (वि.सं.)",
        "ठेगाना",
        "सम्पर्क नम्बर",
        "सिम्बोल / रजिस्ट्रेसन नं.",
        "हालको पेशा / उच्च अध्ययन"
    ]
    ws.append(headers)
    ws.row_dimensions[2].height = 24

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = PatternFill(start_color="1D427B", end_color="1D427B", fill_type="solid")
        cell.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    for idx, a in enumerate(alumni_list, start=1):
        row_vals = [
            idx,
            a.get("full_name", ""),
            a.get("passed_class", ""),
            a.get("pass_out_year", ""),
            a.get("address", ""),
            a.get("phone", ""),
            a.get("symbol_no", ""),
            a.get("current_status", "")
        ]
        ws.append(row_vals)
        r_num = ws.max_row
        ws.row_dimensions[r_num].height = 20

        for c_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_num, column=c_idx)
            cell.border = border_thin
            cell.font = Font(name="Segoe UI", size=9)
            if c_idx in (1, 3, 4, 6, 7):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    widths = [8, 26, 18, 18, 24, 18, 22, 28]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
