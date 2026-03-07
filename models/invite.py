from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.session import Base
from datetime import datetime, timedelta, timezone
import secrets

INVITE_EXPIRY_DAYS = 2


def generate_invite_code() -> str:
    """Generate a secure random invite code."""
    return secrets.token_urlsafe(32)


def default_expiry() -> datetime:
    """Generate default expiry (2 days from now)."""
    return datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)


class Invite(Base):
    """
    Model for storing invite codes for registration.
    """
    __tablename__ = "invites"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True, default=generate_invite_code)
    
    # Email the invite was sent to
    invitee_email = Column(String(255), nullable=True)
    
    # Who created this invite
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id], backref="invites_created")
    
    # Who used this invite (null if unused)
    used_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_by = relationship("User", foreign_keys=[used_by_id], backref="invite_used")
    
    # Inviter metadata
    inviter_ip = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    inviter_user_agent = Column(Text, nullable=True)
    
    # Status
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps - expiry is mandatory (2 days)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, default=default_expiry)
    
    def is_valid(self) -> bool:
        """Check if invite is valid (not used and not expired)."""
        if self.is_used:
            return False
        # Handle both timezone-aware and naive datetimes (SQLite returns naive)
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            return False
        return True
    
    def __repr__(self):
        return f"<Invite(id={self.id}, code='{self.code[:8]}...', is_used={self.is_used})>"
