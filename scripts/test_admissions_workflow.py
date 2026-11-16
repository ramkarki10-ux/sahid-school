import os
import sys
import io
import sqlite3
from unittest.mock import MagicMock

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException, UploadFile
from app.routers.api_admissions import (
    submit_admission_apply,
    list_admissions_admin,
    get_admission_detail_admin,
    update_admission_admin,
    upload_admission_document_admin,
    delete_admission_document_admin,
    approve_admission_admin,
    reject_admission_admin,
    require_admission_manager,
    AdmissionUpdatePayload
)
from app.database import get_db

from app.auth import create_session

def create_mock_request(user=None):
    req = MagicMock()
    req.state.user = user
    if user and isinstance(user, dict):
        token = create_session(user)
        req.cookies = {"session_token": token}
        req.headers = {"Authorization": f"Bearer {token}"}
    else:
        req.cookies = {}
        req.headers = {}
    req.client.host = "127.0.0.1"
    req.url.path = "/api/admissions"
    return req

def make_upload_file(filename, content_bytes, content_type):
    import tempfile
    tf = tempfile.SpooledTemporaryFile()
    tf.write(content_bytes)
    tf.seek(0)
    return UploadFile(filename=filename, file=tf, headers={"content-type": content_type})

def run_tests():
    print("==================================================")
    print("TESTING ONLINE ADMISSION & VERIFICATION WORKFLOW")
    print("==================================================")

    # 1. Database Schema Check
    print("\n--- 1. Testing Database Schema in both databases ---")
    required_cols = [
        "id", "student_name", "dob", "gender", "applying_class", "previous_school",
        "parent_name", "guardian_name", "mobile", "email", "address", "message",
        "status", "remarks", "birth_certificate_url", "citizenship_url",
        "marksheet_url", "character_cert_url", "created_at", "updated_at"
    ]
    for db_path in ['school.db', 'api/school.db']:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(admission_applications)")
        cols = [r[1] for r in cur.fetchall()]
        for c in required_cols:
            assert c in cols, f"Missing {c} in {db_path}"
        conn.close()
    print("✓ Both school.db and api/school.db have updated admission_applications schema!")

    # 2. Test Public Submission WITHOUT any files (strictly optional)
    print("\n--- 2. Testing Public Submission (NO files attached - Optional uploads) ---")
    res_no_files = submit_admission_apply(
        student_name="राम कुमार श्रेष्ठ",
        dob="२०६८/०४/१२",
        gender="छात्र",
        applying_class="कक्षा ८",
        parent_name="हरि बहादुर श्रेष्ठ",
        mobile="९८५२०००१०१",
        address="इटहरी-५, सुनसरी",
        previous_school="सरस्वती माध्यमिक विद्यालय",
        guardian_name="सीता श्रेष्ठ",
        email="ram.shrestha@example.com",
        message="छात्रावास सुविधा आवश्यक छ।"
    )
    assert res_no_files["success"] is True
    adm_id_1 = res_no_files["id"]
    assert res_no_files["documents_uploaded_count"] == 0
    print(f"✓ Application #ADM-{adm_id_1} created without files (documents_uploaded_count: 0)")

    # 3. Test Public Submission WITH optional files (Birth Cert, Citizenship, Marksheet)
    print("\n--- 3. Testing Public Submission WITH optional files ---")
    f_birth = make_upload_file("birth_certificate.pdf", b"%PDF-1.4 Mock Birth Certificate bytes", "application/pdf")
    f_cit = make_upload_file("citizenship.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF Mock Citizenship bytes", "image/jpeg")
    f_ms = make_upload_file("marksheet.pdf", b"%PDF-1.4 Mock Marksheet bytes", "application/pdf")

    res_with_files = submit_admission_apply(
        student_name="अनिता चौधरी",
        dob="२०६५/०९/२२",
        gender="छात्रा",
        applying_class="कक्षा ११ - विज्ञान",
        parent_name="दिलीप चौधरी",
        mobile="९८५२०००२०२",
        address="धरान-१२, सुनसरी",
        previous_school="जनता मावि, धरान",
        guardian_name="",
        email="anita.chaudhary@example.com",
        message="विज्ञान संकायमा छात्रवृत्ति आवेदन",
        file_birth_cert=f_birth,
        file_citizenship=f_cit,
        file_marksheet=f_ms,
        file_character_cert=None
    )
    assert res_with_files["success"] is True
    adm_id_2 = res_with_files["id"]
    assert res_with_files["documents_uploaded_count"] == 3
    print(f"✓ Application #ADM-{adm_id_2} created with 3 attached documents!")

    # 4. Test Privacy & Confidentiality (RBAC: Only Admin & Principal allowed)
    print("\n--- 4. Testing Privacy & Access Control ---")
    
    # 4.1 Anonymous request
    anon_req = create_mock_request(user=None)
    try:
        require_admission_manager(anon_req)
        assert False, "Should have raised 401 for anonymous request"
    except HTTPException as e:
        assert e.status_code == 401
        print("✓ Anonymous request correctly blocked with HTTP 401!")

    # 4.2 Unauthorized role (e.g. Teacher or Non-admin staff)
    teacher_user = {"id": 86, "username": "teacher1", "role": "TEACHER"}
    teacher_req = create_mock_request(user=teacher_user)
    try:
        require_admission_manager(teacher_req)
        assert False, "Should have raised 403 for non-admin role"
    except HTTPException as e:
        assert e.status_code == 403
        print("✓ Non-admin role (TEACHER) correctly blocked with HTTP 403 (Privacy Enforced)!")

    # 4.3 Authorized Admin & Principal
    admin_user = {"id": 1, "username": "admin", "role": "SUPER_ADMIN", "full_name_ne": "प्रमुख प्रशासक"}
    admin_req = create_mock_request(user=admin_user)
    mgr = require_admission_manager(admin_req)
    assert mgr["username"] == "admin"
    print("✓ SUPER_ADMIN authorized successfully!")

    principal_user = {"id": 2, "username": "principal", "role": "PRINCIPAL", "full_name_ne": "विद्यालय प्रिन्सिपल"}
    principal_req = create_mock_request(user=principal_user)
    mgr_p = require_admission_manager(principal_req)
    assert mgr_p["username"] == "principal"
    print("✓ PRINCIPAL authorized successfully!")

    # 5. Admin Detail Inspection
    print("\n--- 5. Admin Detail Retrieval & Document Linking ---")
    detail_res = get_admission_detail_admin(adm_id_2, admin_req)
    assert detail_res["success"] is True
    app_data = detail_res["application"]
    assert len(app_data["documents"]) == 3
    doc_types = [d["document_type"] for d in app_data["documents"]]
    assert any("जन्मदर्ता" in t for t in doc_types)
    assert any("नागरिकता" in t for t in doc_types)
    assert any("मार्कसिट" in t for t in doc_types)
    print(f"✓ Retrieved candidate details with {len(app_data['documents'])} verified documents: {doc_types}")

    # 6. Admin Inline Form Editing (Correcting candidate details)
    print("\n--- 6. Admin Inline Form Edit (Correcting typos/errors) ---")
    edit_payload = AdmissionUpdatePayload(
        student_name="अनिता कुमारी चौधरी (सच्याइएको)",
        applying_class="कक्षा ११ - विज्ञान (छात्रवृत्ति)",
        address="धरान-१५, सुनसरी (ठेगाना सच्याइएको)",
        remarks="प्रवेश परीक्षामा ९४% अंक"
    )
    update_res = update_admission_admin(adm_id_2, edit_payload, admin_req)
    assert update_res["success"] is True

    verify_detail = get_admission_detail_admin(adm_id_2, admin_req)
    updated = verify_detail["application"]
    assert updated["student_name"] == "अनिता कुमारी चौधरी (सच्याइएको)"
    assert updated["applying_class"] == "कक्षा ११ - विज्ञान (छात्रवृत्ति)"
    assert updated["address"] == "धरान-१५, सुनसरी (ठेगाना सच्याइएको)"
    assert updated["remarks"] == "प्रवेश परीक्षामा ९४% अंक"
    print("✓ Candidate data successfully updated inline in admin panel!")

    # 7. Admin Uploading Replacement/New Document Directly from Review Panel
    print("\n--- 7. Admin Uploading New Document from Review Panel ---")
    mock_tc_file = make_upload_file("tc_certificate.pdf", b"%PDF-1.4 Mock Transfer Certificate", "application/pdf")
    upload_res = upload_admission_document_admin(
        id=adm_id_2,
        request=admin_req,
        document_type="स्थानान्तरण प्रमाणपत्र (Transfer Certificate / TC)",
        document_name="अनिता चौधरी - TC",
        document_file=mock_tc_file,
        notes="प्रशासन शाखामा प्राप्त सक्कल TC प्रतिलिपि"
    )
    assert upload_res["success"] is True
    new_doc_id = upload_res["document"]["id"]
    print(f"✓ New document #{new_doc_id} successfully attached by Admin!")

    # Verify count is now 4
    verify_after_upload = get_admission_detail_admin(adm_id_2, admin_req)
    assert len(verify_after_upload["application"]["documents"]) == 4
    print("✓ Total attached documents count verified: 4")

    # 8. Admin Deleting Unwanted/Incorrect Document
    print("\n--- 8. Admin Deleting Unwanted/Incorrect Document ---")
    del_res = delete_admission_document_admin(adm_id_2, new_doc_id, admin_req)
    assert del_res["success"] is True

    verify_after_del = get_admission_detail_admin(adm_id_2, admin_req)
    assert len(verify_after_del["application"]["documents"]) == 3
    print("✓ Unwanted document successfully deleted and removed from candidate profile!")

    # 9. Admin Approval Workflow
    print("\n--- 9. Admin Approval Workflow ---")
    approve_res = approve_admission_admin(
        adm_id_2,
        admin_req,
        remarks="कागजात रुजु भयो, भर्ना स्वीकृत गरिएको छ।"
    )
    assert approve_res["success"] is True

    verify_approved = get_admission_detail_admin(adm_id_2, admin_req)
    approved_app = verify_approved["application"]
    assert approved_app["status"] == "स्वीकृत"
    for d in approved_app["documents"]:
        assert d["verification_status"] == "प्रमाणित", f"Document {d['id']} status is {d['verification_status']}"
    print("✓ Application status set to 'स्वीकृत' and all attached documents set to 'प्रमाणित'!")

    # 10. Admin Rejection Workflow
    print("\n--- 10. Admin Rejection Workflow on Application 1 ---")
    reject_res = reject_admission_admin(
        adm_id_1,
        admin_req,
        reason="सम्पर्क हुन नसकेको र मापदण्ड अपुग"
    )
    assert reject_res["success"] is True
    verify_rejected = get_admission_detail_admin(adm_id_1, admin_req)
    assert verify_rejected["application"]["status"] == "अस्वीकृत"
    print("✓ Application #ADM-1 rejected successfully!")

    # 11. Sync and verify api/school.db
    print("\n--- 11. Synchronizing databases ---")
    import shutil
    shutil.copyfile("school.db", "api/school.db")
    print("✓ Synchronized school.db to api/school.db!")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
