from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)

    # Original fields (kept for backward compatibility, now nullable)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)

    # Kazakh language fields (new)
    title_kz = Column(String(255), nullable=True)
    description_kz = Column(Text, nullable=True)
    content_text_kz = Column(Text, nullable=True)

    # Russian language fields (new)
    title_ru = Column(String(255), nullable=True)
    description_ru = Column(Text, nullable=True)
    content_text_ru = Column(Text, nullable=True)

    # Common fields
    photo_url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True, default=None)
    date = Column(DateTime, default=func.now(), nullable=False)

    # Moderation fields
    moderation_status = Column(String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected'
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)  # 'kz', 'ru', or 'unknown'
    keywords_matched = Column(Text, nullable=True)  # Store matched keywords as JSON or comma-separated
    created_at = Column(DateTime, default=func.now(), nullable=False)
    moderated_at = Column(DateTime, nullable=True)
    moderated_by = Column(Integer, nullable=True)  # Admin ID who moderated

    # Publication scheduling fields (new)
    # status: 'draft' (not ready), 'scheduled' (waiting for publish_at), 'published' (visible to public)
    status = Column(String(20), default='draft', nullable=False, index=True)
    publish_at = Column(DateTime, nullable=True, index=True)  # When to auto-publish (required for 'scheduled' status)
    published_at = Column(DateTime, nullable=True)  # Actual publication timestamp
    is_admin_created = Column(Boolean, default=False, nullable=False)  # True if created by admin (bypasses moderation)

    # Analytics fields
    view_count = Column(Integer, default=0, nullable=False)  # Number of times the news has been viewed
