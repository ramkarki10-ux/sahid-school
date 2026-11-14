import sqlite3
import os

def update_teacher_photos(db_path):
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    teacher_photos = {
        103: "/static/images/teachers/teacher_103_rita_phuyal.jpg",
        104: "/static/images/teachers/teacher_104_ramesh_khadka.jpg",
        105: "/static/images/teachers/teacher_105_chewan_paudel.jpg",
        106: "/static/images/teachers/teacher_106_yubaraj_neupane.jpg",
        107: "/static/images/teachers/teacher_107.svg",
        108: "/static/images/teachers/teacher_108.svg",
        109: "/static/images/teachers/teacher_109.svg",
        110: "/static/images/teachers/teacher_110.svg",
        111: "/static/images/teachers/teacher_111.svg",
        112: "/static/images/teachers/teacher_112.svg",
        113: "/static/images/teachers/teacher_113.svg",
        114: "/static/images/teachers/teacher_114.svg",
        115: "/static/images/teachers/teacher_115.svg",
        116: "/static/images/teachers/teacher_116.svg",
        117: "/static/images/teachers/teacher_117.svg",
        118: "/static/images/teachers/teacher_118.svg"
    }
    
    for tid, photo in teacher_photos.items():
        c.execute("UPDATE teachers SET photo = ? WHERE id = ? AND (photo IS NULL OR photo = '')", (photo, tid))
        # Ensure 103 to 106 have their canonical jpgs
        if tid in [103, 104, 105, 106]:
            c.execute("UPDATE teachers SET photo = ? WHERE id = ?", (photo, tid))
            
    conn.commit()
    conn.close()
    print(f"Updated teacher photos in {db_path}")

if __name__ == '__main__':
    update_teacher_photos("school.db")
    update_teacher_photos("api/school.db")
