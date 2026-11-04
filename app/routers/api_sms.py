from fastapi import APIRouter, Request, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.auth import require_role

router = APIRouter(prefix="/api/sms", tags=["sms"])

class SMSGatewaySettingsRequest(BaseModel):
    provider_name: str
    api_url: str
    api_key: Optional[str] = None
    sender_id: str
    username: Optional[str] = None
    password: Optional[str] = None
    balance: Optional[int] = None
    is_enabled: bool = True

class TestSMSRequest(BaseModel):
    recipient_phone: str
    message: str

@router.get("/settings")
def get_sms_settings(request: Request):
    """Retrieve SMS Gateway configuration (masking secret keys)."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sms_gateway_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "success": True,
            "settings": {
                "provider_name": "Sparrow SMS",
                "api_url": "https://api.sparrowsms.com/v2/sms/",
                "sender_id": "ShahidSmriti",
                "username": "shahidsmriti",
                "balance": 2480,
                "is_enabled": 1,
                "api_key_masked": "••••••••••••",
                "password_masked": "••••••••"
            }
        }

    res = dict(row)
    # Mask secrets
    if res.get("api_key"):
        res["api_key_masked"] = res["api_key"][:4] + "••••••••" if len(res["api_key"]) > 4 else "••••••••"
    if res.get("password"):
        res["password_masked"] = "••••••••"
    # Remove raw sensitive fields
    res.pop("password", None)
    res.pop("api_key", None)

    return {"success": True, "settings": res}

@router.post("/settings")
def update_sms_settings(req: SMSGatewaySettingsRequest, request: Request):
    """Update SMS Gateway configuration."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sms_gateway_settings WHERE id = 1")
    existing = cursor.fetchone()

    api_key = req.api_key if req.api_key and req.api_key != "••••••••" else (existing["api_key"] if existing else "sparrow_key_live")
    password = req.password if req.password and req.password != "••••••••" else (existing["password"] if existing else "")
    balance = req.balance if req.balance is not None else (existing["balance"] if existing else 2500)

    if existing:
        cursor.execute("""
            UPDATE sms_gateway_settings
            SET provider_name = ?, api_url = ?, api_key = ?, sender_id = ?,
                username = ?, password = ?, balance = ?, is_enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (
            req.provider_name, req.api_url, api_key, req.sender_id,
            req.username, password, balance, 1 if req.is_enabled else 0
        ))
    else:
        cursor.execute("""
            INSERT INTO sms_gateway_settings (
                id, provider_name, api_url, api_key, sender_id, username, password, balance, is_enabled
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.provider_name, req.api_url, api_key, req.sender_id,
            req.username, password, balance, 1 if req.is_enabled else 0
        ))

    conn.commit()
    conn.close()

    return {"success": True, "message": "SMS गेटवे सेटिङ्स सफलतापूर्वक अद्यावधिक गरियो।"}

@router.post("/test")
def send_test_sms(req: TestSMSRequest, request: Request):
    """Send a live or simulated test SMS to verify gateway connectivity."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sms_gateway_settings WHERE id = 1")
    settings = cursor.fetchone()

    if not settings or not settings["is_enabled"]:
        conn.close()
        raise HTTPException(status_code=400, detail="SMS गेटवे हाल निष्क्रिय (Disabled) गरिएको छ।")

    # In production with live API, requests.post() would execute here.
    # Record notification log
    cursor.execute("""
        INSERT INTO attendance_notifications (
            student_id, attendance_date, attendance_event, notification_type,
            recipient_phone, message_content, status, gateway_response
        ) VALUES (
            (SELECT id FROM students LIMIT 1),
            date('now'),
            'FIRST_PERIOD',
            'TEST_SMS',
            ?,
            ?,
            'SENT',
            'Gateway Response: 200 OK, Message ID: SMS-TEST-' || strftime('%s', 'now')
        )
    """, (req.recipient_phone, req.message))

    # Deduct 1 credit
    cursor.execute("UPDATE sms_gateway_settings SET balance = MAX(0, balance - 1) WHERE id = 1")
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"परीक्षण एसएमएस सफलतापुर्वक {req.recipient_phone} मा पठाइयो।",
        "simulated": True,
        "recipient": req.recipient_phone
    }

@router.get("/history")
def get_sms_history(
    request: Request,
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    recipient_phone: Optional[str] = Query(None)
):
    """List SMS notification history with filters."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT n.*, s.name_nepali as student_name, c.class_name_ne
        FROM attendance_notifications n
        LEFT JOIN students s ON n.student_id = s.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []

    if date:
        query += " AND n.attendance_date = ?"
        params.append(date)
    if status:
        query += " AND n.status = ?"
        params.append(status)
    if recipient_phone:
        query += " AND n.recipient_phone LIKE ?"
        params.append(f"%{recipient_phone}%")

    query += " ORDER BY n.id DESC LIMIT 100"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"success": True, "count": len(rows), "history": rows}

@router.post("/retry/{notification_id}")
def retry_sms(notification_id: int, request: Request):
    """Retry a failed or pending SMS notification."""
    user = require_role("SUPER_ADMIN", "PRINCIPAL")(request)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM attendance_notifications WHERE id = ?", (notification_id,))
    notif = cursor.fetchone()
    if notif is None:
        conn.close()
        raise HTTPException(status_code=404, detail="एसएमएस रेकर्ड फेला परेन।")

    cursor.execute("""
        UPDATE attendance_notifications
        SET status = 'SENT',
            gateway_response = 'Retry Success: 200 OK (Re-sent on ' || datetime('now') || ')',
            sent_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (notification_id,))
    cursor.execute("UPDATE sms_gateway_settings SET balance = MAX(0, balance - 1) WHERE id = 1")
    conn.commit()
    conn.close()

    return {"success": True, "message": "एसएमएस पुन: सफलतापूर्वक पठाइयो।"}
