import sqlite3
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

def _find_source_db():
    candidates = [
        Path(__file__).resolve().parent.parent / "school.db",
        Path(__file__).resolve().parent.parent / "api" / "school.db",
        Path("/var/task/school.db"),
        Path("/var/task/api/school.db"),
        Path.cwd() / "school.db",
        Path.cwd() / "api" / "school.db",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

SOURCE_DB_PATH = _find_source_db()

# On Vercel / Serverless environments, copy database to /tmp so read and write operations succeed
if IS_SERVERLESS:
    DB_PATH = Path("/tmp/school.db")
    if not DB_PATH.exists() and SOURCE_DB_PATH.exists():
        try:
            shutil.copy2(SOURCE_DB_PATH, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = SOURCE_DB_PATH

_db_initialized = False

def get_db():
    global _db_initialized
    if IS_SERVERLESS and not DB_PATH.exists():
        src = _find_source_db()
        if src.exists():
            try:
                shutil.copy2(src, DB_PATH)
            except Exception:
                pass
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    if not _db_initialized:
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='school_settings'")
            if not cur.fetchone():
                init_db()
            _db_initialized = True
        except Exception:
            pass

    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. School Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ne TEXT NOT NULL,
        name_en TEXT NOT NULL,
        tagline_ne TEXT,
        tagline_en TEXT,
        address_ne TEXT NOT NULL,
        address_en TEXT NOT NULL,
        established_ne TEXT NOT NULL DEFAULT '२०६६',
        established_en TEXT NOT NULL DEFAULT '2009',
        phone TEXT NOT NULL,
        notice_board_phone TEXT,
        email TEXT NOT NULL,
        facebook_url TEXT,
        youtube_url TEXT,
        twitter_url TEXT,
        logo_url TEXT,
        about_text_ne TEXT,
        about_text_en TEXT,
        active_academic_year_id INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Roles and Permissions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        display_name_ne TEXT NOT NULL,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        module TEXT NOT NULL,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER,
        permission_id INTEGER,
        PRIMARY KEY (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
        FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
    );
    """)

    # 3. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        full_name_ne TEXT NOT NULL,
        full_name_en TEXT,
        phone TEXT,
        role TEXT NOT NULL DEFAULT 'VIEWER',
        teacher_id INTEGER,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3.1 User Registrations (Self Signup & Approval Queue)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type TEXT NOT NULL, -- 'STUDENT', 'TEACHER', 'PARENT'
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name_ne TEXT NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        class_id INTEGER,
        class_name TEXT,
        roll_no INTEGER,
        guardian_name TEXT,
        guardian_phone TEXT,
        subject TEXT,
        student_name TEXT,
        student_phone TEXT,
        status TEXT NOT NULL DEFAULT 'विचाराधीन', -- 'विचाराधीन', 'स्वीकृत', 'अस्वीकृत'
        reviewed_by INTEGER,
        reviewed_at TIMESTAMP,
        review_remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (reviewed_by) REFERENCES users(id)
    );
    """)

    # Parent accounts table (for parent portal)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parent_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        pin_hash TEXT NOT NULL,
        guardian_name TEXT,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Academic Years, Classes, Sections, Streams
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_ne TEXT UNIQUE NOT NULL,
        year_en TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        is_active INTEGER DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name_ne TEXT NOT NULL,
        class_name_en TEXT NOT NULL,
        class_numeric INTEGER UNIQUE NOT NULL,
        has_stream INTEGER DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        name TEXT NOT NULL,
        capacity INTEGER DEFAULT 45,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS streams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ne TEXT NOT NULL,
        name_en TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        stream_id INTEGER,
        subject_name_ne TEXT NOT NULL,
        subject_name_en TEXT NOT NULL,
        subject_code TEXT,
        theory_marks REAL DEFAULT 75,
        practical_marks REAL DEFAULT 25,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE SET NULL
    );
    """)

    # 5. Hostels & Transport
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hostels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostel_name TEXT NOT NULL,
        warden TEXT,
        warden_phone TEXT,
        capacity INTEGER DEFAULT 100,
        gender TEXT DEFAULT 'ALL',
        status TEXT DEFAULT 'ACTIVE'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hostel_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostel_id INTEGER,
        room_number TEXT NOT NULL,
        floor INTEGER DEFAULT 1,
        capacity INTEGER DEFAULT 4,
        status TEXT DEFAULT 'AVAILABLE',
        FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_number TEXT NOT NULL,
        route TEXT NOT NULL,
        driver_name TEXT,
        driver_phone TEXT,
        helper_name TEXT,
        helper_phone TEXT,
        capacity INTEGER DEFAULT 35,
        status TEXT DEFAULT 'ACTIVE'
    );
    """)

    # 6. Teachers & Staff
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        name_nepali TEXT NOT NULL,
        name_english TEXT NOT NULL,
        photo TEXT,
        position TEXT NOT NULL,
        subject TEXT NOT NULL,
        level TEXT NOT NULL,
        qualification TEXT,
        experience TEXT,
        phone TEXT NOT NULL,
        email TEXT,
        appointment_date TEXT,
        employment_type TEXT DEFAULT 'स्थायी',
        academic_year_id INTEGER,
        status TEXT DEFAULT 'सक्रिय',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teacher_class_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        academic_year_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        subject_id INTEGER,
        is_class_teacher INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE SET NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        name_nepali TEXT NOT NULL,
        name_english TEXT NOT NULL,
        photo TEXT,
        position TEXT NOT NULL,
        department TEXT NOT NULL,
        qualification TEXT,
        phone TEXT NOT NULL,
        email TEXT,
        appointment_date TEXT,
        employment_type TEXT DEFAULT 'स्थायी',
        status TEXT DEFAULT 'सक्रिय',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. Students & Student Class History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        admission_no TEXT UNIQUE NOT NULL,
        registration_no TEXT,
        name_nepali TEXT NOT NULL,
        name_english TEXT NOT NULL,
        photo TEXT,
        gender TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        roll_no INTEGER NOT NULL,
        address TEXT NOT NULL,
        district TEXT DEFAULT 'सुनसरी',
        municipality TEXT DEFAULT 'इटहरी उपमहानगरपालिका',
        ward TEXT DEFAULT '१९',
        tole TEXT,
        father_name TEXT,
        mother_name TEXT,
        guardian_name TEXT NOT NULL,
        guardian_relation TEXT NOT NULL,
        guardian_phone TEXT NOT NULL,
        emergency_contact TEXT,
        residential_status TEXT DEFAULT 'दिवा',
        hostel_id INTEGER,
        room_id INTEGER,
        bed_no TEXT,
        bus_id INTEGER,
        pickup_point TEXT,
        academic_year_id INTEGER NOT NULL,
        status TEXT DEFAULT 'सक्रिय',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (section_id) REFERENCES sections(id),
        FOREIGN KEY (hostel_id) REFERENCES hostels(id),
        FOREIGN KEY (bus_id) REFERENCES buses(id),
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_class_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        academic_year_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        roll_no INTEGER NOT NULL,
        stream_id INTEGER,
        promotion_status TEXT DEFAULT 'PROMOTED',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id),
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (section_id) REFERENCES sections(id),
        FOREIGN KEY (stream_id) REFERENCES streams(id)
    );
    """)

    # 8. Attendance (with unique constraint on student_id + attendance_date)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        academic_year_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        section_id INTEGER,
        status TEXT NOT NULL CHECK(status IN ('PRESENT', 'ABSENT', 'LEAVE')),
        remark TEXT,
        recorded_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, attendance_date),
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id),
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (section_id) REFERENCES sections(id)
    );
    """)

    # 9. Committees & Leadership
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_management_committee (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        phone TEXT,
        photo TEXT,
        term TEXT DEFAULT '२०८०-२०८३',
        order_index INTEGER DEFAULT 0,
        status TEXT DEFAULT 'सक्रिय',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trustee_committee (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        phone TEXT,
        photo TEXT,
        order_index INTEGER DEFAULT 0,
        status TEXT DEFAULT 'सक्रिय',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS school_leadership (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_type TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        photo TEXT,
        qualification TEXT,
        experience TEXT,
        phone TEXT,
        email TEXT,
        message_ne TEXT,
        biography TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. Notices, News, Publications, Facilities
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title_ne TEXT NOT NULL,
        title_en TEXT,
        description_ne TEXT NOT NULL,
        description_en TEXT,
        category TEXT DEFAULT 'सामान्य',
        publish_date TEXT NOT NULL,
        expiry_date TEXT,
        attachment TEXT,
        featured INTEGER DEFAULT 0,
        status TEXT DEFAULT 'सक्रिय',
        author_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title_ne TEXT NOT NULL,
        title_en TEXT,
        content_ne TEXT NOT NULL,
        content_en TEXT,
        image TEXT,
        category TEXT DEFAULT 'कार्यक्रम',
        publish_date TEXT NOT NULL,
        author_id INTEGER,
        featured INTEGER DEFAULT 0,
        status TEXT DEFAULT 'सक्रिय',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photo_albums (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title_ne TEXT NOT NULL,
        title_en TEXT,
        cover_image TEXT,
        category TEXT DEFAULT 'विद्यालय कार्यक्रम',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        album_id INTEGER,
        image_url TEXT NOT NULL,
        caption_ne TEXT,
        caption_en TEXT,
        is_featured INTEGER DEFAULT 0,
        order_index INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (album_id) REFERENCES photo_albums(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        youtube_url TEXT NOT NULL,
        youtube_id TEXT NOT NULL,
        thumbnail TEXT,
        description TEXT,
        category TEXT DEFAULT 'सांस्कृतिक',
        publish_date TEXT,
        status TEXT DEFAULT 'सक्रिय',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        file_url TEXT NOT NULL,
        file_type TEXT DEFAULT 'PDF',
        category TEXT DEFAULT 'विद्यालय प्रोफाइल',
        publish_date TEXT,
        status TEXT DEFAULT 'सक्रिय',
        uploaded_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        image TEXT,
        description TEXT NOT NULL,
        display_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'सक्रिय'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'शैक्षिक',
        year TEXT NOT NULL,
        description TEXT NOT NULL,
        image TEXT,
        display_order INTEGER DEFAULT 0
    );
    """)

    # 11. Admissions & Contact
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admission_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        dob TEXT NOT NULL,
        gender TEXT NOT NULL,
        applying_class TEXT NOT NULL,
        previous_school TEXT,
        parent_name TEXT NOT NULL,
        guardian_name TEXT,
        mobile TEXT NOT NULL,
        email TEXT,
        address TEXT NOT NULL,
        message TEXT,
        status TEXT DEFAULT 'नयाँ',
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT NOT NULL,
        subject TEXT,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 12. Exams & Results Architecture
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ne TEXT NOT NULL,
        name_en TEXT NOT NULL,
        academic_year_id INTEGER,
        term TEXT,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'PLANNED',
        FOREIGN KEY (academic_year_id) REFERENCES academic_years(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        full_marks REAL DEFAULT 100,
        pass_marks REAL DEFAULT 35,
        FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        theory_obtained REAL DEFAULT 0,
        practical_obtained REAL DEFAULT 0,
        total_obtained REAL DEFAULT 0,
        grade TEXT,
        grade_point REAL,
        remarks TEXT,
        UNIQUE(exam_id, student_id, subject_id),
        FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );
    """)

    # 13. Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT NOT NULL,
        module TEXT NOT NULL,
        record_id TEXT,
        old_value TEXT,
        new_value TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
