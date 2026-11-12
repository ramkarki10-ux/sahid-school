import hashlib
import os
import hmac
import secrets
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from app.database import get_db

SECRET_KEY = os.getenv("APP_SECRET_KEY", "shahid-smriti-school-secure-secret-key-2066")
ADMIN_ROLES = {"SUPER_ADMIN", "ADMIN", "PRINCIPAL"}

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

# In-memory session cache (backed by tamper-proof HMAC signed tokens)
SESSIONS: Dict[str, Dict[str, Any]] = {}

def create_session(user_dict: dict) -> str:
    """Create a tamper-proof, stateless signed session token valid for 30 days."""
    expires_at = datetime.utcnow() + timedelta(days=30)
    session_data = {
        "user_id": user_dict["id"],
        "id": user_dict["id"],
        "username": user_dict["username"],
        "role": user_dict["role"],
        "full_name_ne": user_dict.get("full_name_ne", ""),
        "full_name_en": user_dict.get("full_name_en", ""),
        "teacher_id": user_dict.get("teacher_id"),
        "exp": int(expires_at.timestamp())
    }
    raw_json = json.dumps(session_data, separators=(',', ':'), ensure_ascii=False)
    payload_b64 = base64.urlsafe_b64encode(raw_json.encode('utf-8')).decode('ascii').rstrip('=')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{sig}"
    
    # Store in in-memory cache as well
    session_copy = dict(session_data)
    session_copy["created_at"] = datetime.utcnow()
    session_copy["expires_at"] = expires_at
    SESSIONS[token] = session_copy
    return token

def get_current_user_from_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieve and verify session from token (both in-memory and cryptographic signature)."""
    if not token:
        return None
        
    # Check in-memory first for rapid response
    if token in SESSIONS:
        session = SESSIONS[token]
        if datetime.utcnow() <= session.get("expires_at", datetime.max):
            return session
        else:
            del SESSIONS[token]
            return None
            
    # Stateless verification (survives Vercel serverless cold starts & multiple lambdas)
    try:
        if "." not in token:
            return None
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
            
        padded_b64 = payload_b64 + '=' * (-len(payload_b64) % 4)
        raw_json = base64.urlsafe_b64decode(padded_b64.encode('ascii')).decode('utf-8')
        session_data = json.loads(raw_json)
        
        # Check expiration
        exp = session_data.get("exp", 0)
        if datetime.utcnow().timestamp() > exp:
            return None
            
        session_data["id"] = session_data.get("user_id")
        session_data["expires_at"] = datetime.fromtimestamp(exp)
        
        # Cache for subsequent calls
        SESSIONS[token] = session_data
        return session_data
    except Exception:
        return None

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("session_token") or request.cookies.get("auth_token")
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
    """Enforce role permissions. SUPER_ADMIN, ADMIN, and PRINCIPAL have universal admin control."""
    def role_checker(request: Request) -> Dict[str, Any]:
        user = require_auth(request)
        user_role = user.get("role", "")
        # Super Admin, Admin, and Principal have universal access to all school administration features
        if user_role in ADMIN_ROLES:
            return user
        if user_role in allowed_roles or "SUPER_ADMIN" in user_role:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="तपाईंलाई यो कार्य गर्न अनुमति छैन।"
        )
    return role_checker
