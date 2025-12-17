from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

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
    pass

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

class NewsResponse(NewsBase):
    id: int
    date: datetime
    moderation_status: ModerationStatus
    created_at: datetime
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None

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
