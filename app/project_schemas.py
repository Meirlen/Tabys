from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectType(str, Enum):
    VOTING = "voting"
    APPLICATION = "application"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    title_ru: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    description_ru: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=255)
    project_type: str # ИЗМЕНЯЕМ тип на str
    start_date: datetime
    end_date: datetime
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    creator_id: Optional[int] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('Дата завершения должна быть позже даты начала')
        return v


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    title_ru: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    description_ru: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    status: Optional[ProjectStatus] = None


class VotingParticipantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    description_ru: Optional[str] = None
    video_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None


class ProjectApplicationCreate(BaseModel):
    project_id: int
    phone_number: str = Field(..., pattern=r'^(\+7|8)\d{10}$')
    description: str = Field(..., min_length=10)
    applicant_name: Optional[str] = None
    email: Optional[str] = None