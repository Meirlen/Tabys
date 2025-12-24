from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PublicationStatus(str, Enum):
    """Publication status for admin-created news (bypasses moderation)"""
    DRAFT = "draft"          # Not ready for publication
    SCHEDULED = "scheduled"  # Waiting for publish_at time
    PUBLISHED = "published"  # Published and visible to public

class NewsBase(BaseModel):
    # Legacy fields (for backward compatibility)
    title: Optional[str] = None
    description: Optional[str] = None
    content_text: Optional[str] = None

    # Kazakh language fields
    title_kz: Optional[str] = None
    description_kz: Optional[str] = None
    content_text_kz: Optional[str] = None

    # Russian language fields
    title_ru: Optional[str] = None
    description_ru: Optional[str] = None
    content_text_ru: Optional[str] = None

    # Common fields
    photo_url: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None

    # Moderation fields
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    language: Optional[str] = None
    keywords_matched: Optional[str] = None

class NewsCreate(NewsBase):
    """Schema for creating news articles by admin"""
    status: Optional[PublicationStatus] = PublicationStatus.DRAFT
    publish_at: Optional[datetime] = None

    @validator('publish_at', always=True)
    def validate_publish_at(cls, v, values):
        """Ensure publish_at is set when status is SCHEDULED"""
        status = values.get('status')
        if status == PublicationStatus.SCHEDULED and v is None:
            raise ValueError('publish_at is required when status is SCHEDULED')
        return v

class NewsUpdate(BaseModel):
    # Legacy fields
    title: Optional[str] = None
    description: Optional[str] = None
    content_text: Optional[str] = None

    # Kazakh language fields
    title_kz: Optional[str] = None
    description_kz: Optional[str] = None
    content_text_kz: Optional[str] = None

    # Russian language fields
    title_ru: Optional[str] = None
    description_ru: Optional[str] = None
    content_text_ru: Optional[str] = None

    # Common fields
    photo_url: Optional[str] = None
    category: Optional[str] = None
    date: Optional[datetime] = None

    # Publication scheduling fields
    status: Optional[PublicationStatus] = None
    publish_at: Optional[datetime] = None

class NewsResponse(NewsBase):
    id: int
    date: datetime
    moderation_status: ModerationStatus
    created_at: datetime
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None

    # Publication scheduling fields
    status: Optional[str] = "draft"
    publish_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    is_admin_created: Optional[bool] = False

    class Config:
        orm_mode = True

class NewsSubmit(BaseModel):
    """Schema for parser to submit news articles"""
    title_kz: Optional[str] = None
    title_ru: Optional[str] = None
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    content_text_kz: Optional[str] = None
    content_text_ru: Optional[str] = None
    source_url: str
    source_name: str
    language: str
    category: Optional[str] = None
    keywords_matched: Optional[str] = None
    photo_url: Optional[str] = None

class NewsModerate(BaseModel):
    """Schema for moderating news"""
    moderation_status: ModerationStatus

class NewsStats(BaseModel):
    """Statistics for news moderation"""
    total: int
    pending: int
    approved: int
    rejected: int

# Publication scheduling schemas

class SlotStatus(BaseModel):
    """Status of a single publication slot"""
    time: str  # e.g., "11:00"
    required: int  # minimum required news
    scheduled: int  # currently scheduled news
    status: str  # "ok" or "warning"

class ScheduleStatusResponse(BaseModel):
    """Response for schedule status endpoint"""
    date: str  # Date being checked (YYYY-MM-DD)
    slots: List[SlotStatus]
    total_required: int
    total_scheduled: int
    overall_status: str  # "ok" or "warning"

class PublicationSlotConfig(BaseModel):
    """Configuration for a publication time slot"""
    time: str  # e.g., "11:00"
    min_news: int  # minimum required news for this slot

class NewsScheduleCreate(BaseModel):
    """Schema for scheduling a news article"""
    news_id: int
    publish_at: datetime

    @validator('publish_at')
    def validate_future_date(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('publish_at must be a future datetime')
        return v
