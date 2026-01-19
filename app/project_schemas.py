from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
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
    status: Optional[ProjectStatus] = None
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


class ProjectResponse(BaseModel):
    id: int
    title: str
    title_ru: str
    description: str
    description_ru: str
    author: str
    project_type: str
    status: str
    start_date: datetime
    end_date: datetime
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    created_at: datetime
    admin_id: Optional[int] = None

    # Moderation fields
    moderation_status: str = "approved"
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None
    moderation_comment: Optional[str] = None
    is_admin_created: bool = False

    class Config:
        from_attributes = True


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


# ===== Form Builder Schemas =====

class FormFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    DATE = "date"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    RATING = "rating"
    CITY = "city"
    DISTRICT = "district"
    ADDRESS = "address"


class FormFieldValidation(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


class FormFieldFileConfig(BaseModel):
    accept: str = ".pdf,.doc,.docx,.jpg,.jpeg,.png"
    max_size_mb: int = 10


class FormField(BaseModel):
    id: str  # UUID for field identification
    type: FormFieldType
    label_kz: str
    label_ru: str
    placeholder_kz: Optional[str] = None
    placeholder_ru: Optional[str] = None
    required: bool = False
    order: int = 0
    options: Optional[List[str]] = None  # For dropdown/radio/checkbox
    validation: Optional[FormFieldValidation] = None
    file_config: Optional[FormFieldFileConfig] = None
    depends_on: Optional[str] = None  # For district field to depend on city
    cities_districts: Optional[dict] = None  # For district field - Kazakhstan cities and districts mapping


class FormTemplateCreate(BaseModel):
    project_id: int
    title_kz: str = Field(..., min_length=1, max_length=255)
    title_ru: str = Field(..., min_length=1, max_length=255)
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    fields: List[FormField] = []


class FormTemplateUpdate(BaseModel):
    title_kz: Optional[str] = Field(None, min_length=1, max_length=255)
    title_ru: Optional[str] = Field(None, min_length=1, max_length=255)
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    fields: Optional[List[FormField]] = None
    is_active: Optional[bool] = None


class FormTemplateResponse(BaseModel):
    id: int
    project_id: int
    title_kz: str
    title_ru: str
    description_kz: Optional[str]
    description_ru: Optional[str]
    fields: List[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FormSubmissionCreate(BaseModel):
    # project_id is taken from URL path parameter, not body
    phone_number: str = Field(..., pattern=r'^(\+7|8)\d{10}$')
    email: Optional[str] = None
    applicant_name: Optional[str] = None
    responses: Dict[str, Any]  # field_id: response_value


class FormSubmissionUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(pending|approved|rejected)$')
    admin_comment: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    id: int
    project_id: int
    form_template_id: int
    user_id: Optional[int]
    phone_number: str
    email: Optional[str]
    applicant_name: Optional[str]
    responses: Dict[str, Any]
    status: str
    admin_comment: Optional[str]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    submitted_at: datetime

    class Config:
        from_attributes = True


class FormSubmissionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    submissions: List[FormSubmissionResponse]


class FormAnalyticsResponse(BaseModel):
    total_submissions: int
    pending_count: int
    approved_count: int
    rejected_count: int
    submissions_over_time: List[Dict[str, Any]]  # [{"date": "2026-01-15", "count": 5}, ...]
    field_statistics: Dict[str, Any]  # field_id: {stats based on field type}
    avg_submissions_per_day: float