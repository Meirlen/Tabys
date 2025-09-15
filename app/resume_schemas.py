from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# Enums для схем
class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"


class EducationLevelEnum(str, Enum):
    SECONDARY = "secondary"
    VOCATIONAL = "vocational"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


# Схемы для справочников
class ProfessionBase(BaseModel):
    name_ru: str
    name_kz: str
    category: Optional[str] = None


class ProfessionCreate(ProfessionBase):
    pass


class ProfessionResponse(ProfessionBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RegionBase(BaseModel):
    name_ru: str
    name_kz: str


class RegionCreate(RegionBase):
    pass


class RegionResponse(RegionBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CityBase(BaseModel):
    region_id: int
    name_ru: str
    name_kz: str


class CityCreate(CityBase):
    pass


class CityResponse(CityBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SkillBase(BaseModel):
    name_ru: str
    name_kz: str
    category: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Схемы для образования
class ResumeEducationBase(BaseModel):
    institution_name: str
    specialization: str
    education_level: EducationLevelEnum
    start_year: int
    end_year: Optional[int] = None
    is_current: bool = False


class ResumeEducationCreate(ResumeEducationBase):
    pass


class ResumeEducationUpdate(BaseModel):
    institution_name: Optional[str] = None
    specialization: Optional[str] = None
    education_level: Optional[EducationLevelEnum] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: Optional[bool] = None


class ResumeEducationResponse(ResumeEducationBase):
    id: int
    resume_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Схемы для опыта работы
class ResumeWorkExperienceBase(BaseModel):
    company_name: str
    position: str
    responsibilities: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False


class ResumeWorkExperienceCreate(ResumeWorkExperienceBase):
    pass


class ResumeWorkExperienceUpdate(BaseModel):
    company_name: Optional[str] = None
    position: Optional[str] = None
    responsibilities: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None


class ResumeWorkExperienceResponse(ResumeWorkExperienceBase):
    id: int
    resume_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Схемы для навыков резюме
class ResumeSkillBase(BaseModel):
    skill_id: int
    skill_level: Optional[str] = None


class ResumeSkillCreate(ResumeSkillBase):
    pass


class ResumeSkillResponse(ResumeSkillBase):
    id: int
    resume_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Основные схемы для резюме
class ResumeBase(BaseModel):
    profession_id: int
    full_name: str
    gender: str
    city_id: int
    phone_number: str
    birth_date: date
    citizenship: str
    about_me: Optional[str] = None
    salary_expectation: Optional[str] = None
    employment_type: Optional[str] = None

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.startswith('+'):
            v = '+' + v
        return v


class ResumeCreate(ResumeBase):
    pass


class ResumeUpdate(BaseModel):
    profession_id: Optional[int] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None  # "male", "female"
    city_id: Optional[int] = None
    phone_number: Optional[str] = None
    birth_date: Optional[date] = None
    citizenship: Optional[str] = None
    about_me: Optional[str] = None
    salary_expectation: Optional[str] = None
    employment_type: Optional[str] = None
    is_published: Optional[bool] = None


class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    is_active: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Полная схема резюме с вложенными данными
class ResumeFullResponse(ResumeResponse):
    education: List[ResumeEducationResponse] = []
    work_experience: List[ResumeWorkExperienceResponse] = []
    skills: List[ResumeSkillResponse] = []

    class Config:
        from_attributes = True


# Схемы для создания полного резюме с вложенными данными
class ResumeFullCreate(BaseModel):
    resume: ResumeCreate
    education: List[ResumeEducationCreate] = []
    work_experience: List[ResumeWorkExperienceCreate] = []
    skills: List[ResumeSkillCreate] = []