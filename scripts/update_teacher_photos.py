import sqlite3
import os

db_files = ['school.db', 'api/school.db']

for db_file in db_files:
    if not os.path.exists(db_file):
        continue
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("""
        UPDATE teachers 
        SET photo = '/static/images/teachers/teacher_103_rita_phuyal.jpg' 
        WHERE id = 103 OR employee_id = 'TCH-83001'
    """)
    c.execute("""
        UPDATE teachers 
        SET photo = '/static/images/teachers/teacher_104_ramesh_khadka.jpg' 
        WHERE id = 104 OR employee_id = 'TCH-83002'
    """)
    c.execute("""
        UPDATE teachers 
        SET photo = '/static/images/teachers/teacher_105_chewan_paudel.jpg' 
        WHERE id = 105 OR employee_id = 'TCH-83003'
    """)
    c.execute("""
        UPDATE school_leadership 
        SET photo = '/static/images/teachers/teacher_103_rita_phuyal.jpg' 
        WHERE role_type = 'PRINCIPAL'
    """)
    c.execute("""
        UPDATE school_leadership 
        SET photo = '/static/images/teachers/teacher_104_ramesh_khadka.jpg' 
        WHERE role_type IN ('VICE_PRINCIPAL', 'ASSISTANT_PRINCIPAL')
    """)
    conn.commit()
    conn.close()
    print(f"Successfully updated photos in {db_file}")
