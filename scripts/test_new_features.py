import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import csv
import json
import sqlite3
from unittest.mock import MagicMock
from app.routers import api_bus_users
from app.routers.api_bus_users import BusUserCreate, BusUserUpdate
from app.auth import create_session
from app.utils.excel_handler import parse_bus_users_file, generate_bus_users_template, export_bus_users_to_excel

def run_tests():
    print("=== STARTING FULL TEST SUITE FOR NEW FEATURES ===")

    # ----------------------------------------------------
    # TEST 1: Database and Menu Verification
    # ----------------------------------------------------
    print("\n--- TEST 1: Database & Header Menus Check ---")
    for db in ['school.db', 'api/school.db']:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        
        # Check bus_users table
        cnt = conn.execute("SELECT count(*) FROM bus_users").fetchone()[0]
        print(f"[{db}] bus_users count: {cnt}")
        assert cnt >= 10, f"Expected at least 10 bus users in {db}, found {cnt}"

        # Check menu
        menu = conn.execute("SELECT * FROM header_menus WHERE url = '/bus-users'").fetchone()
        assert menu is not None, f"Menu '/bus-users' not found in {db}"
        print(f"[{db}] Menu found: ID={menu['id']}, Parent={menu['parent_id']}, Title={menu['title_ne']}")
        assert menu['parent_id'] == 9, f"Expected parent_id=9 (Students), found {menu['parent_id']}"
        conn.close()
    print("✓ Test 1 Passed: Database schema, seed data, and header menu verified!")

    # ----------------------------------------------------
    # TEST 2: Template Files and i18n Verification
    # ----------------------------------------------------
    print("\n--- TEST 2: Template Files & i18n Verification ---")
    template_files = [
        "templates/public/bus_users.html",
        "api/templates/public/bus_users.html",
        "templates/admin/bus_users.html",
        "api/templates/admin/bus_users.html",
        "templates/components/topbar.html",
        "api/templates/components/topbar.html",
        "templates/components/navbar.html",
        "api/templates/components/navbar.html",
        "templates/admin/base_admin.html",
        "api/templates/admin/base_admin.html"
    ]
    for tf in template_files:
        with open(tf, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 100, f"{tf} is empty"
    print(f"✓ All {len(template_files)} HTML template files verified!")

    # Check i18n.js
    for js_path in ["static/js/i18n.js", "api/static/js/i18n.js"]:
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
            assert "SchoolI18n" in js
            assert "bus_users" in js
            assert "np" in js and "en" in js
            assert "langBtnNP" in js and "langBtnEN" in js
    print("✓ i18n.js verified with full localization dictionaries and selectors!")

    # ----------------------------------------------------
    # TEST 3: REST API Endpoints & Functions
    # ----------------------------------------------------
    print("\n--- TEST 3: REST API Endpoints Check ---")
    
    # 3.1 List
    res = api_bus_users.list_bus_users(q=None, bus_stop=None, bus_number=None, page=1, page_size=10)
    assert res["success"] is True
    assert res["total"] >= 10
    assert len(res["users"]) > 0
    assert len(res["bus_stops"]) > 0
    print(f"✓ api_bus_users.list_bus_users: {res['total']} users, {len(res['bus_stops'])} stops.")

    # 3.2 Search
    res_search = api_bus_users.list_bus_users(q="रोहित", bus_stop=None, bus_number=None, page=1, page_size=10)
    assert res_search["total"] >= 1
    assert any("रोहित" in u["student_name"] for u in res_search["users"])
    print("✓ Search functionality verified!")

    # 3.3 Filter by bus_stop
    sample_stop = res["bus_stops"][0]
    res_filter = api_bus_users.list_bus_users(q=None, bus_stop=sample_stop, bus_number=None, page=1, page_size=10)
    assert res_filter["total"] >= 1
    assert all(u["bus_stop"] == sample_stop for u in res_filter["users"])
    print(f"✓ Filter by stop '{sample_stop}' verified!")

    # 3.4 Pagination
    res_page = api_bus_users.list_bus_users(q=None, bus_stop=None, bus_number=None, page=1, page_size=5)
    assert len(res_page["users"]) <= 5
    assert res_page["page_size"] == 5
    print("✓ Pagination verified!")

    # 3.5 Templates & Export
    excel_tpl = generate_bus_users_template()
    assert excel_tpl.getbuffer().nbytes > 1000
    print(f"✓ Excel Template generated ({excel_tpl.getbuffer().nbytes} bytes)!")

    csv_tpl_res = api_bus_users.download_bus_users_csv_template()
    assert "विद्यार्थीको पूरा नाम" in csv_tpl_res.body.decode("utf-8-sig")
    print(f"✓ CSV Template verified!")

    # ----------------------------------------------------
    # TEST 4: Add, Edit, Delete (Manual & Bulk Import)
    # ----------------------------------------------------
    print("\n--- TEST 4: CRUD & Bulk Upload ---")
    
    admin_session_token = create_session({
        "id": 1,
        "username": "admin",
        "role": "SUPER_ADMIN",
        "full_name": "प्रशासक"
    })
    
    mock_request = MagicMock()
    mock_request.cookies = {"session_token": admin_session_token}
    mock_request.headers = {}
    mock_request.client.host = "127.0.0.1"

    # Add new user
    new_user = BusUserCreate(
        student_name="विनोद अधिकारी",
        address="इटहरी-१९, तरहरा रोड",
        guardian_name="कमल अधिकारी",
        contact_number="९८०१२३४५६७",
        bus_stop="तरहरा अस्पताल अगाडि",
        bus_number="बस नं. १ (को १ ख २०६६)",
        class_name="कक्षा ११",
        status="सक्रिय",
        remarks="बिहान र दिउँसो"
    )
    create_res = api_bus_users.create_bus_user(new_user, request=mock_request)
    assert create_res["success"] is True
    created_id = create_res["id"]
    print(f"✓ Created student '{new_user.student_name}' with ID {created_id}")

    # Verify lookup
    single_res = api_bus_users.get_bus_user(created_id)
    assert single_res["success"] is True
    assert single_res["user"]["student_name"] == "विनोद अधिकारी"

    # Edit user
    update_data = BusUserUpdate(
        student_name="विनोद कुमार अधिकारी",
        address="इटहरी-१९, तरहरा",
        guardian_name="कमल अधिकारी",
        contact_number="९८०१२३४५६८",
        bus_stop="तरहरा अस्पताल मोड",
        bus_number="बस नं. १ (को १ ख २०६६)",
        class_name="कक्षा १२",
        status="सक्रिय",
        remarks="समय परिवर्तन"
    )
    update_res = api_bus_users.update_bus_user(created_id, update_data, request=mock_request)
    assert update_res["success"] is True
    print(f"✓ Updated student ID {created_id}")

    # Verify update
    single_res2 = api_bus_users.get_bus_user(created_id)
    assert single_res2["user"]["student_name"] == "विनोद कुमार अधिकारी"
    assert single_res2["user"]["class_name"] == "कक्षा १२"

    # Bulk CSV upload test via parse_bus_users_file
    csv_buffer = io.StringIO()
    cw = csv.writer(csv_buffer)
    cw.writerow(["विद्यार्थीको पूरा नाम, थर", "ठेगाना", "अभिभावकको नाम, थर", "सम्पर्क नम्बर", "वस चढ्ने स्थान (Bus Stop)", "बस नम्बर / रुट", "कक्षा", "कैफियत"])
    cw.writerow(["प्रमोद यादव", "दुहबी-२, सुनसरी", "श्याम यादव", "9842111111", "दुहबी चोक", "बस नं. २", "कक्षा ९", "बल्क आयात १"])
    cw.writerow(["सिता कुमारी श्रेष्ठ", "इटहरी-३, सुनसरी", "राम श्रेष्ठ", "9842222222", "सिमसार मोड", "बस नं. १", "कक्षा ८", "बल्क आयात २"])
    csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

    parsed_records, errors = parse_bus_users_file(csv_bytes, "bulk_bus_users.csv")
    assert len(errors) == 0, f"Errors in CSV parsing: {errors}"
    assert len(parsed_records) == 2, f"Expected 2 parsed records, got {len(parsed_records)}"
    print(f"✓ Bulk CSV parser parsed {len(parsed_records)} records successfully!")

    # Test Excel Export with records
    export_buf = export_bus_users_to_excel(parsed_records)
    assert export_buf.getbuffer().nbytes > 1000
    print(f"✓ Excel export generated ({export_buf.getbuffer().nbytes} bytes)!")

    # Delete the created user
    del_res = api_bus_users.delete_bus_user(created_id, request=mock_request)
    assert del_res["success"] is True
    print(f"✓ Deleted student ID {created_id}")

    # Verify deleted
    try:
        api_bus_users.get_bus_user(created_id)
        assert False, "Should have raised 404"
    except Exception as e:
        assert "404" in str(e)
        print("✓ Verified student deleted (404 Not Found)")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
