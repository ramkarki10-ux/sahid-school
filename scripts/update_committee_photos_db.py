import sqlite3
import os

def update_db(db_path):
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (not found)")
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Update SMC members
    smc_photos = {
        28: "/static/images/committees/smc_28.svg",
        29: "/static/images/smc_ram_kumari.jpg",
        30: "/static/images/committees/smc_30.svg",
        31: "/static/images/committees/smc_31.svg",
        32: "/static/images/committees/smc_32.svg",
        33: "/static/images/committees/smc_33.svg",
        34: "/static/images/committees/smc_34.svg",
        35: "/static/images/committees/smc_35.svg",
        36: "/static/images/committees/smc_36.svg",
        37: "/static/images/teachers/teacher_103_rita_phuyal.jpg"
    }
    for mid, photo in smc_photos.items():
        c.execute("UPDATE school_management_committee SET photo = ? WHERE id = ?", (photo, mid))
        
    # Also fallback by order_index if IDs differ
    smc_by_order = {
        1: "/static/images/committees/smc_28.svg",
        2: "/static/images/smc_ram_kumari.jpg",
        3: "/static/images/committees/smc_30.svg",
        4: "/static/images/committees/smc_31.svg",
        5: "/static/images/committees/smc_32.svg",
        6: "/static/images/committees/smc_33.svg",
        7: "/static/images/committees/smc_34.svg",
        8: "/static/images/committees/smc_35.svg",
        9: "/static/images/committees/smc_36.svg",
        10: "/static/images/teachers/teacher_103_rita_phuyal.jpg"
    }
    for ord_idx, photo in smc_by_order.items():
        c.execute("UPDATE school_management_committee SET photo = ? WHERE order_index = ? AND (photo IS NULL OR photo = '')", (photo, ord_idx))
        
    # 2. Update Trustee members
    trustee_photos = {
        1: "/static/images/committees/trustee_1.svg",
        2: "/static/images/committees/trustee_2.svg",
        3: "/static/images/committees/trustee_3.svg",
        4: "/static/images/smc_ram_kumari.jpg",
        5: "/static/images/committees/trustee_5.svg",
        6: "/static/images/committees/trustee_6.svg",
        7: "/static/images/committees/trustee_7.svg",
        8: "/static/images/committees/trustee_8.svg",
        9: "/static/images/committees/trustee_9.svg"
    }
    for mid, photo in trustee_photos.items():
        c.execute("UPDATE trustee_committee SET photo = ? WHERE id = ?", (photo, mid))
        c.execute("UPDATE trustee_committee SET photo = ? WHERE order_index = ? AND (photo IS NULL OR photo = '')", (photo, mid))
        
    conn.commit()
    conn.close()
    print(f"Updated photos in {db_path}")

if __name__ == "__main__":
    update_db("school.db")
    update_db("api/school.db")

