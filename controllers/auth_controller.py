from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from typing import List
from sqlalchemy.orm import Session
from database.session import get_db
from common.auth_service import AuthService
from middleware.auth import get_current_user
from models.user import User
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    InviteResponse,
    CreateInviteRequest,
    ValidateInviteResponse,
)
from schemas.common import MessageResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Public Endpoints (No Auth Required)
# =============================================================================

@router.get("/validate-invite/{code}", response_model=ValidateInviteResponse)
def validate_invite(code: str, db: Session = Depends(get_db)):
    """
    Validate an invite code before showing the signup form.
    Call this when the signup page loads with the invite code.
    """
    service = AuthService(db)
    is_valid, message = service.validate_invite_code(code)
    return ValidateInviteResponse(valid=is_valid, message=message)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with an invite code."""
    service = AuthService(db)
    success, message, user = service.register(
        email=request.email,
        password=request.password,
        invite_code=request.invite_code,
        name=request.name,
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password to get access and refresh tokens."""
    service = AuthService(db)
    success, message, tokens = service.login(
        email=request.email,
        password=request.password,
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """Get a new access token using a refresh token."""
    service = AuthService(db)
    success, message, tokens = service.refresh_tokens(request.refresh_token)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    
    return TokenResponse(**tokens)


# =============================================================================
# Protected Endpoints (Auth Required)
# =============================================================================

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    request: CreateInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new invite code and send it to the invitee's email."""
    service = AuthService(db)
    invite = service.create_invite(
        created_by_id=current_user.id,
        invitee_email=request.invitee_email,
        inviter_name=current_user.name,
        inviter_ip=request.inviter_ip,
        inviter_user_agent=request.inviter_user_agent,
    )
    return invite


@router.get("/invites", response_model=List[InviteResponse])
def list_my_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all invites created by the current user."""
    service = AuthService(db)
    invites = service.get_invites_by_user(current_user.id)
    return invites
