import json
from typing import Optional
from fastapi import Request
from app.database import get_db

def log_audit(
    action: str,
    module: str,
    record_id: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    user: Optional[dict] = None,
    request: Optional[Request] = None
):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        user_id = user["user_id"] if user else None
        username = user["username"] if user else "SYSTEM"
        
        ip_address = None
        user_agent = None
        if request:
            client = getattr(request, "client", None)
            ip_address = client.host if client else None
            user_agent = request.headers.get("user-agent")
            
        old_val_str = json.dumps(old_value, ensure_ascii=False) if old_value else None
        new_val_str = json.dumps(new_value, ensure_ascii=False) if new_value else None
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, username, action, module, record_id, old_value, new_value, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, action, module, str(record_id) if record_id else None, old_val_str, new_val_str, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging audit: {e}")
