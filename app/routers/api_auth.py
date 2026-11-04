from fastapi import APIRouter, Request, Response, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.auth import verify_password, create_session, get_current_user, require_auth, SESSIONS
from app.utils.audit import log_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def api_login(req: LoginRequest, response: Response, request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, password_hash, full_name_ne, full_name_en, role, teacher_id, status
        FROM users WHERE username = ?
    """, (req.username.strip(),))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="गलत प्रयोगकर्ता नाम वा पासवर्ड।")
        
    if user["status"] not in ("ACTIVE", "सक्रिय"):
        raise HTTPException(status_code=403, detail="तपाईंको खाता निष्क्रिय गरिएको छ।")
        
    user_dict = dict(user)
    token = create_session(user_dict)
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    
    log_audit("LOGIN", "AUTH", record_id=str(user["id"]), user={"user_id": user["id"], "username": user["username"]}, request=request)
    
    return {
        "success": True,
        "message": "सफलतापूर्वक लगइन भयो।",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name_ne": user["full_name_ne"],
            "teacher_id": user["teacher_id"]
        }
    }

@router.post("/logout")
def api_logout(request: Request, response: Response):
    user = get_current_user(request)
    token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        del SESSIONS[token]
        
    response.delete_cookie("session_token")
    if user:
        log_audit("LOGOUT", "AUTH", user=user, request=request)
        
    return {"success": True, "message": "सफलतापूर्वक लगआउट भयो।"}

@router.get("/me")
def api_me(request: Request):
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}
