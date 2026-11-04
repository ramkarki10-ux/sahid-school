import sys
import json
import sqlite3
from datetime import date
from starlette.requests import Request
from app.database import get_db
from app.auth import create_session
from app.routers.api_homework import (
    get_subjects_by_class,
    list_homework,
    create_homework,
    update_homework,
    delete_homework,
    HomeworkCreateRequest,
    HomeworkUpdateRequest
)

sys.stdout.reconfigure(encoding='utf-8')

class MockAuthRequest:
    def __init__(self, user_dict):
        token = create_session(user_dict)
        self.cookies = {"session_token": token}
        self.headers = {}
        self.client = type('Client', (), {'host': '127.0.0.1'})()

def test_homework_functions():
    print("1. Testing get_subjects_by_class for Class 1 (कक्षा १) ...")
    res1 = get_subjects_by_class(class_id=1)
    assert res1["success"] is True
    subjs1 = [s["subject_name_ne"] for s in res1["subjects"]]
    print(f"   Class 1 subjects ({len(subjs1)}): {subjs1}")
    assert "नेपाली" in subjs1
    assert "गणित" in subjs1
    assert "विज्ञान तथा प्रविधि" in subjs1
    assert "कम्प्युटर शिक्षा" in subjs1

    print("\n2. Testing get_subjects_by_class for Class 11 (कक्षा ११) ...")
    res11 = get_subjects_by_class(class_id=11)
    assert res11["success"] is True
    subjs11 = [s["subject_name_ne"] for s in res11["subjects"]]
    print(f"   Class 11 subjects ({len(subjs11)}): {subjs11}")
    assert "होटल व्यवस्थापन" in subjs11
    assert "खाद्य तथा पेय सेवा" in subjs11

    print("\n3. Testing list_homework ...")
    mock_req = type('Req', (), {'cookies': {}, 'headers': {}})()
    list_res = list_homework(mock_req)
    assert list_res["success"] is True
    print(f"   Total active homework items: {list_res['count']}")
    assert list_res["count"] > 0
    for hw in list_res["homework"]:
        q_count = len(hw.get("question_list", []))
        print(f"   HW ID {hw['id']}: [{hw.get('class_name_ne')}] {hw.get('subject_name')} -> {hw.get('title')} ({q_count} questions)")
        if hw["id"] in [1, 2, 3]:
            assert q_count == 7, f"Expected 7 questions for HW {hw['id']}, got {q_count}"

    print("\n4. Testing create_homework with 7 default questions ...")
    admin_user = {"id": 1, "username": "admin", "role": "SUPER_ADMIN", "teacher_id": 103}
    mock_auth_req = MockAuthRequest(admin_user)

    create_data = HomeworkCreateRequest(
        class_id=10,
        subject_name="विज्ञान तथा प्रविधि",
        title="पाठ ८: अम्ल, क्षार र लवण (Acids, Bases and Salts)",
        description="अम्ल र क्षारको रासायनिक गुण र pH स्केल सम्बन्धी प्रश्नोत्तर",
        assigned_date=date.today().isoformat(),
        due_date="2026-11-12",
        questions=[
            "अम्ल (Acid) भनेको के हो? यसका कुनै दुई विशेषताहरू लेख्नुहोस्।",
            "दैनिक जीवनमा प्रयोग हुने तीनवटा प्राकृतिक अम्लहरूको नाम र स्रोत उल्लेख गर्नुहोस्।",
            "क्षार (Base) र क्षारिय (Alkali) बीचको भिन्नता के हो?",
            "लिटमस पेपरको प्रयोग गरी अम्ल र क्षार कसरी पहिचान गर्न सकिन्छ?",
            "तटस्थीकरण प्रतिक्रिया (Neutralization reaction) लाई समीकरणसहित व्याख्या गर्नुहोस्।",
            "pH स्केल भनेको के हो? तटस्थ पानीको pH मान कति हुन्छ?",
            "किसानले खेतको माटोमा चुन (Lime) किन हाल्छन्? वैज्ञानिक कारण दिनुहोस्।"
        ]
    )
    create_res = create_homework(create_data, mock_auth_req)
    assert create_res["success"] is True
    new_hw_id = create_res["homework_id"]
    print(f"   Homework created successfully with ID: {new_hw_id}")

    # Check that questions were saved into DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT questions, title FROM homework WHERE id = ?", (new_hw_id,))
    row = c.fetchone()
    conn.close()
    assert row is not None
    saved_questions = json.loads(row["questions"])
    assert len(saved_questions) == 7
    print(f"   Verified {len(saved_questions)} questions saved in database!")

    print("\n5. Testing update_homework: adding 8th question & editing title ...")
    update_data = HomeworkUpdateRequest(
        title="पाठ ८: अम्ल, क्षार र लवण (संशोधित कार्य)",
        questions=saved_questions + ["प्रश्न ८ (थप प्रश्न): दैनिक जीवनमा लवणका दुई प्रमुख उपयोगिताहरू के-के हुन्?"]
    )
    update_res = update_homework(new_hw_id, update_data, mock_auth_req)
    assert update_res["success"] is True

    # Check updated questions count
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT questions, title FROM homework WHERE id = ?", (new_hw_id,))
    row = c.fetchone()
    conn.close()
    updated_questions = json.loads(row["questions"])
    assert len(updated_questions) == 8
    print(f"   Successfully verified update: Title='{row['title']}', Questions Count={len(updated_questions)}")

    print("\n6. Testing delete_homework ...")
    del_res = delete_homework(new_hw_id, mock_auth_req)
    assert del_res["success"] is True
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM homework WHERE id = ?", (new_hw_id,))
    assert c.fetchone() is None
    conn.close()
    print("   Successfully verified homework deletion!")

    print("\n=======================================================")
    print("ALL TESTS PASSED! HOMEWORK & QUESTIONNAIRE SYSTEM 100% OPERATIONAL")
    print("=======================================================")

if __name__ == "__main__":
    test_homework_functions()
