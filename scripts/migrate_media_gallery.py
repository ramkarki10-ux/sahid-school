import sqlite3
import os

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS media_gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    media_type TEXT NOT NULL, -- 'photo' or 'video'
    category TEXT NOT NULL DEFAULT 'विद्यालय कार्यक्रम',
    media_url TEXT NOT NULL,
    thumbnail_url TEXT DEFAULT '',
    external_link TEXT DEFAULT '',
    external_link_title TEXT DEFAULT '',
    youtube_id TEXT DEFAULT '',
    event_date TEXT DEFAULT '',
    uploaded_by TEXT DEFAULT 'admin',
    is_featured INTEGER DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    is_published INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_gallery_type ON media_gallery(media_type);
CREATE INDEX IF NOT EXISTS idx_media_gallery_category ON media_gallery(category);
CREATE INDEX IF NOT EXISTS idx_media_gallery_created_at ON media_gallery(created_at DESC);
"""

INITIAL_MEDIA = [
    # --- PHOTOS ---
    {
        "title": "१६ औं वार्षिकोत्सव तथा अभिभावक दिवस २०८२",
        "description": "विद्यालयको १६ औं वार्षिकोत्सव तथा अभिभावक दिवस समारोहमा विभिन्न विशिष्ट व्यक्तित्वहरूको उपस्थिति, विद्यार्थीहरूको सांस्कृतिक झाँकी तथा शैक्षिक पुरस्कार वितरण।",
        "media_type": "photo",
        "category": "विद्यालय कार्यक्रम",
        "media_url": "/static/images/hero-banner.jpg",
        "thumbnail_url": "/static/images/hero-banner.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "फेसबुकमा सम्पूर्ण फोटोहरू हेर्नुहोस्",
        "youtube_id": "",
        "event_date": "२०८२/११/२५",
        "uploaded_by": "admin",
        "is_featured": 1,
        "display_order": 1
    },
    {
        "title": "विज्ञान तथा रोबोटिक्स प्रदर्शनी २०८२",
        "description": "कक्षा ८ देखि १२ सम्मका विद्यार्थीहरूद्वारा निर्मित स्वचालित रोबोट, स्मार्ट सिँचाइ प्रणाली, र हाइड्रोइलेक्ट्रिक मोडलहरूको भव्य प्रदर्शनी।",
        "media_type": "photo",
        "category": "शैक्षिक",
        "media_url": "/static/images/slider_admission.jpg",
        "thumbnail_url": "/static/images/slider_admission.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "विज्ञान प्रदर्शनी फेसबुक एल्बम",
        "youtube_id": "",
        "event_date": "२०८२/१०/१५",
        "uploaded_by": "admin",
        "is_featured": 1,
        "display_order": 2
    },
    {
        "title": "अन्तर-सदन वार्षिक एथलेटिक्स तथा फुटबल प्रतियोगिता",
        "description": "विद्यार्थीहरूको शारीरिक विकास र खेल भावना अभिवृद्धि गर्न आयोजित वार्षिक खेलकुद सप्ताह अन्तर्गत १०० मिटर दौड, भलिबल र फुटबलका रोमाञ्चक क्षणहरू।",
        "media_type": "photo",
        "category": "खेलकुद",
        "media_url": "/static/images/slider_hostel.jpg",
        "thumbnail_url": "/static/images/slider_hostel.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "खेलकुद तस्विर ग्यालेरी",
        "youtube_id": "",
        "event_date": "२०८२/०९/२२",
        "uploaded_by": "admin",
        "is_featured": 0,
        "display_order": 3
    },
    {
        "title": "मौलिक नेपाली सांस्कृतिक नृत्य तथा नाटक प्रस्तुति",
        "description": "विविध जातजाति तथा संस्कृतिको झल्को दिने थारु, तामाङ सेलो, साकेला र मारुनी नृत्य प्रतियोगिताका मनमोहक तस्विरहरू।",
        "media_type": "photo",
        "category": "सांस्कृतिक",
        "media_url": "/static/images/hero-banner.jpg",
        "thumbnail_url": "/static/images/hero-banner.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "सांस्कृतिक कार्यक्रम पोस्ट",
        "youtube_id": "",
        "event_date": "२०८२/०८/१८",
        "uploaded_by": "admin",
        "is_featured": 0,
        "display_order": 4
    },
    {
        "title": "छात्रावास विद्यार्थीहरूको योग, ध्यान तथा सामूहिक अध्ययन",
        "description": "आवासीय सुविधा अन्तर्गत विद्यार्थीहरूको नियमित बिहानी योग, प्राणायाम तथा बेलुकीको सामूहिक अध्ययन सत्रका तस्विरहरू।",
        "media_type": "photo",
        "category": "छात्रावास",
        "media_url": "/static/images/slider_hostel.jpg",
        "thumbnail_url": "/static/images/slider_hostel.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "छात्रावास जीवन विवरण",
        "youtube_id": "",
        "event_date": "२०८२/०७/१०",
        "uploaded_by": "admin",
        "is_featured": 0,
        "display_order": 5
    },
    {
        "title": "शैक्षिक तथा जैविक विविधता अध्ययन अवलोकन भ्रमण (इलाम-कन्याम)",
        "description": "कक्षा ९ र १० का विद्यार्थीहरूका लागि आयोजित ३ दिने चिया बगान, जैविक विविधता र स्थानीय पर्यावरण अध्ययन अवलोकन भ्रमण।",
        "media_type": "photo",
        "category": "भ्रमण",
        "media_url": "/static/images/slider_admission.jpg",
        "thumbnail_url": "/static/images/slider_admission.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "भ्रमण तस्विरहरू",
        "youtube_id": "",
        "event_date": "२०८२/०६/१४",
        "uploaded_by": "admin",
        "is_featured": 0,
        "display_order": 6
    },
    # --- VIDEOS ---
    {
        "title": "सहिद स्मृति आवासीय मावि वृत्तचित्र तथा विद्यालय परिचय",
        "description": "विद्यालयको स्थापना, उद्देश्य, सुविधा सम्पन्न भौतिक पूर्वाधार, आवासीय व्यवस्था तथा शैक्षिक गतिविधिसम्बन्धी आधिकारिक वृत्तचित्र।",
        "media_type": "video",
        "category": "विद्यालय कार्यक्रम",
        "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "external_link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "external_link_title": "YouTube मा पूरा वृत्तचित्र हेर्नुहोस्",
        "youtube_id": "dQw4w9WgXcQ",
        "event_date": "२०८२/१२/०१",
        "uploaded_by": "admin",
        "is_featured": 1,
        "display_order": 1
    },
    {
        "title": "वार्षिक सांस्कृतिक कार्यक्रम २०८२ का आकर्षक प्रस्तुतिहरू",
        "description": "विद्यार्थीहरूद्वारा प्रस्तुत नेपाली मौलिक नृत्य, नाटक तथा साङ्गीतिक प्रस्तुतिहरू।",
        "media_type": "video",
        "category": "सांस्कृतिक",
        "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "external_link": "https://www.facebook.com/profile.php?id=100092258731456",
        "external_link_title": "फेसबुक लाइभ स्ट्रिम रेकर्डिङ",
        "youtube_id": "dQw4w9WgXcQ",
        "event_date": "२०८२/११/२०",
        "uploaded_by": "admin",
        "is_featured": 1,
        "display_order": 2
    },
    {
        "title": "अन्तर-विद्यालय विज्ञान प्रदर्शनी तथा विद्यार्थी अन्तरक्रिया",
        "description": "सुनसरी र मोरङ जिल्लाका विभिन्न विद्यालयहरूबीच सम्पन्न विज्ञान तथा प्रविधि प्रदर्शनीको भिडियो संकलन।",
        "media_type": "video",
        "category": "शैक्षिक",
        "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "external_link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "external_link_title": "YouTube भिडियो लिंक",
        "youtube_id": "dQw4w9WgXcQ",
        "event_date": "२०८२/१०/१८",
        "uploaded_by": "admin",
        "is_featured": 0,
        "display_order": 3
    }
]

def migrate_db(db_path):
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create table & indexes
    cur.executescript(SCHEMA_SQL)
    
    # Check current count
    cur.execute("SELECT count(*) FROM media_gallery")
    cnt = cur.fetchone()[0]
    print(f"  Existing media_gallery records: {cnt}")
    
    if cnt == 0:
        insert_sql = """
        INSERT INTO media_gallery (
            title, description, media_type, category, media_url,
            thumbnail_url, external_link, external_link_title,
            youtube_id, event_date, uploaded_by, is_featured, display_order
        ) VALUES (
            :title, :description, :media_type, :category, :media_url,
            :thumbnail_url, :external_link, :external_link_title,
            :youtube_id, :event_date, :uploaded_by, :is_featured, :display_order
        )
        """
        for item in INITIAL_MEDIA:
            cur.execute(insert_sql, item)
        print(f"  Inserted {len(INITIAL_MEDIA)} initial media records.")
    
    conn.commit()
    conn.close()
    print(f"✓ Migration complete for {db_path}")

if __name__ == "__main__":
    for db in ['school.db', 'api/school.db']:
        if os.path.exists(db):
            migrate_db(db)
