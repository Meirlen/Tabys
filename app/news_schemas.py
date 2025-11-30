from pydantic import BaseModel
from datetime import datetime
from typing import Optional

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

    class Config:
        orm_mode = True
