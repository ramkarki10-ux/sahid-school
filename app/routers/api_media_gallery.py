import re
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import require_auth
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/media-gallery", tags=["media_gallery"])

ALLOWED_ROLES = {"SUPER_ADMIN", "ADMIN", "PRINCIPAL"}

def require_gallery_admin(request: Request) -> Dict[str, Any]:
    """Strict Role-Based Access Control (RBAC):
    Only authenticated users with roles 'SUPER_ADMIN', 'ADMIN', or 'PRINCIPAL' are permitted.
    Public visitors, students, and parents have read-only access.
    """
    user = require_auth(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="प्रमाणीकरण आवश्यक छ। कृपया पहिले लगइन गर्नुहोस्।"
        )
    role = str(user.get("role", "")).upper()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="पहुँच अस्वीकृत: ग्यालेरी सम्पादन, अपलोड, बदल्ने वा मेटाउने अधिकार केवल एडमिन र प्रिन्सिपललाई मात्र छ।"
        )
    return user

def extract_youtube_id(url: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from various YouTube URL formats."""
    if not url:
        return None
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Pydantic Schemas
class MediaItemCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=250)
    description: Optional[str] = ""
    media_type: str = Field(..., pattern="^(photo|video)$")
    category: Optional[str] = "विद्यालय कार्यक्रम"
    media_url: str = Field(..., min_length=1)
    thumbnail_url: Optional[str] = ""
    external_link: Optional[str] = ""
    external_link_title: Optional[str] = ""
    youtube_id: Optional[str] = ""
    event_date: Optional[str] = ""
    is_featured: Optional[int] = 0
    display_order: Optional[int] = 0

class BatchMediaItem(BaseModel):
    title: str
    media_url: str
    thumbnail_url: Optional[str] = ""
    description: Optional[str] = ""

class MediaBatchCreate(BaseModel):
    media_type: str = "photo"
    category: Optional[str] = "विद्यालय कार्यक्रम"
    event_date: Optional[str] = ""
    description: Optional[str] = ""
    external_link: Optional[str] = ""
    external_link_title: Optional[str] = ""
    items: List[BatchMediaItem]

class MediaItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    event_date: Optional[str] = None
    external_link: Optional[str] = None
    external_link_title: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    youtube_id: Optional[str] = None
    is_featured: Optional[int] = None
    display_order: Optional[int] = None
    is_published: Optional[int] = None

class MediaReplacePayload(BaseModel):
    media_url: str = Field(..., min_length=1)
    thumbnail_url: Optional[str] = ""
    youtube_id: Optional[str] = ""

# ----------------------------------------------------
# 1. PUBLIC READ-ONLY ENDPOINTS
# ----------------------------------------------------
@router.get("")
def list_media_gallery(
    media_type: Optional[str] = Query(None, description="'photo', 'video', or None for all"),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Search query"),
    is_featured: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100)
):
    """Public read-only listing of photos and videos with search, category filtering, and pagination."""
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = ["is_published = 1"]
    params = []

    if media_type and media_type.lower() in ["photo", "video"]:
        where_clauses.append("media_type = ?")
        params.append(media_type.lower())

    if category and category.strip():
        where_clauses.append("category = ?")
        params.append(category.strip())

    if is_featured is not None:
        where_clauses.append("is_featured = ?")
        params.append(is_featured)

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(title LIKE ? OR description LIKE ? OR category LIKE ? OR external_link_title LIKE ?)")
        params.extend([term, term, term, term])

    where_sql = " AND ".join(where_clauses)

    # Total count
    cursor.execute(f"SELECT COUNT(*) FROM media_gallery WHERE {where_sql}", params)
    total = cursor.fetchone()[0]

    limit = max(1, min(page_size, 100))
    offset = max(0, (page - 1) * limit)
    total_pages = max(1, math.ceil(total / limit))

    # Fetch items ordered by display_order ASC, id DESC
    cursor.execute(
        f"SELECT * FROM media_gallery WHERE {where_sql} ORDER BY display_order ASC, id DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    items = [dict(r) for r in cursor.fetchall()]

    # Categories list with counts
    cursor.execute("""
        SELECT category, COUNT(*) as cnt 
        FROM media_gallery 
        WHERE is_published = 1 
        GROUP BY category 
        ORDER BY cnt DESC
    """)
    cat_rows = cursor.fetchall()
    categories = [{"name": r["category"] if isinstance(r, dict) else r[0], "count": r["cnt"] if isinstance(r, dict) else r[1]} for r in cat_rows]

    conn.close()

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "items": items,
        "categories": categories
    }

@router.get("/categories")
def get_gallery_categories():
    """Retrieve distinct categories for photos and videos."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT category FROM media_gallery WHERE is_published = 1 ORDER BY category ASC
    """)
    cats = [r[0] for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "categories": cats}

@router.get("/stats")
def get_gallery_stats():
    """Summary stats of gallery items."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM media_gallery WHERE media_type = 'photo' AND is_published = 1")
    total_photos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM media_gallery WHERE media_type = 'video' AND is_published = 1")
    total_videos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM media_gallery WHERE is_featured = 1 AND is_published = 1")
    featured = cursor.fetchone()[0]
    conn.close()
    return {
        "success": True,
        "total_photos": total_photos,
        "total_videos": total_videos,
        "featured_media": featured
    }

@router.get("/{media_id}")
def get_single_media(media_id: int):
    """Retrieve single media item details."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_gallery WHERE id = ?", (media_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="मिडिया फेला परेन।")
    return {"success": True, "media": dict(row)}

# ----------------------------------------------------
# 2. RBAC PROTECTED ENDPOINTS (Admin & Principal Only)
# ----------------------------------------------------
@router.post("")
def create_media_item(payload: MediaItemCreate, request: Request):
    """Upload/Add a new photo or video. Strictly restricted to Admin & Principal."""
    user = require_gallery_admin(request)

    m_type = payload.media_type.lower()
    m_url = payload.media_url.strip()
    title = payload.title.strip()
    desc = (payload.description or "").strip()
    cat = (payload.category or "विद्यालय कार्यक्रम").strip()
    ext_link = (payload.external_link or "").strip()
    ext_title = (payload.external_link_title or "").strip()
    event_date = (payload.event_date or "").strip()
    thumb_url = (payload.thumbnail_url or "").strip()

    # Extract YouTube ID if it's a video or YouTube link
    yt_id = payload.youtube_id or extract_youtube_id(m_url) or extract_youtube_id(ext_link) or ""
    if m_type == "video" and yt_id and not thumb_url:
        thumb_url = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
    elif m_type == "photo" and not thumb_url:
        thumb_url = m_url

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO media_gallery (
            title, description, media_type, category, media_url,
            thumbnail_url, external_link, external_link_title,
            youtube_id, event_date, uploaded_by, is_featured, display_order, is_published
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        title, desc, m_type, cat, m_url,
        thumb_url, ext_link, ext_title,
        yt_id, event_date, user.get("username", "admin"),
        payload.is_featured or 0, payload.display_order or 0
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_audit("MEDIA_CREATE", "GALLERY", record_id=str(new_id), user=user, request=request)

    return {
        "success": True,
        "message": f"{'तस्विर' if m_type == 'photo' else 'भिडियो'} सफलतापूर्वक थपियो।",
        "id": new_id
    }

@router.post("/batch")
def batch_create_media(payload: MediaBatchCreate, request: Request):
    """Upload multiple high-resolution photos or media items in batch. Strictly restricted to Admin & Principal."""
    user = require_gallery_admin(request)

    if not payload.items:
        raise HTTPException(status_code=400, detail="कम्तीमा एक तस्विर वा भिडियो आवश्यक छ।")

    conn = get_db()
    cursor = conn.cursor()
    inserted_count = 0

    m_type = payload.media_type.lower()
    cat = (payload.category or "विद्यालय कार्यक्रम").strip()
    event_date = (payload.event_date or "").strip()
    ext_link = (payload.external_link or "").strip()
    ext_title = (payload.external_link_title or "").strip()
    common_desc = (payload.description or "").strip()

    for idx, item in enumerate(payload.items):
        title = item.title.strip() if item.title else f"{cat} तस्विर #{idx+1}"
        m_url = item.media_url.strip()
        if not m_url:
            continue
        
        desc = item.description.strip() if item.description else common_desc
        thumb_url = item.thumbnail_url.strip() if item.thumbnail_url else m_url
        yt_id = extract_youtube_id(m_url) or ""

        cursor.execute("""
            INSERT INTO media_gallery (
                title, description, media_type, category, media_url,
                thumbnail_url, external_link, external_link_title,
                youtube_id, event_date, uploaded_by, is_featured, display_order, is_published
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 1)
        """, (
            title, desc, m_type, cat, m_url,
            thumb_url, ext_link, ext_title,
            yt_id, event_date, user.get("username", "admin"), idx
        ))
        inserted_count += 1

    conn.commit()
    conn.close()

    log_audit("MEDIA_BATCH_CREATE", "GALLERY", record_id=f"count:{inserted_count}", user=user, request=request)

    return {
        "success": True,
        "message": f"सफलतापूर्वक {inserted_count} वटा मिडिया फाइलहरू आयात गरियो।",
        "inserted_count": inserted_count
    }

@router.put("/{media_id}")
def update_media_item(media_id: int, payload: MediaItemUpdate, request: Request):
    """Update title, rich description, category, event date, external social links, etc. Strictly restricted to Admin & Principal."""
    user = require_gallery_admin(request)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_gallery WHERE id = ?", (media_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        raise HTTPException(status_code=404, detail="मिडिया फेला परेन।")

    fields = []
    params = []

    if payload.title is not None:
        fields.append("title = ?")
        params.append(payload.title.strip())

    if payload.description is not None:
        fields.append("description = ?")
        params.append(payload.description.strip())

    if payload.category is not None:
        fields.append("category = ?")
        params.append(payload.category.strip())

    if payload.event_date is not None:
        fields.append("event_date = ?")
        params.append(payload.event_date.strip())

    if payload.external_link is not None:
        fields.append("external_link = ?")
        params.append(payload.external_link.strip())

    if payload.external_link_title is not None:
        fields.append("external_link_title = ?")
        params.append(payload.external_link_title.strip())

    if payload.media_url is not None:
        fields.append("media_url = ?")
        params.append(payload.media_url.strip())
        yt = extract_youtube_id(payload.media_url.strip())
        if yt:
            fields.append("youtube_id = ?")
            params.append(yt)

    if payload.thumbnail_url is not None:
        fields.append("thumbnail_url = ?")
        params.append(payload.thumbnail_url.strip())

    if payload.is_featured is not None:
        fields.append("is_featured = ?")
        params.append(payload.is_featured)

    if payload.display_order is not None:
        fields.append("display_order = ?")
        params.append(payload.display_order)

    if payload.is_published is not None:
        fields.append("is_published = ?")
        params.append(payload.is_published)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    sql = f"UPDATE media_gallery SET {', '.join(fields)} WHERE id = ?"
    params.append(media_id)

    cursor.execute(sql, params)
    conn.commit()
    conn.close()

    log_audit("MEDIA_UPDATE", "GALLERY", record_id=str(media_id), user=user, request=request)

    return {"success": True, "message": "मिडिया विवरण सफलतापूर्वक सम्पादन भयो।"}

@router.post("/{media_id}/replace")
def replace_media_item(media_id: int, payload: MediaReplacePayload, request: Request):
    """Replace an existing photo or video file/URL cleanly without altering the existing title, rich description, or event date.
    Strictly restricted to Admin & Principal.
    """
    user = require_gallery_admin(request)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_gallery WHERE id = ?", (media_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="मिडिया फेला परेन।")

    current_item = dict(row)
    new_media_url = payload.media_url.strip()
    new_thumb = (payload.thumbnail_url or "").strip()
    yt_id = payload.youtube_id or extract_youtube_id(new_media_url) or ""

    if current_item["media_type"] == "video" and yt_id and not new_thumb:
        new_thumb = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
    elif current_item["media_type"] == "photo" and not new_thumb:
        new_thumb = new_media_url

    cursor.execute("""
        UPDATE media_gallery 
        SET media_url = ?, thumbnail_url = ?, youtube_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_media_url, new_thumb, yt_id, media_id))
    conn.commit()
    conn.close()

    log_audit("MEDIA_REPLACE", "GALLERY", record_id=str(media_id), user=user, request=request)

    return {
        "success": True,
        "message": f"सफलतापूर्वक {'तस्विर' if current_item['media_type'] == 'photo' else 'भिडियो'} प्रतिस्थापन (Replace) गरियो।",
        "new_media_url": new_media_url,
        "thumbnail_url": new_thumb
    }

@router.delete("/{media_id}")
def delete_media_item(media_id: int, request: Request):
    """Confirmation-based deletion of unwanted or outdated photos/videos. Strictly restricted to Admin & Principal."""
    user = require_gallery_admin(request)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_gallery WHERE id = ?", (media_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="मिडिया फेला परेन।")

    item_title = row["title"] if isinstance(row, dict) else row[1]
    cursor.execute("DELETE FROM media_gallery WHERE id = ?", (media_id,))
    conn.commit()
    conn.close()

    log_audit("MEDIA_DELETE", "GALLERY", record_id=str(media_id), old_value={"title": item_title}, user=user, request=request)

    return {"success": True, "message": f'"{item_title}" सफलतापूर्वक हटाइयो।'}
