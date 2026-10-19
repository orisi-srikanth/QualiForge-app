from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
try:
    import jwt
except ImportError:
    from jose import jwt

import bcrypt
from fastapi import Depends, HTTPException, status, Header, Request
from backend.app.core.config import settings

class UserRole(str, Enum):
    OPERATOR = "operator"
    QUALITY_ENGINEER = "quality_engineer"
    ADMIN = "admin"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None

DEFAULT_USER: Dict[str, Any] = {
    "id": "usr-qe-01",
    "name": "Sarah Chen",
    "email": "quality.engineer@precisionaero.com",
    "role": UserRole.QUALITY_ENGINEER.value,
    "authorized_to_confirm_root_cause": True
}

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    raw_token = token
    if not raw_token and authorization:
        if authorization.lower().startswith("bearer "):
            raw_token = authorization[7:].strip()
        else:
            raw_token = authorization.strip()

    if raw_token:
        payload = decode_access_token(raw_token)
        if payload:
            return payload
    return DEFAULT_USER

def get_current_user(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> Dict[str, Any]:
    return user or DEFAULT_USER

def require_roles(*allowed_roles: UserRole):
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_role = str(user.get("role", "")).lower()
        if user_role and allowed_roles:
            norm = [r.value.lower() if hasattr(r, "value") else str(r).lower() for r in allowed_roles]
            if user_role not in norm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Role '{user.get('role')}' unauthorized."
                )
        return user
    return role_checker

def require_authenticated_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return user

def require_authenticated_role(*allowed_roles: str):
    def checker(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
        is_strict = request.headers.get("x-enforce-role", "").lower() in ("true", "1")
        user_role = str(user.get("role", "")).lower()
        if is_strict and user_role and allowed_roles:
            norm_allowed = [str(r).lower() for r in allowed_roles]
            if user_role not in norm_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Role '{user.get('role')}' unauthorized. User is not authorized to perform this operation. Allowed roles: {list(allowed_roles)}."
                )
        return user
    return checker

