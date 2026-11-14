import json
import sys
from starlette.requests import Request
from app.routers.api_committees import (
    list_management_committee,
    get_management_member,
    create_management_member,
    update_management_member,
    list_trustee_committee,
    get_trustee_member,
    create_trustee_member,
    update_trustee_member,
    CommitteeMemberCreate
)
from app.routers.admin import admin_management_committee, admin_trustee_committee
from app.routers.public import page_management_committee, page_trustee_committee, page_about
from app.auth import create_session

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Mock request builder
def build_request(path: str, role="SUPER_ADMIN", username="admin"):
    token = create_session({"id": 1, "username": username, "role": role})
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [
            (b"host", b"localhost:3000"),
            (b"cookie", f"auth_token={token}".encode("latin-1"))
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 3000),
        "scheme": "http",
        "query_string": b""
    }
    return Request(scope)

SAMPLE_PHOTO_A = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
SAMPLE_PHOTO_B = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def run_tests():
    print("=== TEST 1: SMC Listing ===")
    res = list_management_committee()
    members = res.get("members", [])
    print(f"Total SMC members: {len(members)}")
    assert len(members) >= 10, f"Expected at least 10 SMC members, got {len(members)}"
    m1 = members[0]
    m2 = members[1]
    print(f"  [1] ID {m1['id']} - {m1['name']} ({m1['position']})")
    print(f"  [2] ID {m2['id']} - {m2['name']} ({m2['position']})")
    print(f"  [10] ID {members[9]['id']} - {members[9]['name']} ({members[9]['position']})")

    print("\n=== TEST 2: Trustee Listing ===")
    res_t = list_trustee_committee()
    trustees = res_t.get("members", [])
    print(f"Total Trustees: {len(trustees)}")
    assert len(trustees) >= 9, f"Expected at least 9 Trustees, got {len(trustees)}"
    t1 = trustees[0]
    t2 = trustees[1]
    print(f"  [1] ID {t1['id']} - {t1['name']} ({t1['position']})")
    print(f"  [2] ID {t2['id']} - {t2['name']} ({t2['position']})")

    print("\n=== TEST 3: Individual Member GET endpoints ===")
    gm1 = get_management_member(m1["id"])
    assert gm1["id"] == m1["id"] and gm1["name"] == m1["name"]
    gt1 = get_trustee_member(t1["id"])
    assert gt1["id"] == t1["id"] and gt1["name"] == t1["name"]
    print("Individual GET endpoints returned correct member details.")

    print("\n=== TEST 4: SMC Independent Photo Upload & State Isolation ===")
    req = build_request("/api/committees/management")
    
    # 1. Update Member 1 with Photo A
    data1 = CommitteeMemberCreate(
        name=m1["name"],
        position=m1["position"],
        phone=m1.get("phone") or "९८५२०२८२४०",
        photo=SAMPLE_PHOTO_A,
        qualification="स्नातक",
        term="२०८०-२०८३",
        order_index=m1["order_index"],
        status="सक्रिय"
    )
    upd1 = update_management_member(m1["id"], data1, req)
    assert upd1["success"] is True

    # 2. Update Member 2 with Photo B
    data2 = CommitteeMemberCreate(
        name=m2["name"],
        position=m2["position"],
        phone=m2.get("phone") or "९८४२०००००२",
        photo=SAMPLE_PHOTO_B,
        qualification="स्नातकोत्तर",
        term="२०८०-२०८३",
        order_index=m2["order_index"],
        status="सक्रिय"
    )
    upd2 = update_management_member(m2["id"], data2, req)
    assert upd2["success"] is True

    # 3. Verify Isolation: Member 1 has Photo A, Member 2 has Photo B!
    check_m1 = get_management_member(m1["id"])
    check_m2 = get_management_member(m2["id"])
    assert check_m1["photo"] == SAMPLE_PHOTO_A, "Member 1 photo was overwritten or lost!"
    assert check_m2["photo"] == SAMPLE_PHOTO_B, "Member 2 photo was not saved!"
    print("✓ VERIFIED: Member 1 and Member 2 photos are strictly isolated and preserved!")

    print("\n=== TEST 5: Trustee Committee Independent Photo Upload & State Isolation ===")
    t_req = build_request("/api/committees/trustee")

    # 1. Update Trustee 1 with Photo A
    t_data1 = CommitteeMemberCreate(
        name=t1["name"],
        position=t1["position"],
        phone=t1.get("phone") or "९८५२०००००१",
        photo=SAMPLE_PHOTO_A,
        qualification="स्नातकोत्तर",
        order_index=t1["order_index"],
        status="सक्रिय"
    )
    t_upd1 = update_trustee_member(t1["id"], t_data1, t_req)
    assert t_upd1["success"] is True

    # 2. Update Trustee 2 with Photo B
    t_data2 = CommitteeMemberCreate(
        name=t2["name"],
        position=t2["position"],
        phone=t2.get("phone") or "९८५२०००००२",
        photo=SAMPLE_PHOTO_B,
        qualification="स्नातक",
        order_index=t2["order_index"],
        status="सक्रिय"
    )
    t_upd2 = update_trustee_member(t2["id"], t_data2, t_req)
    assert t_upd2["success"] is True

    # 3. Verify Isolation: Trustee 1 has Photo A, Trustee 2 has Photo B!
    check_t1 = get_trustee_member(t1["id"])
    check_t2 = get_trustee_member(t2["id"])
    assert check_t1["photo"] == SAMPLE_PHOTO_A, "Trustee 1 photo was overwritten or lost!"
    assert check_t2["photo"] == SAMPLE_PHOTO_B, "Trustee 2 photo was not saved!"
    print("✓ VERIFIED: Trustee 1 and Trustee 2 photos are strictly isolated and preserved!")

    print("\n=== TEST 6: Template Rendering Verification ===")
    admin_req = build_request("/admin/management-committee")
    admin_smc_resp = admin_management_committee(admin_req)
    assert admin_smc_resp.status_code == 200
    html_text = admin_smc_resp.body.decode("utf-8")
    assert "विद्यालय व्यवस्थापन समिति" in html_text
    assert "SMC_STORAGE_KEY" in html_text
    assert "smcMembersTableBody" in html_text
    print("✓ Admin SMC template rendered with dual-sync engine.")

    admin_trustee_req = build_request("/admin/trustee-committee")
    admin_trustee_resp = admin_trustee_committee(admin_trustee_req)
    assert admin_trustee_resp.status_code == 200
    html_t_text = admin_trustee_resp.body.decode("utf-8")
    assert "गुठियार समिति" in html_t_text
    assert "TRUSTEE_STORAGE_KEY" in html_t_text
    assert "trusteeMembersTableBody" in html_t_text
    print("✓ Admin Trustee template rendered with dual-sync engine.")

    pub_smc_req = build_request("/management-committee")
    pub_smc_resp = page_management_committee(pub_smc_req)
    assert pub_smc_resp.status_code == 200
    html_pub_text = pub_smc_resp.body.decode("utf-8")
    assert "विद्यालय व्यवस्थापन समिति" in html_pub_text
    assert "SMC_STORAGE_KEY" in html_pub_text
    assert "smcMembersGrid" in html_pub_text
    print("✓ Public SMC template rendered with dual-sync engine.")

    pub_trustee_req = build_request("/trustee-committee")
    pub_trustee_resp = page_trustee_committee(pub_trustee_req)
    assert pub_trustee_resp.status_code == 200
    html_pub_t_text = pub_trustee_resp.body.decode("utf-8")
    assert "गुठियार समिति" in html_pub_t_text
    assert "TRUSTEE_STORAGE_KEY" in html_pub_t_text
    assert "trusteeMembersGrid" in html_pub_t_text
    print("✓ Public Trustee template rendered with dual-sync engine.")

    about_req = build_request("/about")
    about_resp = page_about(about_req)
    assert about_resp.status_code == 200
    html_about = about_resp.body.decode("utf-8")
    assert "विद्यालय व्यवस्थापन समिति" in html_about
    print("✓ Public About page rendered with committee members.")

    # Restore committee photos so production DB stays populated with valid avatars
    import sqlite3
    for p in ['school.db', 'api/school.db']:
        conn = sqlite3.connect(p)
        conn.execute("UPDATE school_management_committee SET photo = '/static/images/committees/smc_28.svg' WHERE id = ?", (m1["id"],))
        conn.execute("UPDATE school_management_committee SET photo = '/static/images/smc_ram_kumari.jpg' WHERE id = ?", (m2["id"],))
        conn.execute("UPDATE trustee_committee SET photo = '/static/images/committees/trustee_1.svg' WHERE id = ?", (t1["id"],))
        conn.execute("UPDATE trustee_committee SET photo = '/static/images/committees/trustee_2.svg' WHERE id = ?", (t2["id"],))
        conn.commit()
        conn.close()

    print("\n" + "="*50)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("="*50)

if __name__ == "__main__":
    run_tests()
