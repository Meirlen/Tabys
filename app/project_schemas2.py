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
    description: str = Field(..., min_length=1)
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
    description: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    status: Optional[ProjectStatus] = None


class VotingParticipantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
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


# === МУЛЬТИЯЗЫЧНЫЕ СХЕМЫ ===

class ProjectCreateMulti(BaseModel):
    title_kz: str = Field(..., min_length=1, max_length=255, description="Заголовок на казахском")
    title_ru: str = Field(..., min_length=1, max_length=255, description="Заголовок на русском")
    description_kz: str = Field(..., min_length=1, description="Описание на казахском")
    description_ru: str = Field(..., min_length=1, description="Описание на русском")
    author: str = Field(..., min_length=1, max_length=255)
    project_type: str  # "voting" или "application"
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

    @validator('project_type')
    def validate_project_type(cls, v):
        if v not in ['voting', 'application']:
            raise ValueError('project_type должен быть "voting" или "application"')
        return v


class ProjectUpdateMulti(BaseModel):
    title_kz: Optional[str] = Field(None, min_length=1, max_length=255)
    title_ru: Optional[str] = Field(None, min_length=1, max_length=255)
    description_kz: Optional[str] = Field(None, min_length=1)
    description_ru: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    status: Optional[ProjectStatus] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and 'start_date' in values and values['start_date'] and v <= values['start_date']:
            raise ValueError('Дата завершения должна быть позже даты начала')
        return v


class VotingParticipantCreateMulti(BaseModel):
    name_kz: str = Field(..., min_length=1, max_length=255, description="Имя на казахском")
    name_ru: str = Field(..., min_length=1, max_length=255, description="Имя на русском")
    description_kz: Optional[str] = Field(None, description="Описание на казахском")
    description_ru: Optional[str] = Field(None, description="Описание на русском")
    video_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None


class VotingParticipantUpdateMulti(BaseModel):
    name_kz: Optional[str] = Field(None, min_length=1, max_length=255)
    name_ru: Optional[str] = Field(None, min_length=1, max_length=255)
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    video_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None


# === ОРИГИНАЛЬНЫЕ СХЕМЫ (для обратной совместимости) ===

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=255)
    project_type: str  # ИЗМЕНЯЕМ тип на str
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
    description: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    status: Optional[ProjectStatus] = None


class VotingParticipantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
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


# === ОТВЕТЫ API ===

class ProjectResponseMulti(BaseModel):
    id: int
    title_kz: str
    title_ru: str
    description_kz: str
    description_ru: str
    author: str
    project_type: str
    status: str
    start_date: datetime
    end_date: datetime
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VotingParticipantResponseMulti(BaseModel):
    id: int
    name_kz: str
    name_ru: str
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    votes_count: int
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# === УТИЛИТАРНЫЕ ФУНКЦИИ ===

def get_localized_field(obj, field_name: str, language: str = "ru"):
    """
    Получает локализованное поле объекта

    Args:
        obj: Объект с мультиязычными полями
        field_name: Базовое имя поля (например, 'title', 'description')
        language: Язык ('kz' или 'ru')

    Returns:
        Локализованное значение поля
    """
    lang_suffix = "_kz" if language == "kz" else "_ru"
    field_with_lang = field_name + lang_suffix

    if hasattr(obj, field_with_lang):
        return getattr(obj, field_with_lang)
    return None


def format_project_response(project, language: str = "ru"):
    """
    Форматирует ответ проекта для указанного языка

    Args:
        project: Объект проекта из базы данных
        language: Язык ответа ('kz' или 'ru')

    Returns:
        Словарь с локализованными данными
    """
    return {
        "id": project.id,
        "title": get_localized_field(project, "title", language),
        "description": get_localized_field(project, "description", language),
        "author": project.author,
        "project_type": project.project_type,
        "status": project.status,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "photo_url": project.photo_url,
        "video_url": project.video_url,
        "created_at": project.created_at
    }


def format_participant_response(participant, language: str = "ru"):
    """
    Форматирует ответ участника для указанного языка

    Args:
        participant: Объект участника из базы данных
        language: Язык ответа ('kz' или 'ru')

    Returns:
        Словарь с локализованными данными
    """
    return {
        "id": participant.id,
        "name": get_localized_field(participant, "name", language),
        "description": get_localized_field(participant, "description", language),
        "photo_url": participant.photo_url,
        "video_url": participant.video_url,
        "votes_count": participant.votes_count,
        "instagram_url": participant.instagram_url,
        "facebook_url": participant.facebook_url,
        "linkedin_url": participant.linkedin_url,
        "twitter_url": participant.twitter_url,
        "created_at": participant.created_at
    }


# === ВАЛИДАЦИЯ ЯЗЫКОВ ===

def validate_language(lang: str) -> str:
    """
    Валидирует параметр языка

    Args:
        lang: Код языка

    Returns:
        Валидный код языка

    Raises:
        ValueError: Если язык не поддерживается
    """
    if lang not in ["kz", "ru"]:
        raise ValueError("Поддерживаются только языки: kz, ru")
    return lang