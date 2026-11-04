import hashlib
import os
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from app.database import get_db

SECRET_KEY = os.getenv("APP_SECRET_KEY", "shahid-smriti-school-secure-secret-key-2066")

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt$hash"""
    try:
        salt, stored_hash = hashed_password.split('$', 1)
        check_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return hmac.compare_digest(stored_hash, check_hash)
    except Exception:
        return False

# In-memory session store (or token cookies)
SESSIONS: Dict[str, Dict[str, Any]] = {}

def create_session(user_dict: dict) -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "user_id": user_dict["id"],
        "username": user_dict["username"],
        "role": user_dict["role"],
        "full_name_ne": user_dict.get("full_name_ne", ""),
        "full_name_en": user_dict.get("full_name_en", ""),
        "teacher_id": user_dict.get("teacher_id"),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    return token

def get_current_user_from_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or token not in SESSIONS:
        return None
    session = SESSIONS[token]
    if datetime.utcnow() > session["expires_at"]:
        del SESSIONS[token]
        return None
    return session

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("session_token")
    if not token:
        # Check Authorization header Bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    return get_current_user_from_token(token)

def require_auth(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="कृपया पहिले लगइन गर्नुहोस्।"
        )
    return user

def require_role(*allowed_roles):
    def role_checker(request: Request) -> Dict[str, Any]:
        user = require_auth(request)
        if user["role"] not in allowed_roles and "SUPER_ADMIN" not in user["role"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="तपाईंलाई यो कार्य गर्न अनुमति छैन।"
            )
        return user
    return role_checker
