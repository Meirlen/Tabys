"""
Telegram Bot OTP Authentication Models
Implements secure one-time password system for Telegram bot authentication
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timedelta
import secrets
import string


class TelegramOTP(Base):
    """
    One-time password tokens for Telegram bot authentication

    Flow:
    1. Admin generates OTP via backend API
    2. Admin sends /login <OTP> to Telegram bot
    3. Bot validates OTP and receives JWT
    4. OTP is immediately invalidated after use
    """
    __tablename__ = "telegram_otp_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # OTP token (8-character alphanumeric, cryptographically secure)
    token = Column(String(8), unique=True, nullable=False, index=True)

    # User who generated the OTP
    admin_id = Column(Integer, ForeignKey("adminstrators_shaqyru1.id"), nullable=False, index=True)

    # OTP status
    is_used = Column(Boolean, default=False, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)  # Default: 10 minutes from creation
    used_at = Column(DateTime, nullable=True)

    # Optional metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(512), nullable=True)

    # Relationship
    admin = relationship("Admin", foreign_keys=[admin_id])

    # Indexes for performance
    __table_args__ = (
        Index('idx_token_active', 'token', 'is_used', 'is_revoked'),
        Index('idx_admin_created', 'admin_id', 'created_at'),
    )

    @staticmethod
    def generate_token() -> str:
        """Generate cryptographically secure 8-character OTP token"""
        alphabet = string.ascii_uppercase + string.digits
        # Exclude ambiguous characters: O, 0, I, 1, L
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
        return ''.join(secrets.choice(alphabet) for _ in range(8))

    @staticmethod
    def get_expiry_time(minutes: int = 10) -> datetime:
        """Calculate expiry time (default: 10 minutes from now)"""
        return datetime.utcnow() + timedelta(minutes=minutes)

    def is_valid(self) -> bool:
        """Check if OTP is valid (not used, not revoked, not expired)"""
        if self.is_used or self.is_revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True

    def mark_used(self):
        """Mark OTP as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()

    def revoke(self):
        """Revoke OTP (admin-initiated invalidation)"""
        self.is_revoked = True


class TelegramSession(Base):
    """
    Telegram user sessions mapped to backend admin accounts

    Stores the binding between telegram_user_id and backend admin_id
    Session data (JWT) is stored in Redis for performance
    """
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Telegram user identifier
    telegram_user_id = Column(String(20), unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    telegram_first_name = Column(String(255), nullable=True)
    telegram_last_name = Column(String(255), nullable=True)

    # Backend admin account
    admin_id = Column(Integer, ForeignKey("adminstrators_shaqyru1.id"), nullable=False, index=True)

    # Session status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_activity_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime, nullable=True)  # Optional hard expiry

    # Security metadata
    first_login_ip = Column(String(45), nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    # Relationship
    admin = relationship("Admin", foreign_keys=[admin_id])

    # Indexes
    __table_args__ = (
        Index('idx_telegram_active', 'telegram_user_id', 'is_active'),
        Index('idx_admin_sessions', 'admin_id', 'is_active'),
    )

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()

    def deactivate(self):
        """Deactivate session (logout)"""
        self.is_active = False
