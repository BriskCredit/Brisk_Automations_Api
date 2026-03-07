from sqlalchemy.orm import Session
from typing import Optional, Tuple
from datetime import datetime, timezone
import os
from models.user import User
from models.invite import Invite, generate_invite_code
from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, create_refresh_token, verify_refresh_token
from common.email_service import EmailService
from utils.logger import get_logger

logger = get_logger("app.common.auth")


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_invite_by_code(self, code: str) -> Optional[Invite]:
        """Get invite by code."""
        return self.db.query(Invite).filter(Invite.code == code).first()
    
    def validate_invite_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate an invite code before showing signup form.
        Returns: (is_valid, message)
        """
        invite = self.get_invite_by_code(code)
        
        if not invite:
            return False, "Invalid invite code"
        
        if invite.is_used:
            return False, "Invite code has already been used"
        
        if not invite.is_valid():
            return False, "Invite code has expired"
        
        return True, "Invite code is valid"
    
    def create_invite(
        self, 
        created_by_id: int,
        invitee_email: str,
        inviter_name: Optional[str] = None,
        inviter_ip: Optional[str] = None,
        inviter_user_agent: Optional[str] = None
    ) -> Invite:
        """Create a new invite code and send invite email."""
        invite = Invite(
            code=generate_invite_code(),
            created_by_id=created_by_id,
            invitee_email=invitee_email,
            inviter_ip=inviter_ip,
            inviter_user_agent=inviter_user_agent,
        )
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)
        
        # Get frontend URL from environment
        frontend_base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Send invite email
        self._send_invite_email(
            invitee_email=invitee_email,
            invite_code=invite.code,
            frontend_base_url=frontend_base_url,
            inviter_name=inviter_name,
            expires_at=invite.expires_at,
        )
        
        return invite
    
    def _send_invite_email(
        self,
        invitee_email: str,
        invite_code: str,
        frontend_base_url: str,
        inviter_name: Optional[str],
        expires_at: datetime,
    ) -> None:
        """Send invite email to the invitee."""
        try:
            email_service = EmailService()
            
            # Build invite URL
            base_url = frontend_base_url.rstrip('/')
            invite_url = f"{base_url}/signup?invite={invite_code}"
            
            inviter_display = inviter_name or "A team member"
            expires_str = expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
            
            subject = "You've been invited to join Brisk"
            
            body = f"""Hi,

{inviter_display} has invited you to join Brisk.

Click the link below to create your account:
{invite_url}

This invite expires on {expires_str}.

If you didn't expect this invitation, you can safely ignore this email.

Best regards,
The Brisk Team"""
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">You've been invited!</h2>
        <p>{inviter_display} has invited you to join Brisk.</p>
        <p style="margin: 30px 0;">
            <a href="{invite_url}" 
               style="background-color: #2563eb; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; display: inline-block;">
                Accept Invitation
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            Or copy this link: <a href="{invite_url}">{invite_url}</a>
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 30px;">
            This invite expires on {expires_str}.<br>
            If you didn't expect this invitation, you can safely ignore this email.
        </p>
    </div>
</body>
</html>
"""
            
            email_service.send_email(
                to=[invitee_email],
                subject=subject,
                body=body,
                html_body=html_body,
            )
            logger.info(f"Invite email sent to {invitee_email}")
            
        except Exception as e:
            logger.error(f"Failed to send invite email to {invitee_email}: {e}")
            # Don't fail the invite creation if email fails
            # The invite is still valid and the code can be shared manually
    
    def register(
        self, 
        email: str, 
        password: str, 
        invite_code: str,
        name: str
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user with invite code.
        Returns: (success, message, user)
        """
        # Validate invite code
        invite = self.get_invite_by_code(invite_code)
        if not invite:
            return False, "Invalid invite code", None
        
        if not invite.is_valid():
            if invite.is_used:
                return False, "Invite code has already been used", None
            return False, "Invite code has expired", None
        
        # Validate email matches invite
        if invite.invitee_email and invite.invitee_email.lower() != email.lower():
            return False, "This invite was sent to a different email address", None
        
        # Check if user exists
        if self.get_user_by_email(email):
            return False, "Email already registered", None
        
        # Create user
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name=name,
        )
        self.db.add(user)
        self.db.flush()  # Get user ID
        
        # Mark invite as used
        invite.is_used = True
        invite.used_by_id = user.id
        invite.used_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(user)
        
        return True, "User registered successfully", user
    
    def login(self, email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Authenticate user and return tokens.
        Returns: (success, message, tokens_dict)
        """
        user = self.get_user_by_email(email)
        
        if not user:
            return False, "Invalid email or password", None
        
        if not user.is_active:
            return False, "Account is disabled", None
        
        if not verify_password(password, user.hashed_password):
            return False, "Invalid email or password", None
        
        # Generate tokens
        tokens = {
            "access_token": create_access_token(user.id, user.email),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
        }
        
        return True, "Login successful", tokens
    
    def refresh_tokens(self, refresh_token: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Generate new access token using refresh token.
        Returns: (success, message, tokens_dict)
        """
        payload = verify_refresh_token(refresh_token)
        
        if not payload:
            return False, "Invalid or expired refresh token", None
        
        user_id = int(payload.get("sub"))
        user = self.get_user_by_id(user_id)
        
        if not user:
            return False, "User not found", None
        
        if not user.is_active:
            return False, "Account is disabled", None
        
        # Generate new tokens
        tokens = {
            "access_token": create_access_token(user.id, user.email),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
        }
        
        return True, "Tokens refreshed", tokens
    
    def get_invites_by_user(self, user_id: int) -> list[Invite]:
        """Get all invites created by a user."""
        return self.db.query(Invite).filter(Invite.created_by_id == user_id).all()
