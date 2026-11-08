import os
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, status, Query, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.templates import templates

router = APIRouter(tags=["feed"])

class CreatePostRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    notice_id: Optional[int] = None
    post_type: Optional[str] = "post" # 'post', 'notice_share', 'announcement', 'achievement'
    author_name: Optional[str] = None
    author_role: Optional[str] = None

class CreateCommentRequest(BaseModel):
    content: str
    author_name: Optional[str] = None
    author_role: Optional[str] = None

def get_author_info(request: Request, override_name: Optional[str] = None, override_role: Optional[str] = None):
    """Determine author identity from session or guest details."""
    user = get_current_user(request)
    if user:
        role_labels = {
            "SUPER_ADMIN": "प्रमुख एडमिन",
            "ADMIN": "प्रशासक",
            "PRINCIPAL": "प्रधानाध्यापक",
            "TEACHER": "शिक्षक",
            "STUDENT": "विद्यार्थी",
            "PARENT": "अभिभावक"
        }
        name = user.get("full_name_ne") or user.get("username") or "प्रयोगकर्ता"
        role = user.get("role", "USER")
        role_label = role_labels.get(role, role)
        avatar = user.get("avatar") or "/static/images/default-avatar.png"
        return {
            "user_id": user.get("user_id") or user.get("id"),
            "name": f"{name} ({role_label})" if role_label not in name else name,
            "role": role,
            "role_label": role_label,
            "avatar": avatar,
            "is_logged_in": True
        }
    
    # Guest user
    guest_name = (override_name.strip() if override_name else "विद्यार्थी / अभिभावक")
    guest_role = (override_role.strip() if override_role else "GUEST")
    return {
        "user_id": None,
        "name": guest_name,
        "role": guest_role,
        "role_label": "अतिथि / विद्यार्थी",
        "avatar": "/static/images/default-avatar.png",
        "is_logged_in": False
    }

def format_relative_time(dt_str: str) -> str:
    """Format timestamp into Nepali friendly relative time."""
    try:
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60:
            return "भर्खरै"
        elif seconds < 3600:
            mins = int(seconds // 60)
            return f"{mins} मिनेट अघि"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} घण्टा अघि"
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f"{days} दिन अघि"
        else:
            return dt_str[:10]
    except Exception:
        return dt_str[:10] if dt_str else "भर्खरै"

# ----------------- HTML PAGE VIEW -----------------
@router.get("/feed", response_class=HTMLResponse)
def feed_page(request: Request):
    """Facebook-style Dynamic News Feed Page for Shahid Smriti School."""
    conn = get_db()
    cursor = conn.cursor()

    # Get settings
    cursor.execute("SELECT * FROM school_settings WHERE id = 1")
    settings = dict(cursor.fetchone() or {})

    # Current user
    user = get_current_user(request)
    current_user_id = user.get("user_id") if user else None

    # Fetch Posts with details
    cursor.execute("""
        SELECT p.*, n.title_ne as notice_title, n.publish_date as notice_date, n.attachment as notice_attachment, n.category as notice_category
        FROM feed_posts p
        LEFT JOIN notices n ON p.notice_id = n.id
        WHERE p.status = 'ACTIVE'
        ORDER BY p.id DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()

    posts = []
    for r in rows:
        p = dict(r)
        p["relative_time"] = format_relative_time(p.get("created_at") or "")
        
        # Check if current user liked
        p["has_liked"] = False
        if current_user_id:
            cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (p["id"], current_user_id))
            p["has_liked"] = bool(cursor.fetchone())

        # Fetch comments for this post
        cursor.execute("""
            SELECT * FROM post_comments 
            WHERE post_id = ? 
            ORDER BY id ASC
        """, (p["id"],))
        comments = []
        for c in cursor.fetchall():
            cd = dict(c)
            cd["relative_time"] = format_relative_time(cd.get("created_at") or "")
            comments.append(cd)
        p["comments"] = comments

        posts.append(p)

    # Fetch trending notices for sidebar
    cursor.execute("SELECT * FROM notices WHERE status = 'सक्रिय' ORDER BY id DESC LIMIT 5")
    trending_notices = [dict(r) for r in cursor.fetchall()]

    # Fetch upcoming calendar events for sidebar
    cursor.execute("SELECT * FROM school_calendar_events ORDER BY start_date ASC LIMIT 4")
    upcoming_events = [dict(r) for r in cursor.fetchall()]

    # Quick stats
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'सक्रिय'")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM teachers WHERE status = 'सक्रिय'")
    total_teachers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM feed_posts WHERE status = 'ACTIVE'")
    total_posts = cursor.fetchone()[0]

    conn.close()

    return templates.TemplateResponse(request, "public/feed.html", {
        "request": request,
        "settings": settings,
        "current_user": user,
        "posts": posts,
        "trending_notices": trending_notices,
        "upcoming_events": upcoming_events,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_posts": total_posts,
        "active_menu": "feed"
    })

# ----------------- REST API ENDPOINTS -----------------
@router.get("/api/feed/posts")
def get_feed_posts(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get list of active posts with comments and like status."""
    conn = get_db()
    cursor = conn.cursor()
    user = get_current_user(request)
    current_user_id = user.get("user_id") if user else None

    cursor.execute("""
        SELECT p.*, n.title_ne as notice_title, n.publish_date as notice_date, n.attachment as notice_attachment, n.category as notice_category
        FROM feed_posts p
        LEFT JOIN notices n ON p.notice_id = n.id
        WHERE p.status = 'ACTIVE'
        ORDER BY p.id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()

    posts = []
    for r in rows:
        p = dict(r)
        p["relative_time"] = format_relative_time(p.get("created_at") or "")
        p["has_liked"] = False
        if current_user_id:
            cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (p["id"], current_user_id))
            p["has_liked"] = bool(cursor.fetchone())

        # Comments
        cursor.execute("SELECT * FROM post_comments WHERE post_id = ? ORDER BY id ASC", (p["id"],))
        comments = []
        for c in cursor.fetchall():
            cd = dict(c)
            cd["relative_time"] = format_relative_time(cd.get("created_at") or "")
            comments.append(cd)
        p["comments"] = comments
        posts.append(p)

    conn.close()
    return {"success": True, "count": len(posts), "posts": posts}

@router.post("/api/feed/posts")
def create_feed_post(req: CreatePostRequest, request: Request):
    """Create a new post in the school feed."""
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="पोस्टको विवरण खाली हुन सक्दैन।")

    author = get_author_info(request, req.author_name, req.author_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO feed_posts (
            author_id, author_name, author_role, author_avatar, content,
            image_url, notice_id, post_type, likes_count, comments_count, shares_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
    """, (
        author["user_id"],
        author["name"],
        author["role"],
        author["avatar"],
        content,
        req.image_url,
        req.notice_id,
        req.post_type or "post"
    ))
    new_id = cursor.lastrowid
    conn.commit()

    # Retrieve created post
    cursor.execute("""
        SELECT p.*, n.title_ne as notice_title 
        FROM feed_posts p 
        LEFT JOIN notices n ON p.notice_id = n.id 
        WHERE p.id = ?
    """, (new_id,))
    created_post = dict(cursor.fetchone())
    created_post["relative_time"] = "भर्खरै"
    created_post["has_liked"] = False
    created_post["comments"] = []

    conn.close()

    return {
        "success": True,
        "message": "तपाईंको पोस्ट सफलतापूर्वक प्रकाशित भयो!",
        "post": created_post
    }

@router.post("/api/feed/posts/{post_id}/like")
def toggle_post_like(post_id: int, request: Request):
    """Toggle like/unlike on a post with instant counter updates."""
    user = get_current_user(request)
    user_id = user.get("user_id") if user else None
    user_name = (user.get("full_name_ne") or user.get("username")) if user else "शुभचिन्तक"
    user_role = user.get("role", "GUEST") if user else "GUEST"

    conn = get_db()
    cursor = conn.cursor()

    # Check post existence
    cursor.execute("SELECT id, likes_count FROM feed_posts WHERE id = ? AND status = 'ACTIVE'", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="पोस्ट फेला परेन।")

    # Check existing like
    if user_id:
        cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"
        cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id IS NULL AND user_name = ?", (post_id, client_ip))
    existing_like = cursor.fetchone()

    if existing_like:
        # Unlike
        cursor.execute("DELETE FROM post_likes WHERE id = ?", (existing_like["id"],))
        cursor.execute("UPDATE feed_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
        liked = False
    else:
        # Like
        like_user_name = user_name if user_id else (request.client.host if request.client else "127.0.0.1")
        cursor.execute("""
            INSERT INTO post_likes (post_id, user_id, user_name, user_role)
            VALUES (?, ?, ?, ?)
        """, (post_id, user_id, like_user_name, user_role))
        cursor.execute("UPDATE feed_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        liked = True

    conn.commit()

    # Get updated count
    cursor.execute("SELECT likes_count FROM feed_posts WHERE id = ?", (post_id,))
    new_likes_count = cursor.fetchone()["likes_count"]
    conn.close()

    return {
        "success": True,
        "liked": liked,
        "likes_count": new_likes_count
    }

@router.get("/api/feed/posts/{post_id}/comments")
def get_post_comments(post_id: int):
    """Get comments for a specific post."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM post_comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
    comments = []
    for c in cursor.fetchall():
        cd = dict(c)
        cd["relative_time"] = format_relative_time(cd.get("created_at") or "")
        comments.append(cd)
    conn.close()
    return {"success": True, "comments": comments}

@router.post("/api/feed/posts/{post_id}/comment")
def add_post_comment(post_id: int, req: CreateCommentRequest, request: Request):
    """Add a new comment to a post."""
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="कमेन्ट खाली हुन सक्दैन।")

    author = get_author_info(request, req.author_name, req.author_role)

    conn = get_db()
    cursor = conn.cursor()

    # Check post existence
    cursor.execute("SELECT id, comments_count FROM feed_posts WHERE id = ? AND status = 'ACTIVE'", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="पोस्ट फेला परेन।")

    cursor.execute("""
        INSERT INTO post_comments (post_id, user_id, user_name, user_role, user_avatar, content)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        author["user_id"],
        author["name"],
        author["role"],
        author["avatar"],
        content
    ))
    new_comment_id = cursor.lastrowid
    cursor.execute("UPDATE feed_posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))
    conn.commit()

    # Fetch created comment
    cursor.execute("SELECT * FROM post_comments WHERE id = ?", (new_comment_id,))
    created_comment = dict(cursor.fetchone())
    created_comment["relative_time"] = "भर्खरै"

    # Fetch total comments count
    cursor.execute("SELECT comments_count FROM feed_posts WHERE id = ?", (post_id,))
    total_comments = cursor.fetchone()["comments_count"]

    conn.close()

    return {
        "success": True,
        "message": "कमेन्ट सफलतापूर्वक थपियो!",
        "comment": created_comment,
        "comments_count": total_comments
    }

@router.delete("/api/feed/posts/{post_id}")
def delete_feed_post(post_id: int, request: Request):
    """Delete a post (only author or admin allowed)."""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM feed_posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="पोस्ट फेला परेन।")

    post_dict = dict(post)
    is_admin = user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]
    is_author = user and user.get("user_id") == post_dict.get("author_id")

    if not (is_admin or is_author):
        conn.close()
        raise HTTPException(status_code=403, detail="तपाईंसँग यो पोस्ट मेटाउने अनुमति छैन।")

    cursor.execute("DELETE FROM feed_posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "पोस्ट सफलतापूर्वक मेटाइयो।"}

@router.delete("/api/feed/comments/{comment_id}")
def delete_post_comment(comment_id: int, request: Request):
    """Delete a comment (only author or admin allowed)."""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM post_comments WHERE id = ?", (comment_id,))
    cmt = cursor.fetchone()
    if not cmt:
        conn.close()
        raise HTTPException(status_code=404, detail="कमेन्ट फेला परेन।")

    cmt_dict = dict(cmt)
    is_admin = user and user.get("role") in ["SUPER_ADMIN", "ADMIN", "PRINCIPAL"]
    is_author = user and user.get("user_id") == cmt_dict.get("user_id")

    if not (is_admin or is_author):
        conn.close()
        raise HTTPException(status_code=403, detail="कमेन्ट मेटाउने अनुमति छैन।")

    post_id = cmt_dict["post_id"]
    cursor.execute("DELETE FROM post_comments WHERE id = ?", (comment_id,))
    cursor.execute("UPDATE feed_posts SET comments_count = MAX(0, comments_count - 1) WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "कमेन्ट मेटाइयो।"}

@router.post("/api/feed/share-notice/{notice_id}")
def share_notice_to_feed(notice_id: int, request: Request):
    """Share an official notice directly to the Facebook-style Feed."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notices WHERE id = ?", (notice_id,))
    notice = cursor.fetchone()
    if not notice:
        conn.close()
        raise HTTPException(status_code=404, detail="सूचना फेला परेन।")

    n = dict(notice)
    author = get_author_info(request)

    share_text = f"📢 विद्यालयको आधिकारिक सूचना: {n['title_ne']}\n\n{n.get('description_ne', '')[:200]}..."

    cursor.execute("""
        INSERT INTO feed_posts (
            author_id, author_name, author_role, author_avatar, content,
            notice_id, post_type, likes_count, comments_count, shares_count
        ) VALUES (?, ?, ?, ?, ?, ?, 'notice_share', 0, 0, 1)
    """, (
        author["user_id"],
        author["name"],
        author["role"],
        author["avatar"],
        share_text,
        notice_id
    ))
    new_post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "सूचना सफलतापूर्वक न्युज फिडमा सेयर भयो!",
        "post_id": new_post_id
    }
