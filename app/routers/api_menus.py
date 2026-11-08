from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/menus", tags=["menus"])

class MenuCreate(BaseModel):
    parent_id: Optional[int] = None
    title_ne: str
    title_en: Optional[str] = None
    url: str
    icon: Optional[str] = "link"
    order_index: Optional[int] = 10
    is_active: Optional[int] = 1

class HeaderSettingsUpdate(BaseModel):
    name_ne: str
    name_en: Optional[str] = None
    tagline_ne: Optional[str] = None
    tagline_en: Optional[str] = None
    established_ne: Optional[str] = None
    address_ne: Optional[str] = None
    logo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

DEFAULT_MENUS_SEED = [
    # Top-level menus
    {"id": 1, "parent_id": None, "title_ne": "गृहपृष्ठ", "title_en": "Home", "url": "/", "icon": "home", "order_index": 1},
    {"id": 2, "parent_id": None, "title_ne": "न्युज फिड", "title_en": "News Feed", "url": "/feed", "icon": "newspaper", "order_index": 2},
    {"id": 3, "parent_id": None, "title_ne": "हाम्रो विद्यालय", "title_en": "About Us", "url": "/about", "icon": "info", "order_index": 3},
    {"id": 4, "parent_id": None, "title_ne": "उपलब्धि", "title_en": "Achievements", "url": "/achievements", "icon": "award", "order_index": 4},
    {"id": 5, "parent_id": None, "title_ne": "सूचना", "title_en": "Notices", "url": "/notices", "icon": "bell", "order_index": 5},
    {"id": 6, "parent_id": None, "title_ne": "प्रकाशन", "title_en": "Publications", "url": "/publications", "icon": "file-text", "order_index": 6},
    {"id": 7, "parent_id": None, "title_ne": "विद्यालय प्रशासन", "title_en": "Administration", "url": "/administration", "icon": "shield-check", "order_index": 7},
    {"id": 8, "parent_id": None, "title_ne": "शैक्षिक कार्यक्रम", "title_en": "Academics", "url": "/academics", "icon": "graduation-cap", "order_index": 8},
    {"id": 9, "parent_id": None, "title_ne": "विद्यार्थी", "title_en": "Students", "url": "/students", "icon": "users", "order_index": 9},
    {"id": 10, "parent_id": None, "title_ne": "भर्ना", "title_en": "Admission", "url": "/admission", "icon": "user-plus", "order_index": 10},
    {"id": 11, "parent_id": None, "title_ne": "नतिजा", "title_en": "Results", "url": "/results", "icon": "award", "order_index": 11},
    {"id": 12, "parent_id": None, "title_ne": "नागरिक वडापत्र", "title_en": "Citizen Charter", "url": "/citizen-charter", "icon": "file-badge", "order_index": 12},
    {"id": 13, "parent_id": None, "title_ne": "शिक्षक", "title_en": "Teachers", "url": "/teachers", "icon": "briefcase", "order_index": 13},
    {"id": 14, "parent_id": None, "title_ne": "ग्यालेरी", "title_en": "Gallery", "url": "/gallery", "icon": "image", "order_index": 14},
    {"id": 15, "parent_id": None, "title_ne": "सम्पर्क", "title_en": "Contact", "url": "/contact", "icon": "map-pin", "order_index": 15},

    # Submenus for विद्यालय प्रशासन (parent_id = 7)
    {"id": 16, "parent_id": 7, "title_ne": "विद्यालय व्यवस्थापन समिति", "title_en": "School Management Committee", "url": "/management-committee", "icon": "users", "order_index": 1},
    {"id": 17, "parent_id": 7, "title_ne": "गुठियार समिति", "title_en": "Trustee Committee", "url": "/trustee-committee", "icon": "landmark", "order_index": 2},
    {"id": 18, "parent_id": 7, "title_ne": "प्रधानाध्यापक / नेतृत्व", "title_en": "Leadership", "url": "/leadership", "icon": "award", "order_index": 3},
    {"id": 19, "parent_id": 7, "title_ne": "शिक्षक तथा कर्मचारी", "title_en": "Teachers & Staff", "url": "/teachers", "icon": "briefcase", "order_index": 4},
    {"id": 20, "parent_id": 7, "title_ne": "समग्र प्रशासनिक संरचना", "title_en": "Administrative Structure", "url": "/administration", "icon": "shield-check", "order_index": 5},

    # Submenus for विद्यार्थी (parent_id = 9)
    {"id": 21, "parent_id": 9, "title_ne": "विद्यार्थी विवरण", "title_en": "Student Directory", "url": "/students", "icon": "table", "order_index": 1},
    {"id": 22, "parent_id": 9, "title_ne": "दैनिक हाजिरी पोर्टल", "title_en": "Daily Attendance Portal", "url": "/parent/login", "icon": "calendar-check", "order_index": 2},
    {"id": 23, "parent_id": 9, "title_ne": "दैनिक गृहकार्य (Homework)", "title_en": "Homework", "url": "/homework", "icon": "book-open-check", "order_index": 3},
    {"id": 24, "parent_id": 9, "title_ne": "परीक्षा नतिजा (Results)", "title_en": "Exam Results", "url": "/results", "icon": "file-check-2", "order_index": 4},
    {"id": 25, "parent_id": 9, "title_ne": "कक्षागत सूचना", "title_en": "Class Notices", "url": "/notices", "icon": "bell-ring", "order_index": 5},
    {"id": 26, "parent_id": 9, "title_ne": "अनलाइन बिदा निवेदन", "title_en": "Leave Application", "url": "/leave-application", "icon": "clipboard-pen", "order_index": 6},

    # Submenus for ग्यालेरी (parent_id = 14)
    {"id": 27, "parent_id": 14, "title_ne": "फोटो ग्यालेरी", "title_en": "Photo Gallery", "url": "/gallery", "icon": "images", "order_index": 1},
    {"id": 28, "parent_id": 14, "title_ne": "भिडियो ग्यालेरी", "title_en": "Video Gallery", "url": "/videos", "icon": "video", "order_index": 2},
]

@router.get("")
def get_menus():
    """List all menus structured hierarchically."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM header_menus ORDER BY order_index ASC, id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    top_menus = [m for m in rows if not m.get("parent_id")]
    for tm in top_menus:
        tm["children"] = [sm for sm in rows if sm.get("parent_id") == tm["id"]]

    return {"menus": top_menus, "all": rows}

@router.post("")
def create_menu(data: MenuCreate, request: Request):
    """Create a new main menu or sub-menu."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO header_menus (parent_id, title_ne, title_en, url, icon, order_index, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.parent_id, data.title_ne, data.title_en, data.url, data.icon, data.order_index, data.is_active))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_audit("CREATE", "HEADER_MENU", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "मेनु सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/{menu_id}")
def update_menu(menu_id: int, data: MenuCreate, request: Request):
    """Update existing menu or sub-menu."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE header_menus SET
            parent_id = ?, title_ne = ?, title_en = ?, url = ?, icon = ?, order_index = ?, is_active = ?
        WHERE id = ?
    """, (data.parent_id, data.title_ne, data.title_en, data.url, data.icon, data.order_index, data.is_active, menu_id))
    conn.commit()
    conn.close()

    log_audit("UPDATE", "HEADER_MENU", record_id=str(menu_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "मेनु सफलतापूर्वक अद्यावधिक भयो।"}

@router.delete("/{menu_id}")
def delete_menu(menu_id: int, request: Request):
    """Delete menu and its children sub-menus."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cur = conn.cursor()
    # Delete children first
    cur.execute("DELETE FROM header_menus WHERE parent_id = ?", (menu_id,))
    # Delete menu
    cur.execute("DELETE FROM header_menus WHERE id = ?", (menu_id,))
    conn.commit()
    conn.close()

    log_audit("DELETE", "HEADER_MENU", record_id=str(menu_id), user=user, request=request)
    return {"success": True, "message": "मेनु सफलतापूर्वक मेटाइयो।"}

@router.post("/reset")
def reset_menus(request: Request):
    """Reset menus to standard system defaults."""
    user = require_role("SUPER_ADMIN", "ADMIN")(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM header_menus")
    for m in DEFAULT_MENUS_SEED:
        cur.execute("""
            INSERT INTO header_menus (id, parent_id, title_ne, title_en, url, icon, order_index, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (m["id"], m["parent_id"], m["title_ne"], m["title_en"], m["url"], m["icon"], m["order_index"]))
    conn.commit()
    conn.close()

    log_audit("RESET", "HEADER_MENUS", user=user, request=request)
    return {"success": True, "message": "पूर्वनिर्धारित मुख्य तथा सब-मेनुहरू सफलतापूर्वक रिसेट गरियो।"}

@router.post("/settings/header")
def update_header_settings(data: HeaderSettingsUpdate, request: Request):
    """Update school logo, name, tagline, address in header."""
    user = require_role("SUPER_ADMIN", "ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE school_settings SET
            name_ne = ?, name_en = ?, tagline_ne = ?, tagline_en = ?,
            established_ne = COALESCE(?, established_ne),
            address_ne = COALESCE(?, address_ne),
            logo_url = COALESCE(?, logo_url),
            phone = COALESCE(?, phone),
            email = COALESCE(?, email),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (
        data.name_ne, data.name_en, data.tagline_ne, data.tagline_en,
        data.established_ne, data.address_ne, data.logo_url,
        data.phone, data.email
    ))
    conn.commit()
    conn.close()

    log_audit("UPDATE", "HEADER_SETTINGS", new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "विद्यालयको लोगो तथा नाम विवरण सफलतापूर्वक अद्यावधिक भयो।"}
