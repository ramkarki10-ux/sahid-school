with open('app/utils/excel_handler.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_sec = '''    headers = ["क्र.सं.", "कक्षा", "विषय", "गृहकार्य शीर्षक", "शिक्षक", "तोकिएको मिति", "बुझाउने मिति", "स्थिति", "विस्तृत विवरण"]
    rows = []
    for idx, h in enumerate(hw_list, start=1):
        rows.append([
            idx, h.get("class_name_ne", ""), h.get("subject_name", ""), h.get("title", ""),
            h.get("teacher_name", ""), h.get("assigned_date", ""), h.get("due_date", ""),
            h.get("status", "सक्रिय"), h.get("description", "")
        ])'''

new_sec = '''    headers = ["क्र.सं.", "कक्षा", "विषय", "गृहकार्य शीर्षक", "शिक्षक", "तोकिएको मिति", "बुझाउने मिति", "स्थिति", "प्रश्नावली", "विस्तृत विवरण"]
    rows = []
    for idx, h in enumerate(hw_list, start=1):
        q_raw = h.get("questions")
        q_text = ""
        if q_raw:
            try:
                import json
                ql = json.loads(q_raw) if isinstance(q_raw, str) else q_raw
                q_text = "\\n".join([f"{i+1}. {q}" for i, q in enumerate(ql)])
            except Exception:
                q_text = str(q_raw)
        rows.append([
            idx, h.get("class_name_ne", ""), h.get("subject_name", ""), h.get("title", ""),
            h.get("teacher_name", ""), h.get("assigned_date", ""), h.get("due_date", ""),
            h.get("status", "सक्रिय"), q_text, h.get("description", "")
        ])'''

if old_sec in text:
    text = text.replace(old_sec, new_sec, 1)
    with open('app/utils/excel_handler.py', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(text)
    print('Updated export_homework_to_excel successfully!')
else:
    print('Already updated or pattern not found.')

