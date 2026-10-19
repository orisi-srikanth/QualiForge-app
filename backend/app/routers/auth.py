from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.app.core.security import create_access_token, DEFAULT_USER

router = APIRouter()

class LoginPayload(BaseModel):
    username: Optional[str] = Field(None, json_schema_extra={"example": "engineer@precisionaero.com"}, description="User email (optional)")
    password: Optional[str] = Field(None, json_schema_extra={"example": "Engineer123!"}, description="User password (optional)")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str

@router.post("/auth/login", tags=["Auth"], summary="Authenticate user persona (No Auth Required)", description="Authentication is disabled. Returns token/profile for any or no credentials.")
def login(payload: Optional[LoginPayload] = None):
    uname = payload.username if payload and payload.username else "engineer@precisionaero.com"
    role_map = {
        "admin@precisionaero.com": "admin",
        "engineer@precisionaero.com": "quality_engineer",
        "operator@precisionaero.com": "operator",
    }
    role = role_map.get(uname, "quality_engineer")
    token = create_access_token({"sub": uname, "role": role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "name": uname.split("@")[0].capitalize() if "@" in uname else "User"
    }

@router.get("/auth/me", tags=["Auth"], summary="Get current user profile (No Auth Required)", description="Returns default authorized engineering profile.")
def get_me():
    return DEFAULT_USER
