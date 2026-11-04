from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.auth import require_role
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/promotions", tags=["promotions"])

class ClassPromotionConfig(BaseModel):
    from_class_id: int
    to_class_id: Optional[int] = None
    stream_id: Optional[int] = None
    action: str = "PROMOTE"  # PROMOTE, HOLD, GRADUATE, TRANSFER
    student_ids: Optional[List[int]] = None

class PromotionExecuteRequest(BaseModel):
    current_academic_year_id: int
    new_academic_year_id: int
    promotions: List[ClassPromotionConfig]

@router.get("/preview")
def get_promotion_preview(current_academic_year_id: int, request: Request):
    require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch all classes in sequence
    cursor.execute("SELECT id, class_name_ne, class_numeric, has_stream FROM classes ORDER BY class_numeric ASC")
    classes = [dict(c) for c in cursor.fetchall()]
    
    class_map = {c["class_numeric"]: c for c in classes}
    
    preview_data = []
    total_students_to_promote = 0
    
    for c in classes:
        c_num = c["class_numeric"]
        c_id = c["id"]
        
        # Count active students in current academic year
        cursor.execute("""
            SELECT COUNT(*) FROM students 
            WHERE class_id = ? AND academic_year_id = ? AND status = 'सक्रिय'
        """, (c_id, current_academic_year_id))
        count = cursor.fetchone()[0]
        
        next_class = class_map.get(c_num + 1)
        
        target_action = "PROMOTE"
        to_class_id = next_class["id"] if next_class else None
        to_class_name = next_class["class_name_ne"] if next_class else "स्नातक (Graduated)"
        
        if c_num == 12:
            target_action = "GRADUATE"
            to_class_id = None
            to_class_name = "कक्षा १२ उत्तीर्ण (Graduated)"
        elif c_num == 10:
            target_action = "PROMOTE_TO_11_OR_STREAM"
            to_class_name = "कक्षा ११ (संकाय छनोट सहित)"
            
        preview_data.append({
            "from_class_id": c_id,
            "from_class_name": c["class_name_ne"],
            "from_class_numeric": c_num,
            "total_students": count,
            "to_class_id": to_class_id,
            "to_class_name": to_class_name,
            "default_action": target_action,
            "has_stream": 1 if (next_class and next_class["has_stream"]) else 0
        })
        total_students_to_promote += count
        
    cursor.execute("SELECT id, name_ne, code FROM streams")
    available_streams = [dict(s) for s in cursor.fetchall()]
    
    conn.close()
    return {
        "success": True,
        "classes": preview_data,
        "streams": available_streams,
        "total_students_all_classes": total_students_to_promote
    }

@router.post("/execute")
def execute_promotion(req: PromotionExecuteRequest, request: Request):
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    
    # Validate academic years
    cursor.execute("SELECT id, year_ne FROM academic_years WHERE id = ?", (req.current_academic_year_id,))
    cur_year = cursor.fetchone()
    cursor.execute("SELECT id, year_ne FROM academic_years WHERE id = ?", (req.new_academic_year_id,))
    new_year = cursor.fetchone()
    
    if not cur_year or not new_year:
        conn.close()
        raise HTTPException(status_code=400, detail="अमान्य शैक्षिक वर्ष चयन गरिएको छ।")
        
    promoted_count = 0
    held_count = 0
    graduated_count = 0
    
    for p in req.promotions:
        from_cid = p.from_class_id
        to_cid = p.to_class_id
        action = p.action
        stream_id = p.stream_id
        
        # Get students of from_cid in current year
        if p.student_ids:
            placeholders = ",".join(["?"] * len(p.student_ids))
            cursor.execute(f"""
                SELECT id, roll_no, section_id FROM students
                WHERE id IN ({placeholders}) AND class_id = ? AND academic_year_id = ?
            """, (*p.student_ids, from_cid, req.current_academic_year_id))
        else:
            cursor.execute("""
                SELECT id, roll_no, section_id FROM students
                WHERE class_id = ? AND academic_year_id = ? AND status = 'सक्रिय'
            """, (from_cid, req.current_academic_year_id))
            
        students = cursor.fetchall()
        
        for s in students:
            stu_id = s["id"]
            cur_roll = s["roll_no"]
            cur_sec = s["section_id"]
            
            if action == "GRADUATE":
                cursor.execute("""
                    UPDATE students SET
                        status = 'उत्तीर्ण (Graduated)',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (stu_id,))
                cursor.execute("""
                    INSERT INTO student_class_history (
                        student_id, academic_year_id, class_id, section_id, roll_no, stream_id, promotion_status, remarks
                    ) VALUES (?, ?, ?, ?, ?, ?, 'GRADUATED', 'कक्षा १२ उत्तीर्ण')
                """, (stu_id, req.current_academic_year_id, from_cid, cur_sec, cur_roll, stream_id))
                graduated_count += 1
                
            elif action == "HOLD":
                # Stays in same class but updates to new academic year
                cursor.execute("""
                    UPDATE students SET
                        academic_year_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (req.new_academic_year_id, stu_id))
                cursor.execute("""
                    INSERT INTO student_class_history (
                        student_id, academic_year_id, class_id, section_id, roll_no, stream_id, promotion_status, remarks
                    ) VALUES (?, ?, ?, ?, ?, ?, 'HOLD', 'कक्षा दोहोर्याइएको')
                """, (stu_id, req.new_academic_year_id, from_cid, cur_sec, cur_roll, stream_id))
                held_count += 1
                
            else: # PROMOTE
                if not to_cid:
                    continue
                cursor.execute("""
                    UPDATE students SET
                        class_id = ?,
                        academic_year_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (to_cid, req.new_academic_year_id, stu_id))
                cursor.execute("""
                    INSERT INTO student_class_history (
                        student_id, academic_year_id, class_id, section_id, roll_no, stream_id, promotion_status, remarks
                    ) VALUES (?, ?, ?, ?, ?, ?, 'PROMOTED', 'कक्षा बढुवा')
                """, (stu_id, req.new_academic_year_id, to_cid, cur_sec, cur_roll, stream_id))
                promoted_count += 1
                
    # Update active academic year
    cursor.execute("UPDATE academic_years SET is_active = 0")
    cursor.execute("UPDATE academic_years SET is_active = 1 WHERE id = ?", (req.new_academic_year_id,))
    cursor.execute("UPDATE school_settings SET active_academic_year_id = ?", (req.new_academic_year_id,))
    
    conn.commit()
    conn.close()
    
    msg = f"{cur_year['year_ne']} बाट {new_year['year_ne']} मा {promoted_count} विद्यार्थी बढुवा, {graduated_count} उत्तीर्ण र {held_count} विद्यार्थी होल्ड सफलतापूर्वक गरियो।"
    log_audit("PROMOTION_EXECUTE", "PROMOTION", new_value={
        "promoted": promoted_count,
        "graduated": graduated_count,
        "held": held_count,
        "from_year": cur_year["year_ne"],
        "to_year": new_year["year_ne"]
    }, user=user, request=request)
    
    return {
        "success": True,
        "message": msg,
        "promoted_count": promoted_count,
        "graduated_count": graduated_count,
        "held_count": held_count
    }
