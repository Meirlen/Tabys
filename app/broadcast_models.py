"""
Telegram Broadcast Models
Database models for broadcast messaging to Telegram bot users
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class BroadcastTargetAudience(str, enum.Enum):
    """Target audience types for broadcasts"""
    ALL_TELEGRAM_USERS = "all_telegram_users"  # Everyone who logged into bot
    ADMINS_ONLY = "admins_only"  # Only admin users
    BY_ROLE = "by_role"  # Filter by specific role
    ACTIVE_SESSIONS = "active_sessions"  # Only users with active sessions


class BroadcastStatus(str, enum.Enum):
    """Broadcast status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryStatus(str, enum.Enum):
    """Individual delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Broadcast(Base):
    """Telegram broadcast message"""
    __tablename__ = "telegram_broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Targeting
    target_audience = Column(
        Enum(BroadcastTargetAudience),
        nullable=False,
        default=BroadcastTargetAudience.ALL_TELEGRAM_USERS
    )
    target_role = Column(String(50), nullable=True)  # Used when target_audience = BY_ROLE

    # Status tracking
    status = Column(
        Enum(BroadcastStatus),
        nullable=False,
        default=BroadcastStatus.DRAFT
    )

    # Statistics
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # Metadata
    created_by = Column(Integer, ForeignKey("adminstrators_shaqyru1.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)  # For scheduled broadcasts
    sent_at = Column(DateTime, nullable=True)  # When sending started
    completed_at = Column(DateTime, nullable=True)  # When sending completed

    # Relationships
    creator = relationship("Admin", foreign_keys=[created_by])
    deliveries = relationship("BroadcastDelivery", back_populates="broadcast", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Broadcast(id={self.id}, title={self.title}, status={self.status})>"


class BroadcastDelivery(Base):
    """Individual broadcast delivery tracking"""
    __tablename__ = "telegram_broadcast_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_id = Column(Integer, ForeignKey("telegram_broadcasts.id"), nullable=False)
    telegram_user_id = Column(String(50), nullable=False, index=True)

    # Delivery status
    status = Column(
        Enum(DeliveryStatus),
        nullable=False,
        default=DeliveryStatus.PENDING
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    broadcast = relationship("Broadcast", back_populates="deliveries")

    def __repr__(self):
        return f"<BroadcastDelivery(id={self.id}, broadcast_id={self.broadcast_id}, status={self.status})>"
