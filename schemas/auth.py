from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    invite_code: str = Field(..., description="Invite code from URL")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InviteResponse(BaseModel):
    id: int
    code: str
    invitee_email: Optional[str]
    is_used: bool
    created_at: Optional[datetime]
    expires_at: datetime
    used_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CreateInviteRequest(BaseModel):
    invitee_email: EmailStr = Field(..., description="Email address to send the invite to")
    inviter_ip: Optional[str] = None
    inviter_user_agent: Optional[str] = None


class ValidateInviteResponse(BaseModel):
    valid: bool
    message: str
