from fastapi import APIRouter, Request, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import re
from app.database import get_db
from app.auth import require_role, require_auth
from app.utils.audit import log_audit
from app.utils.excel_handler import (
    export_notices_to_excel,
    export_publications_to_excel,
    export_admissions_to_excel,
    export_news_to_excel,
    export_contact_messages_to_excel
)

router = APIRouter(prefix="/api", tags=["content"])

# --- NOTICES ---
class NoticeCreate(BaseModel):
    title_ne: str
    title_en: Optional[str] = None
    description_ne: str
    description_en: Optional[str] = None
    category: Optional[str] = "सामान्य"
    publish_date: str
    expiry_date: Optional[str] = None
    attachment: Optional[str] = None
    featured: Optional[int] = 0
    status: Optional[str] = "सक्रिय"

@router.get("/notices")
def list_notices(
    category: Optional[str] = Query(None),
    featured_only: Optional[bool] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status")
):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM notices WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if featured_only:
        query += " AND featured = 1"
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    notices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"notices": notices}

@router.post("/notices")
def create_notice(data: NoticeCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notices (
            title_ne, title_en, description_ne, description_en, category,
            publish_date, expiry_date, attachment, featured, status, author_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.title_ne, data.title_en, data.description_ne, data.description_en,
        data.category, data.publish_date, data.expiry_date, data.attachment,
        data.featured, data.status, user["user_id"]
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "NOTICES", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "सूचना सफलतापूर्वक प्रकाशित भयो।", "id": new_id}

@router.put("/notices/{id}")
def update_notice(id: int, data: NoticeCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE notices SET
            title_ne = ?, title_en = ?, description_ne = ?, description_en = ?,
            category = ?, publish_date = ?, expiry_date = ?, attachment = ?,
            featured = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.title_ne, data.title_en, data.description_ne, data.description_en,
        data.category, data.publish_date, data.expiry_date, data.attachment,
        data.featured, data.status, id
    ))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "NOTICES", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "सूचना अद्यावधिक भयो।"}

@router.get("/notices/export")
def export_notices_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_notices_to_excel(notices)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=notices_data.xlsx"}
    )

@router.get("/notices/{id}")
def get_notice(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notices WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="सूचना फेला परेन।")
    return dict(row)

@router.delete("/notices/{id}")
def delete_notice(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notices WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "NOTICES", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "सूचना मेटाइयो।"}

# --- NEWS ---
class NewsCreate(BaseModel):
    title_ne: str
    title_en: Optional[str] = None
    content_ne: str
    content_en: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = "कार्यक्रम"
    publish_date: str
    featured: Optional[int] = 0
    status: Optional[str] = "सक्रिय"

@router.get("/news")
def list_news():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY id DESC")
    news_items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"news": news_items}

@router.get("/news/export")
def export_news_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY id DESC")
    news_items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_news_to_excel(news_items)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=news_data.xlsx"}
    )

@router.post("/news")
def create_news(data: NewsCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO news (
            title_ne, title_en, content_ne, content_en, image,
            category, publish_date, featured, status, author_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.title_ne, data.title_en, data.content_ne, data.content_en,
        data.image, data.category, data.publish_date, data.featured,
        data.status, user["user_id"]
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "NEWS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "समाचार सफलतापूर्वक थपियो।", "id": new_id}

@router.put("/news/{id}")
def update_news(id: int, data: NewsCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE news SET
            title_ne = ?, title_en = ?, content_ne = ?, content_en = ?,
            image = ?, category = ?, publish_date = ?, featured = ?,
            status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.title_ne, data.title_en, data.content_ne, data.content_en,
        data.image, data.category, data.publish_date, data.featured,
        data.status, id
    ))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "NEWS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "समाचार अद्यावधिक भयो।"}

@router.delete("/news/{id}")
def delete_news(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM news WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "NEWS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "समाचार मेटाइयो।"}

# --- PUBLICATIONS ---
class PublicationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: str
    file_type: Optional[str] = "PDF"
    category: Optional[str] = "विद्यालय प्रोफाइल"
    publish_date: Optional[str] = None
    status: Optional[str] = "सक्रिय"

@router.get("/publications")
def list_publications(category: Optional[str] = Query(None)):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM publications WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    pubs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"publications": pubs}

@router.post("/publications")
def create_publication(data: PublicationCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO publications (title, description, file_url, file_type, category, publish_date, status, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data.title, data.description, data.file_url, data.file_type, data.category, data.publish_date, data.status, user["user_id"]))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "PUBLICATIONS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "प्रकाशन थपियो।", "id": new_id}

@router.put("/publications/{id}")
def update_publication(id: int, data: PublicationCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE publications SET
            title = ?, description = ?, file_url = ?, file_type = ?,
            category = ?, publish_date = ?, status = ?
        WHERE id = ?
    """, (data.title, data.description, data.file_url, data.file_type, data.category, data.publish_date, data.status, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "PUBLICATIONS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "प्रकाशन अद्यावधिक भयो।"}

@router.get("/publications/export")
def export_publications_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publications ORDER BY id DESC")
    pubs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_publications_to_excel(pubs)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=publications_data.xlsx"}
    )

@router.delete("/publications/{id}")
def delete_publication(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM publications WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "PUBLICATIONS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "प्रकाशन मेटाइयो।"}

# --- VIDEOS ---
class VideoCreate(BaseModel):
    title: str
    youtube_url: str
    description: Optional[str] = None
    category: Optional[str] = "सांस्कृतिक"
    publish_date: Optional[str] = None

@router.get("/videos")
def list_videos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY id DESC")
    videos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"videos": videos}

@router.post("/videos")
def create_video(data: VideoCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    
    # Extract youtube id
    y_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", data.youtube_url)
    youtube_id = y_match.group(1) if y_match else "dQw4w9WgXcQ"
    thumbnail = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO videos (title, youtube_url, youtube_id, thumbnail, description, category, publish_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.title, data.youtube_url, youtube_id, thumbnail, data.description, data.category, data.publish_date))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "VIDEOS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "भिडियो थपियो।", "id": new_id}

@router.put("/videos/{id}")
def update_video(id: int, data: VideoCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    y_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", data.youtube_url)
    youtube_id = y_match.group(1) if y_match else "dQw4w9WgXcQ"
    thumbnail = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE videos SET
            title = ?, youtube_url = ?, youtube_id = ?, thumbnail = ?,
            description = ?, category = ?, publish_date = ?
        WHERE id = ?
    """, (data.title, data.youtube_url, youtube_id, thumbnail, data.description, data.category, data.publish_date, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "VIDEOS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "भिडियो अद्यावधिक भयो।"}

@router.delete("/videos/{id}")
def delete_video(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "VIDEOS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "भिडियो मेटाइयो।"}

# --- GALLERY ---
class AlbumCreate(BaseModel):
    title_ne: str
    title_en: Optional[str] = None
    cover_image: Optional[str] = "/static/images/hero-banner.jpg"
    category: Optional[str] = "विद्यालय कार्यक्रम"
    description_ne: Optional[str] = ""

class PhotoAdd(BaseModel):
    image_url: str
    caption_ne: Optional[str] = ""
    order_index: Optional[int] = 0

@router.get("/gallery")
def list_gallery():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo_albums ORDER BY id DESC")
    albums = [dict(a) for a in cursor.fetchall()]
    for alb in albums:
        cursor.execute("SELECT * FROM photos WHERE album_id = ? ORDER BY order_index ASC", (alb["id"],))
        alb["photos"] = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return {"albums": albums}

@router.post("/content/albums")
@router.post("/albums")
def create_album(data: AlbumCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO photo_albums (title_ne, title_en, cover_image, category, description_ne)
        VALUES (?, ?, ?, ?, ?)
    """, (data.title_ne, data.title_en or data.title_ne, data.cover_image, data.category, data.description_ne))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit("CREATE", "PHOTO_ALBUMS", record_id=str(new_id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "एल्बम सफलतापूर्वक सिर्जना गरियो।", "id": new_id}

@router.put("/content/albums/{id}")
@router.put("/albums/{id}")
def update_album(id: int, data: AlbumCreate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE photo_albums SET
            title_ne = ?, title_en = ?, cover_image = ?, category = ?, description_ne = ?
        WHERE id = ?
    """, (data.title_ne, data.title_en or data.title_ne, data.cover_image, data.category, data.description_ne, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "PHOTO_ALBUMS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": "एल्बम अद्यावधिक भयो।"}

@router.delete("/content/albums/{id}")
@router.delete("/albums/{id}")
def delete_album(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM photos WHERE album_id = ?", (id,))
    cursor.execute("DELETE FROM photo_albums WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "PHOTO_ALBUMS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "एल्बम र यसका तस्विरहरू मेटाइयो।"}

@router.post("/content/albums/{id}/photos")
def add_photo_to_album(id: int, data: PhotoAdd, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO photos (album_id, image_url, caption_ne, order_index)
        VALUES (?, ?, ?, ?)
    """, (id, data.image_url, data.caption_ne, data.order_index))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "message": "तस्विर एल्बममा थपियो।", "id": new_id}

@router.delete("/content/photos/{id}")
def delete_photo(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM photos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "तस्विर मेटाइयो।"}

# --- ADMISSION APPLICATIONS ---
class AdmissionCreate(BaseModel):
    student_name: str
    dob: str
    gender: str
    applying_class: str
    previous_school: Optional[str] = None
    parent_name: str
    guardian_name: Optional[str] = None
    mobile: str
    email: Optional[str] = None
    address: str
    message: Optional[str] = None

class AdmissionStatusUpdate(BaseModel):
    status: str
    remarks: Optional[str] = None

@router.get("/admissions")
def list_admissions(request: Request, status_filter: Optional[str] = Query(None, alias="status")):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM admission_applications WHERE 1=1"
    params = []
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"applications": rows}

@router.put("/admissions/{id}")
def update_admission_status(id: int, data: AdmissionStatusUpdate, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE admission_applications SET status = ?, remarks = ? WHERE id = ?
    """, (data.status, data.remarks, id))
    conn.commit()
    conn.close()
    log_audit("UPDATE", "ADMISSIONS", record_id=str(id), new_value=data.dict(), user=user, request=request)
    return {"success": True, "message": f"भर्ना आवेदनको स्थिति '{data.status}' मा अद्यावधिक भयो।"}

@router.delete("/admissions/{id}")
def delete_admission(id: int, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admission_applications WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_audit("DELETE", "ADMISSIONS", record_id=str(id), user=user, request=request)
    return {"success": True, "message": "भर्ना आवेदन सफलतापूर्वक हटाइयो।"}

@router.get("/admissions/export")
def export_admissions_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admission_applications ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_admissions_to_excel(rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=admissions_data.xlsx"}
    )

@router.post("/admission")
def submit_admission(data: AdmissionCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admission_applications (
            student_name, dob, gender, applying_class, previous_school,
            parent_name, guardian_name, mobile, email, address, message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.student_name, data.dob, data.gender, data.applying_class, data.previous_school,
        data.parent_name, data.guardian_name, data.mobile, data.email, data.address, data.message
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "message": "भर्ना आवेदन फाराम सफलतापूर्वक पेश भयो। हामी छिट्टै सम्पर्क गर्नेछौँ।", "id": new_id}

# --- CONTACT MESSAGES ---
class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    subject: Optional[str] = None
    message: str

@router.post("/contact")
def submit_contact(data: ContactCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contact_messages (name, email, phone, subject, message)
        VALUES (?, ?, ?, ?, ?)
    """, (data.name, data.email, data.phone, data.subject, data.message))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "message": "तपाईंको सन्देश सफलतापूर्वक पठाइयो। धन्यवाद!", "id": new_id}

@router.get("/contact/messages")
def list_contact_messages(request: Request):
    require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact_messages ORDER BY id DESC")
    msgs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"messages": msgs}

@router.delete("/contact/messages/{id}")
def delete_contact_message(id: int, request: Request):
    require_role("SUPER_ADMIN", "PRINCIPAL", "CONTENT_EDITOR")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_messages WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "सन्देश हटाइयो।"}

@router.get("/contact/export")
def export_contact_messages_route(request: Request):
    require_auth(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact_messages ORDER BY id DESC")
    msgs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    stream = export_contact_messages_to_excel(msgs)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=contact_messages.xlsx"}
    )

