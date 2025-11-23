from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NewsBase(BaseModel):
    title: str
    description: str
    photo_url: Optional[str] = None
    content_text: str
    date: Optional[datetime] = None

class NewsCreate(NewsBase):
    pass

class NewsUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    content_text: Optional[str] = None
    date: Optional[datetime] = None

class NewsResponse(NewsBase):
    id: int
    date: datetime

    class Config:
        orm_mode = True
