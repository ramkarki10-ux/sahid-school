import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.routers import api_documents
from app.routers.api_documents import (
    determine_requirement_group,
    get_document_requirements,
    get_student_checklist,
    require_verifier_role,
    VerifyDocumentRequest
)
from app.auth import create_session

def run_tests():
    print("=== STARTING FULL STUDENT DOCUMENT VERIFICATION TEST SUITE ===")

    # ----------------------------------------------------
    # TEST 1: Database Schema & Records Check
    # ----------------------------------------------------
    print("\n--- TEST 1: Database Schema & Seed Verification ---")
    required_cols = [
        "id", "student_id", "admission_id", "student_class", "class_numeric",
        "student_age", "requirement_group", "document_type", "document_name",
        "file_path", "file_size", "mime_type", "file_data", "verification_status",
        "verification_note", "verified_by", "verified_by_name", "verified_at"
    ]
    for db in ['school.db', 'api/school.db']:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(student_documents)")
        cols = [r["name"] for r in cur.fetchall()]
        print(f"[{db}] Column count: {len(cols)}")
        for req in required_cols:
            assert req in cols, f"Missing required column '{req}' in {db}"

        cur.execute("SELECT count(*) FROM student_documents")
        cnt = cur.fetchone()[0]
        print(f"[{db}] student_documents total records: {cnt}")
        assert cnt >= 16, f"Expected at least 16 records in {db}, found {cnt}"
        conn.close()
    print("✓ Test 1 Passed: student_documents schema & seed records verified in both databases!")

    # ----------------------------------------------------
    # TEST 2: Conditional Requirements Logic
    # ----------------------------------------------------
    print("\n--- TEST 2: Conditional Document Requirements Logic ---")
    assert determine_requirement_group(class_numeric=8) == "nursery_to_10"
    assert determine_requirement_group(class_numeric=10) == "nursery_to_10"
    assert determine_requirement_group(class_numeric=11) == "class_11_12"
    assert determine_requirement_group(class_numeric=12) == "class_11_12"
    assert determine_requirement_group(class_name="कक्षा ११ - साइन्स") == "class_11_12"
    assert determine_requirement_group(age=14) == "nursery_to_10"
    assert determine_requirement_group(age=17) == "class_11_12"
    print("✓ Class/Age group determination tested successfully!")

    # Test requirements payload
    req_nursery = get_document_requirements(class_numeric=8)
    assert req_nursery["requirement_group"] == "nursery_to_10"
    mandatory_types_nursery = [d["type"] for d in req_nursery["rule"]["required_documents"]]
    assert any("जन्मदर्ता" in t for t in mandatory_types_nursery)
    assert any("नागरिकता" in t for t in mandatory_types_nursery)
    print("✓ Nursery to Class 10 rules verified: Birth Certificate & Guardian Citizenship required.")

    req_plus2 = get_document_requirements(class_numeric=12)
    assert req_plus2["requirement_group"] == "class_11_12"
    mandatory_types_plus2 = [d["type"] for d in req_plus2["rule"]["required_documents"]]
    assert any("नागरिकता वा जन्मदर्ता" in t for t in mandatory_types_plus2)
    assert any("मार्कसिट" in t for t in mandatory_types_plus2)
    assert any("चारित्रिक" in t for t in mandatory_types_plus2)
    assert any("स्थानान्तरण" in t or "TC" in t for t in mandatory_types_plus2)
    print("✓ Class 11 and 12 rules verified: Citizenship/Birth, Marksheet, Character Cert, and TC required.")

    # ----------------------------------------------------
    # TEST 3: Student Compliance Checklist
    # ----------------------------------------------------
    print("\n--- TEST 3: Student Compliance Checklist ---")
    chk_rohit = get_student_checklist(student_id=1)
    assert chk_rohit["success"] is True
    assert chk_rohit["requirement_group"] == "nursery_to_10"
    assert chk_rohit["overall_status"] == "COMPLETED"
    print(f"✓ Rohit Karki (Class 8) checklist status: {chk_rohit['overall_status']} ({chk_rohit['overall_label']})")

    chk_bhawana = get_student_checklist(student_id=8)
    assert chk_bhawana["success"] is True
    assert chk_bhawana["requirement_group"] == "class_11_12"
    assert chk_bhawana["overall_status"] == "COMPLETED"
    assert len(chk_bhawana["checklist"]) == 4
    print(f"✓ Bhawana Rai (Class 12) checklist status: {chk_bhawana['overall_status']} ({chk_bhawana['overall_label']})")

    # ----------------------------------------------------
    # TEST 4: Role-Based Access Control (RBAC) Verification
    # ----------------------------------------------------
    print("\n--- TEST 4: Role-Based Access Control (RBAC) ---")
    
    # 4.1 Anonymous
    anon_req = MagicMock()
    anon_req.cookies = {}
    anon_req.headers = {}
    try:
        require_verifier_role(anon_req)
        assert False, "Anonymous request should be blocked"
    except HTTPException as e:
        assert e.status_code == 401
        print("✓ Anonymous verification blocked with 401 Unauthorized")

    # 4.2 Lower-level roles: STUDENT, TEACHER, PARENT
    for role in ["STUDENT", "TEACHER", "PARENT", "STAFF"]:
        token = create_session({"id": 99, "username": f"user_{role}", "role": role})
        mock_req = MagicMock()
        mock_req.cookies = {"session_token": token}
        mock_req.headers = {}
        try:
            require_verifier_role(mock_req)
            assert False, f"Role {role} should be blocked"
        except HTTPException as e:
            assert e.status_code == 403
            assert "पहुँच अस्वीकृत" in e.detail
            print(f"✓ Role '{role}' blocked with 403 Forbidden")

    # 4.3 Authorized Verifiers: SUPER_ADMIN, ADMIN, PRINCIPAL
    for role in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]:
        token = create_session({"id": 1, "username": f"user_{role}", "role": role, "full_name_ne": f"प्रशासक ({role})"})
        mock_req = MagicMock()
        mock_req.cookies = {"session_token": token}
        mock_req.headers = {}
        mock_req.client.host = "127.0.0.1"
        u = require_verifier_role(mock_req)
        assert u["role"] == role
        print(f"✓ Role '{role}' authorized successfully for verification!")

    # ----------------------------------------------------
    # TEST 5: Verification State Changes (Approve, Revision, Reject)
    # ----------------------------------------------------
    print("\n--- TEST 5: Verification Workflow State Changes ---")
    admin_token = create_session({"id": 1, "username": "admin", "role": "SUPER_ADMIN", "full_name_ne": "प्रमुख प्रशासक"})
    admin_req = MagicMock()
    admin_req.cookies = {"session_token": admin_token}
    admin_req.headers = {}
    admin_req.client.host = "127.0.0.1"

    # 5.1 Approve Document 3 (Anita Chaudhary Birth Cert)
    res_app = api_documents.verify_document(
        doc_id=3,
        req=VerifyDocumentRequest(verification_status="प्रमाणित", verification_note="सदर गरियो।"),
        request=admin_req
    )
    assert res_app["success"] is True
    assert res_app["verification_status"] == "प्रमाणित"
    print("✓ Document 3 approved successfully!")

    # 5.2 Mark Document 3 as Needs Revision
    res_rev = api_documents.verify_document(
        doc_id=3,
        req=VerifyDocumentRequest(verification_status="सुधार आवश्यक", verification_note="जन्मदर्ताको छाप स्पष्ट छैन।"),
        request=admin_req
    )
    assert res_rev["success"] is True
    assert res_rev["verification_status"] == "सुधार आवश्यक"
    print("✓ Document 3 marked as Needs Revision successfully!")

    # 5.3 Reject Document 3
    res_rej = api_documents.verify_document(
        doc_id=3,
        req=VerifyDocumentRequest(verification_status="अस्वीकृत", verification_note="नक्कली कागजात।"),
        request=admin_req
    )
    assert res_rej["success"] is True
    assert res_rej["verification_status"] == "अस्वीकृत"
    print("✓ Document 3 rejected successfully!")

    # ----------------------------------------------------
    # TEST 6: List & Filter Endpoints
    # ----------------------------------------------------
    print("\n--- TEST 6: List & Status Tabs Check ---")
    list_res = api_documents.list_documents(request=admin_req)
    assert list_res["success"] is True
    assert list_res["total"] >= 16
    assert "status_counts" in list_res
    print(f"✓ Status counts: {list_res['status_counts']}")
    print(f"✓ Group counts: {list_res['group_counts']}")

    # Filter by Pending
    pending_res = api_documents.list_documents(request=admin_req, verification_status="जाँच हुन बाँकी")
    assert all(d["verification_status"] == "जाँच हुन बाँकी" for d in pending_res["documents"])
    print(f"✓ Pending filter: {len(pending_res['documents'])} items")

    # Filter by Group
    grp_res = api_documents.list_documents(request=admin_req, requirement_group="class_11_12")
    assert all(d["requirement_group"] == "class_11_12" for d in grp_res["documents"])
    print(f"✓ Class 11-12 group filter: {len(grp_res['documents'])} items")

    # Export check
    exp_res = api_documents.export_documents_route(request=admin_req)
    assert exp_res.status_code == 200
    print("✓ Excel export generated successfully!")

    # ----------------------------------------------------
    # TEST 7: Template Synchronization Check
    # ----------------------------------------------------
    print("\n--- TEST 7: Template Synchronization Check ---")
    for tf in ["templates/admin/document_verification.html", "api/templates/admin/document_verification.html"]:
        with open(tf, "r", encoding="utf-8") as f:
            c = f.read()
            assert "विद्यार्थीको जन्मदर्ता (Birth Certificate)" in c
            assert "अभिभावकको नागरिकता" in c
            assert "कक्षा ११ र १२" in c
            assert "प्रमाणित" in c
            assert "सुधार आवश्यक" in c
            assert "अस्वीकृत" in c
            assert "can_verify" in c
    print("✓ Both template files verified and synced with conditional rules & RBAC!")

    print("\n==================================================")
    print("ALL STUDENT DOCUMENT VERIFICATION TESTS PASSED (100%)!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
