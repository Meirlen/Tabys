from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Bilingual titles
    title_kz = Column(String(500), nullable=False)
    title_ru = Column(String(500), nullable=False)

    # Bilingual messages
    message_kz = Column(Text, nullable=True)
    message_ru = Column(Text, nullable=True)

    # Notification metadata
    notification_type = Column(String(100), nullable=False)  # e.g. "application_approved"
    entity_type = Column(String(100), nullable=True)  # e.g. "project_application"
    entity_id = Column(Integer, nullable=True)

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)

    # Admin comment (if applicable)
    admin_comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index('ix_user_notifications_user_unread', 'user_id', 'is_read'),
    )
