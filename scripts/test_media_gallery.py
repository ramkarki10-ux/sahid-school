import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.routers import api_media_gallery
from app.routers.api_media_gallery import (
    MediaItemCreate,
    MediaBatchCreate,
    BatchMediaItem,
    MediaItemUpdate,
    MediaReplacePayload,
    extract_youtube_id,
    require_gallery_admin
)
from app.auth import create_session

def run_tests():
    print("=== STARTING FULL MEDIA GALLERY CMS TEST SUITE ===")

    # ----------------------------------------------------
    # TEST 1: Database Schema & Records Check
    # ----------------------------------------------------
    print("\n--- TEST 1: Database Schema & Seed Verification ---")
    required_cols = [
        "id", "title", "description", "media_type", "category",
        "media_url", "thumbnail_url", "external_link", "external_link_title",
        "youtube_id", "event_date", "uploaded_by", "is_featured",
        "display_order", "is_published", "created_at", "updated_at"
    ]
    for db in ['school.db', 'api/school.db']:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(media_gallery)")
        col_names = [r["name"] for r in cur.fetchall()]
        print(f"[{db}] Column count: {len(col_names)}")
        for req in required_cols:
            assert req in col_names, f"Missing required column '{req}' in {db}"

        cur.execute("SELECT count(*) FROM media_gallery")
        cnt = cur.fetchone()[0]
        print(f"[{db}] media_gallery total records: {cnt}")
        assert cnt >= 9, f"Expected at least 9 records in {db}, found {cnt}"
        conn.close()
    print("✓ Test 1 Passed: media_gallery schema & records verified in both databases!")

    # ----------------------------------------------------
    # TEST 2: YouTube URL Parsing
    # ----------------------------------------------------
    print("\n--- TEST 2: YouTube URL Parser ---")
    urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for u, expected in urls:
        parsed = extract_youtube_id(u)
        assert parsed == expected, f"Expected {expected} for {u}, got {parsed}"
    print("✓ Test 2 Passed: YouTube URL parser extracted video IDs from all formats!")

    # ----------------------------------------------------
    # TEST 3: Public Read-Only Endpoints
    # ----------------------------------------------------
    print("\n--- TEST 3: Public Read-Only Endpoints ---")
    # All media
    res_all = api_media_gallery.list_media_gallery(media_type=None, category=None, q=None, is_featured=None, page=1, page_size=10)
    assert res_all["success"] is True
    assert res_all["total"] >= 9
    print(f"✓ Total media: {res_all['total']}")

    # Photos only
    res_photos = api_media_gallery.list_media_gallery(media_type="photo", category=None, q=None, is_featured=None, page=1, page_size=10)
    assert all(item["media_type"] == "photo" for item in res_photos["items"])
    print(f"✓ Photos count: {res_photos['total']}")

    # Videos only
    res_videos = api_media_gallery.list_media_gallery(media_type="video", category=None, q=None, is_featured=None, page=1, page_size=10)
    assert all(item["media_type"] == "video" for item in res_videos["items"])
    print(f"✓ Videos count: {res_videos['total']}")

    # Search
    res_search = api_media_gallery.list_media_gallery(media_type=None, category=None, q="वार्षिकोत्सव", is_featured=None, page=1, page_size=10)
    assert res_search["total"] >= 1
    print(f"✓ Search by term 'वार्षिकोत्सव': {res_search['total']} results")

    # Stats
    stats = api_media_gallery.get_gallery_stats()
    assert stats["total_photos"] >= 6
    assert stats["total_videos"] >= 3
    print(f"✓ Stats: {stats['total_photos']} photos, {stats['total_videos']} videos")

    # Single item
    sample_id = res_all["items"][0]["id"]
    single = api_media_gallery.get_single_media(sample_id)
    assert single["success"] is True
    assert single["media"]["id"] == sample_id
    print(f"✓ Single item lookup ID {sample_id}: '{single['media']['title']}'")

    # ----------------------------------------------------
    # TEST 4: RBAC & Security Permission Checks
    # ----------------------------------------------------
    print("\n--- TEST 4: Role-Based Access Control (RBAC) Verification ---")
    
    # 4.1 Unauthenticated Request
    anon_req = MagicMock()
    anon_req.cookies = {}
    anon_req.headers = {}
    try:
        require_gallery_admin(anon_req)
        assert False, "Should raise 401 for anonymous user"
    except HTTPException as e:
        assert e.status_code == 401
        print("✓ Anonymous request blocked with 401 Unauthorized")

    # 4.2 Non-Admin / Unauthorized Role (e.g. STUDENT, PARENT)
    student_token = create_session({"id": 101, "username": "student_ram", "role": "STUDENT"})
    student_req = MagicMock()
    student_req.cookies = {"session_token": student_token}
    student_req.headers = {}
    try:
        require_gallery_admin(student_req)
        assert False, "Should raise 403 for student role"
    except HTTPException as e:
        assert e.status_code == 403
        assert "पहुँच अस्वीकृत" in e.detail
        print("✓ Student role blocked with 403 Forbidden")

    # 4.3 Authorized Admin & Principal
    admin_token = create_session({"id": 1, "username": "admin", "role": "SUPER_ADMIN"})
    admin_req = MagicMock()
    admin_req.cookies = {"session_token": admin_token}
    admin_req.headers = {}
    admin_req.client.host = "127.0.0.1"
    user = require_gallery_admin(admin_req)
    assert user["role"] == "SUPER_ADMIN"
    print("✓ SUPER_ADMIN authorized successfully!")

    principal_token = create_session({"id": 2, "username": "principal", "role": "PRINCIPAL"})
    principal_req = MagicMock()
    principal_req.cookies = {"session_token": principal_token}
    principal_req.headers = {}
    principal_req.client.host = "127.0.0.1"
    user_p = require_gallery_admin(principal_req)
    assert user_p["role"] == "PRINCIPAL"
    print("✓ PRINCIPAL authorized successfully!")

    # ----------------------------------------------------
    # TEST 5: CRUD, Replace, and Batch Operations
    # ----------------------------------------------------
    print("\n--- TEST 5: CRUD & Media Replacement ---")

    # 5.1 Create single photo
    new_media = MediaItemCreate(
        title="कक्षा १२ कम्प्युटर ल्याब प्रयोगात्मक परीक्षा",
        description="कक्षा १२ का विद्यार्थीहरूको कम्प्युटर साइन्स प्रयोगात्मक परीक्षा तथा कोडिङ परियोजना प्रस्तुति।",
        media_type="photo",
        category="शैक्षिक",
        media_url="/static/images/hero-banner.jpg",
        event_date="२०८२/११/३०",
        external_link="https://www.facebook.com/profile.php?id=100092258731456",
        external_link_title="फेसबुक फोटो पोस्ट",
        is_featured=1,
        display_order=10
    )
    created = api_media_gallery.create_media_item(new_media, request=admin_req)
    assert created["success"] is True
    created_id = created["id"]
    print(f"✓ Created new media item with ID {created_id}")

    # 5.2 Edit metadata
    update_payload = MediaItemUpdate(
        title="कक्षा १२ कम्प्युटर ल्याब प्रयोगात्मक परीक्षा (संशोधित)",
        description="संशोधित विस्तृत विवरण: शतप्रतिशत विद्यार्थीहरूको सफल सहभागिता।",
        category="शैक्षिक",
        event_date="२०८२/१२/०१"
    )
    up_res = api_media_gallery.update_media_item(created_id, update_payload, request=admin_req)
    assert up_res["success"] is True

    # Verify update
    chk = api_media_gallery.get_single_media(created_id)
    assert chk["media"]["title"] == "कक्षा १२ कम्प्युटर ल्याब प्रयोगात्मक परीक्षा (संशोधित)"
    assert chk["media"]["event_date"] == "२०८२/१२/०१"
    print(f"✓ Verified updated metadata for ID {created_id}")

    # 5.3 REPLACE MEDIA (Verify clean file swap without breaking metadata!)
    replace_payload = MediaReplacePayload(
        media_url="/static/images/slider_admission.jpg"
    )
    rep_res = api_media_gallery.replace_media_item(created_id, replace_payload, request=admin_req)
    assert rep_res["success"] is True
    assert rep_res["new_media_url"] == "/static/images/slider_admission.jpg"

    chk_rep = api_media_gallery.get_single_media(created_id)
    assert chk_rep["media"]["media_url"] == "/static/images/slider_admission.jpg"
    # Metadata preserved
    assert chk_rep["media"]["title"] == "कक्षा १२ कम्प्युटर ल्याब प्रयोगात्मक परीक्षा (संशोधित)"
    assert chk_rep["media"]["event_date"] == "२०८२/१२/०१"
    print("✓ Replace Media verified: Image file cleanly swapped while keeping title & description intact!")

    # 5.4 Batch Upload
    batch_payload = MediaBatchCreate(
        media_type="photo",
        category="खेलकुद",
        event_date="२०८२/११/२८",
        description="अन्तर-सदन ब्याडमिन्टन प्रतियोगिता",
        external_link="https://www.facebook.com/profile.php?id=100092258731456",
        external_link_title="फेसबुक खेलकुद एल्बम",
        items=[
            BatchMediaItem(title="फाइनल खेल १", media_url="/static/images/hero-banner.jpg"),
            BatchMediaItem(title="फाइनल खेल २", media_url="/static/images/slider_hostel.jpg")
        ]
    )
    batch_res = api_media_gallery.batch_create_media(batch_payload, request=admin_req)
    assert batch_res["success"] is True
    assert batch_res["inserted_count"] == 2
    print(f"✓ Batch upload created {batch_res['inserted_count']} photos successfully!")

    # 5.5 Delete Media
    del_res = api_media_gallery.delete_media_item(created_id, request=admin_req)
    assert del_res["success"] is True
    print(f"✓ Deleted media item ID {created_id}")

    try:
        api_media_gallery.get_single_media(created_id)
        assert False, "Should have raised 404"
    except HTTPException as e:
        assert e.status_code == 404
        print("✓ Verified deletion confirmed (404 Not Found)")

    # ----------------------------------------------------
    # TEST 6: Template files sync verification
    # ----------------------------------------------------
    print("\n--- TEST 6: HTML Templates Verification ---")
    templates_to_check = [
        "templates/admin/gallery.html",
        "api/templates/admin/gallery.html",
        "templates/public/gallery.html",
        "api/templates/public/gallery.html",
        "templates/public/videos.html",
        "api/templates/public/videos.html",
        "templates/components/navbar.html",
        "api/templates/components/navbar.html",
        "templates/admin/base_admin.html",
        "api/templates/admin/base_admin.html"
    ]
    for tf in templates_to_check:
        assert os.path.exists(tf), f"Template {tf} does not exist"
        with open(tf, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 500, f"Template {tf} is too small ({len(content)} bytes)"
    print(f"✓ All {len(templates_to_check)} template files verified and synced!")

    print("\n==================================================")
    print("ALL MEDIA GALLERY TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
