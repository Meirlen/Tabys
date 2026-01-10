
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, validator, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class UserTypeEnum(str, Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"

class ServiceStatusEnum(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"

class PersonStatusEnum(str, Enum):
    STUDENT = "student"
    WORKER = "worker"
    SCHOOLER = "schooler"
    UNEMPLOYED = "unemployed"

class OrganizationTypeEnum(str, Enum):
    BUSINESS = "business"
    GOVERNMENT = "government"
    EDUCATIONAL = "educational"
    NON_PROFIT = "non_profit"

class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ModerationAction(BaseModel):
    moderation_status: ModerationStatus
    moderation_comment: Optional[str] = None

class ModerationStats(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int

class TextMessageData(BaseModel):
    textMessage:str


class MessageData(BaseModel):
    TextMessageData:TextMessageData

class WebHookBody(BaseModel):
    messageData: MessageData

class Blacklist(BaseModel):
    phone: str
    comment: str


class LoginAdmin(BaseModel):
    login: str
    password: str


class TokenData(BaseModel):
    id: Optional[str] = None

class AdminCreate(BaseModel):
    name: str
    login: str = None
    password: str = None
    phone: str = None



class UserMessage(BaseModel):
    room_id: str
    message: str

class UserMessageZapis(BaseModel):
    firm_id: int
    message: str



# Pydantic model for response
class MessageCountResponse(BaseModel):
    date: str  # Date format, e.g., "2024-11-01"
    count: int

class MessageStatsResponse(BaseModel):
    start_date: str
    end_date: str
    stats: List[MessageCountResponse]


class UserCountResponse(BaseModel):
    date: str  # Формат даты, например "01.11.2024"
    count: int


class UserStatsResponse(BaseModel):
    start_date: str
    end_date: str
    stats: List[UserCountResponse]


# Схемы для авторизации
class LoginRequest(BaseModel):
    phone_number: str



class OtpRequest(BaseModel):
    phone_number: str
    code: str


# Схемы для регистрации физических лиц
class IndividualRegistration(BaseModel):
    phone_number: str
    full_name: str
    address: str
    person_status_id: int



# Схемы для регистрации организаций
# Схема остается с phone_number
class OrganizationRegistration(BaseModel):
    phone_number: str
    name: str
    bin_number: str
    organization_type_id: int
    address: str
    email: Optional[EmailStr] = None
    otp_code: Optional[str] = None  # Optional OTP code for verification





# Pydantic model to serialize User data with additional fields
# Схемы для ответов
class UserResponse(BaseModel):
    id: int
    phone_number: str
    user_type: UserTypeEnum
    service_status: ServiceStatusEnum
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class IndividualResponse(UserResponse):
    individual_data: Optional['IndividualData'] = None

class OrganizationResponse(UserResponse):
    organization_data: Optional['OrganizationData'] = None


class IndividualData(BaseModel):
    full_name: str
    id_document_photo: str
    selfie_with_id_photo: str
    address: str
    person_status_id: int

    class Config:
        from_attributes = True


class OrganizationData(BaseModel):
    name: str
    bin_number: str
    organization_type_id: int
    email: Optional[str] = None
    address: str

    class Config:
        from_attributes = True


# Справочники
class PersonStatusResponse(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    code: PersonStatusEnum

    class Config:
        from_attributes = True


class OrganizationTypeResponse(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    code: OrganizationTypeEnum

    class Config:
        from_attributes = True



# Токены
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_data: UserResponse

class LoginResponse(BaseModel):
    message: str
    otp_sent: bool = True



# Обновляем forward references
IndividualResponse.update_forward_refs()
OrganizationResponse.update_forward_refs()



class TemplateCreate(BaseModel):
    title: str
    message: str

class TemplateUpdate(BaseModel):
    title: str
    message: str

class Chat_Gpt_config_Create(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_ prefix

    instance_id:int
    model_name: str
    message: str


class CategoryCreate(BaseModel):
    name: str
    name_ru: str

class PageCreate(BaseModel):
    name: str
    name_ru: str
    page_key:str
    type:str
    category_id: int


class TableColumnCreate(BaseModel):
    name: str
    page_id: int
    column_type: str
    field_info: str



# Pydantic схемы для Table_content
class TableContentCreate(BaseModel):
    content: str
    column_id: int
    instance_id: int



# Pydantic-схема для валидации данных
class CompanySchema(BaseModel):
    instance_id: int
    name: str
    phone: str
    desc: str

    site:  str = None
    email:  str = None





# Pydantic-схема для адреса компании
class AddressCreateSchema(BaseModel):
    instance_id: int
    name: str
    city: str

    class Config:
        from_attributes = True


class AddressUpdateSchema(BaseModel):
    id: int
    name: str
    city: str

class WorkScheduleCreateSchema(BaseModel):
    instance_id: int
    address_id: int
    Mon: str
    Tue: str
    Wed: str
    Thu: str
    Fri: str
    Sat: str
    Sun: str
    for_all_addresses:bool
    full_day:bool
    full_week:bool



class WorkScheduleUpdateSchema(BaseModel):
    id: int
    Mon: str
    Tue: str
    Wed: str
    Thu: str
    Fri: str
    Sat: str
    Sun: str



class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserCreate2(BaseModel):
    phone_number: str
    password: str


class Login(BaseModel):
    phone_number: str


class CheckOtp(BaseModel):
    phone_number: str
    otp: str



class AvailableDate(BaseModel):
    firm_id: int
    date: str



class CredentialsCreate(BaseModel):
    service_name: str
    token_type: str
    value: Optional[str] = None  # value can be optional if not provided


# Pydantic схемы для валидации данных
class EducationBase(BaseModel):
    university: str
    start_date: datetime
    end_date: Optional[datetime] = None
    specialization: Optional[str] = None
    degree: Optional[str] = None
    certificates: Optional[str] = None


class EducationCreate(EducationBase):
    pass


class Education(EducationBase):
    id: int
    expert_id: int

    class Config:
        from_attributes = True


class WorkExperienceBase(BaseModel):
    company_name: str
    position: str
    start_date: datetime
    end_date: Optional[datetime] = None
    work_description: Optional[str] = None


class WorkExperienceCreate(WorkExperienceBase):
    pass


class WorkExperience(WorkExperienceBase):
    id: int
    expert_id: int

    class Config:
        from_attributes = True


class ExpertBase(BaseModel):
    full_name: str
    specialization: str
    phone: Optional[str] = None
    website: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None


class ExpertCreate(ExpertBase):
    education: List[EducationCreate] = []
    experience: List[WorkExperienceCreate] = []


class ExpertList(ExpertBase):
    id: int

    class Config:
        from_attributes = True


class ExpertDetail(ExpertBase):
    id: int
    education: List[Education] = []
    experience: List[WorkExperience] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollaborationRequestBase(BaseModel):
    user_name: str
    user_email: EmailStr
    user_phone: Optional[str] = None
    message: Optional[str] = None


class CollaborationRequestCreate(CollaborationRequestBase):
    pass


class CollaborationRequest(CollaborationRequestBase):
    id: int
    request_id: str
    expert_id: int
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class ExpertFilter(BaseModel):
    specialization: Optional[str] = None
    city: Optional[str] = None
    search: Optional[str] = None



# Добавьте в schemas.py

# Модель для токена
class Token(BaseModel):
    access_token: str
    token_type: str


# Модель данных токена
class TokenData(BaseModel):
    id: Optional[str] = None





from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date


# ========== ВЛОЖЕННЫЕ СХЕМЫ ==========

class ProfessionInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True


class CityInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    region_id: int

    class Config:
        from_attributes = True


class SkillInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True


from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date


# ========== ВЛОЖЕННЫЕ СХЕМЫ ==========

class ProfessionInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True


class CityInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    region_id: int

    class Config:
        from_attributes = True


class SkillInVacancy(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True


# ========== СХЕМЫ ДЛЯ ВАКАНСИЙ ==========

class VacancyCreate(BaseModel):
    """Создание вакансии"""
    # Основные поля (ОБЯЗАТЕЛЬНЫЕ)
    profession_id: int
    city_id: int
    title_kz: str
    title_ru: str
    description_kz: str
    description_ru: str
    employment_type: str
    work_type: str
    contact_email: EmailStr

    # Дополнительные поля
    requirements_kz: Optional[str] = None
    requirements_ru: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_years: Optional[int] = None
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    deadline: Optional[date] = None
    required_skills: Optional[List[int]] = None  # ID навыков


class VacancyUpdate(BaseModel):
    """Обновление вакансии"""
    profession_id: Optional[int] = None
    city_id: Optional[int] = None
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    requirements_kz: Optional[str] = None
    requirements_ru: Optional[str] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_years: Optional[int] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    deadline: Optional[date] = None
    is_active: Optional[bool] = None
    required_skills: Optional[List[int]] = None


class VacancyList(BaseModel):
    """Список вакансий (краткая инфа)"""
    id: int
    profession: Optional[ProfessionInVacancy] = None
    city: Optional[CityInVacancy] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_years: Optional[int] = None
    company_name: Optional[str] = None
    deadline: Optional[date] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class VacancyDetail(BaseModel):
    """Детальная информация о вакансии"""
    id: int
    profession: Optional[ProfessionInVacancy] = None
    city: Optional[CityInVacancy] = None
    description_kz: str
    description_ru: str
    requirements_kz: Optional[str] = None
    requirements_ru: Optional[str] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_years: Optional[int] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    required_skills: List[SkillInVacancy] = []
    deadline: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Moderation fields
    moderation_status: str = "approved"
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None
    moderation_comment: Optional[str] = None
    is_admin_created: bool = False

    class Config:
        from_attributes = True


# ========== СХЕМЫ ДЛЯ ОТКЛИКОВ ==========

class VacancyApplicationCreate(BaseModel):
    """Создание отклика"""
    resume_id: int
    cover_letter: Optional[str] = None
    vacancy_id: Optional[int] = None  # заполняется автоматически в роуте


class VacancyApplicationUpdate(BaseModel):
    """Обновление статуса отклика"""
    status: str  # new, reviewed, accepted, rejected


class VacancyApplicationResponse(BaseModel):
    """Ответ с информацией об отклике"""
    id: int
    vacancy_id: int
    user_id: int
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== ФИЛЬТРЫ ==========

class VacancyFilter(BaseModel):
    """Фильтры для поиска вакансий"""
    profession_id: Optional[int] = None
    city_id: Optional[int] = None
    region_id: Optional[int] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    keyword: Optional[str] = None
    lang: Optional[str] = "ru"


class ResumeBasic(BaseModel):
    """Базовая информация о резюме для выбора"""
    id: int
    profession_id: int
    full_name: str
    is_active: bool
    is_published: bool

    # Дополнительная информация для удобства выбора
    profession_name: Optional[str] = None
    city_name: Optional[str] = None

    class Config:
        from_attributes = True





from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

# Program schemas
class EventProgramBase(BaseModel):
    time: int
    description: str


class EventProgramCreate(EventProgramBase):
    pass


class EventProgram(EventProgramBase):
    id: int
    event_id: int

    class Config:
        from_attributes = True


# Speaker schemas
class EventSpeakerBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    bio: str
    photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None


class EventSpeakerCreate(EventSpeakerBase):
    pass


class EventSpeaker(EventSpeakerBase):
    id: int
    event_id: int

    class Config:
        from_attributes = True


# Participant schemas
class EventParticipantBase(BaseModel):
    first_name: str
    last_name: str
    company_name: str
    email: EmailStr


class EventParticipantCreate(EventParticipantBase):
    pass


class EventParticipant(EventParticipantBase):
    id: int
    event_id: int
    registration_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Event schemas
class EventBase(BaseModel):
    title: str
    event_date: datetime
    location: str
    format: Literal["Online", "Offline"]
    description: str
    event_photo: Optional[str] = None


class EventCreate(EventBase):
    programs: List[EventProgramCreate] = []
    speakers: List[EventSpeakerCreate] = []


class EventList(EventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventDetail(EventBase):
    id: int
    programs: List[EventProgram] = []
    speakers: List[EventSpeaker] = []
    created_at: datetime
    updated_at: datetime

    # Moderation fields
    moderation_status: str = "approved"
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None
    moderation_comment: Optional[str] = None
    is_admin_created: bool = False

    class Config:
        from_attributes = True


class EventUpdate(BaseModel):
    title: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    format: Optional[Literal["Online", "Offline"]] = None
    description: Optional[str] = None
    event_photo: Optional[str] = None

    class Config:
        from_attributes = True


class EventFilter(BaseModel):
    format: Optional[str] = None
    search: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum


# Перечисления для выпадающих списков
class CourseLanguage(str, Enum):
    KAZAKH = "kz"
    RUSSIAN = "ru"
    ENGLISH = "en"


class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CourseCurrency(str, Enum):
    KZT = "KZT"
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"


class CourseStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Категории курсов
class CourseCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CourseCategoryCreate(CourseCategoryBase):
    pass


class CourseCategory(CourseCategoryBase):
    id: int

    class Config:
        from_attributes = True


# Ответы на тесты
class CourseTestAnswerBase(BaseModel):
    answer_text: str
    is_correct: bool = False


class CourseTestAnswerCreate(CourseTestAnswerBase):
    pass


class CourseTestAnswer(CourseTestAnswerBase):
    id: int
    test_id: int

    class Config:
        from_attributes = True


# Тесты
class CourseTestBase(BaseModel):
    question: str
    image: Optional[str] = None


class CourseTestCreate(CourseTestBase):
    answers: List[CourseTestAnswerCreate]


class CourseTest(CourseTestBase):
    id: int
    lesson_id: int
    answers: List[CourseTestAnswer]

    class Config:
        from_attributes = True


# Уроки
class CourseLessonBase(BaseModel):
    title: str
    description: str
    video_url: str
    order: int


class CourseLessonCreate(CourseLessonBase):
    tests: Optional[List[CourseTestCreate]] = []


class CourseLesson(CourseLessonBase):
    id: int
    chapter_id: int
    tests: List[CourseTest] = []

    class Config:
        from_attributes = True


# Главы курса
class CourseChapterBase(BaseModel):
    title: str
    order: int

class LoginUserSchema(BaseModel):
    phone_number: str


class CourseChapterCreate(CourseChapterBase):
    lessons: Optional[List[CourseLessonCreate]] = []



class CourseChapter(CourseChapterBase):
    id: int
    course_id: int
    lessons: List[CourseLesson] = []

    class Config:
        from_attributes = True


# Базовая схема курса
class CourseBase(BaseModel):
    title: str
    description: str
    course_url: str
    language: CourseLanguage
    duration: int
    skills: str
    currency: CourseCurrency
    price: float
    level: Optional[CourseLevel] = None

    @validator('price')
    def price_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Цена не может быть отрицательной')
        return v

    @validator('duration')
    def duration_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Продолжительность курса должна быть положительным числом')
        return v


# Схема для создания курса
class CourseCreate(CourseBase):
    cover_image: Optional[str] = None
    video_preview: Optional[str] = None
    categories: List[int] = []  # ID категорий
    chapters: List[CourseChapterCreate] = []
    is_free: Optional[bool] = False


# Схема для обновления курса
class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_url: Optional[str] = None
    language: Optional[CourseLanguage] = None
    duration: Optional[int] = None
    skills: Optional[str] = None
    currency: Optional[CourseCurrency] = None
    price: Optional[float] = None
    cover_image: Optional[str] = None
    video_preview: Optional[str] = None
    level: Optional[CourseLevel] = None
    categories: Optional[List[int]] = None
    is_free: Optional[bool] = None
    is_popular: Optional[bool] = None
    is_recommended: Optional[bool] = None

    @validator('price')
    def price_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('Цена не может быть отрицательной')
        return v

    @validator('duration')
    def duration_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Продолжительность курса должна быть положительным числом')
        return v


# Схема для обновления статуса курса (для модерации администратором)
class CourseStatusUpdate(BaseModel):
    status: CourseStatus
    status_comment: Optional[str] = None


# Схема для отображения списка курсов
class CourseList(BaseModel):
    id: int
    title: str
    description: str
    language: str
    duration: int
    price: float
    currency: str
    cover_image: Optional[str]
    is_free: bool
    is_popular: bool
    is_recommended: bool
    rating: float
    views_count: int
    level: Optional[str]
    status: CourseStatus
    categories: List[CourseCategory]
    created_at: datetime

    class Config:
        from_attributes = True


# Схема для подробного отображения курса
class CourseDetail(CourseList):
    course_url: str
    skills: str
    video_preview: Optional[str]
    author_id: int
    updated_at: datetime
    chapters: List[CourseChapter]

    # Moderation fields
    moderation_status: str = "approved"
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[int] = None
    moderation_comment: Optional[str] = None
    is_admin_created: bool = False

    class Config:
        from_attributes = True


# Схема для записи на курс
class CourseEnrollmentCreate(BaseModel):
    course_id: int


# Схема для отображения записи на курс
class CourseEnrollment(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrollment_date: datetime
    completed: bool
    completion_date: Optional[datetime] = None
    progress: float
    completed_lessons: List[int] = []  # Добавляем это поле

    class Config:
        from_attributes = True


# Схема для фильтрации курсов
class CourseFilter(BaseModel):
    category_id: Optional[int] = None
    language: Optional[CourseLanguage] = None
    level: Optional[CourseLevel] = None
    is_free: Optional[bool] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    search: Optional[str] = None  # Поиск по названию и описанию


# Новая схема, которую нужно добавить
class CourseEnrollmentWithCourse(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrollment_date: datetime
    completed: bool = False
    completion_date: Optional[datetime] = None
    progress: float = 0.0
    completed_lessons: List[int] = []
    course: CourseList  # Включаем полную информацию о курсе

    class Config:
        from_attributes = True



from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

# Базовая схема для сертификатов
class CertificateBase(BaseModel):
    title: str
    description: Optional[str] = None
    course_id: Optional[int] = None  # Необязательное поле

# Схема для создания сертификата
class CertificateCreate(CertificateBase):
    user_id: int
    image_url: Optional[str] = None
    file_url: Optional[str] = None

# Схема для обновления сертификата
class CertificateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[int] = None
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    status: Optional[str] = None

# Схема для ответа (полная информация о сертификате)
class Certificate(CertificateBase):
    id: int
    user_id: int
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    issue_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схема для фильтрации сертификатов
class CertificateFilter(BaseModel):
    status: Optional[str] = None
    user_id: Optional[int] = None
    course_id: Optional[int] = None
    issue_date_from: Optional[date] = None
    issue_date_to: Optional[date] = None



# Добавьте эти схемы в ваш файл schemas.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# RBAC Role Enum
class RoleEnum(str, Enum):
    CLIENT = "client"
    VOLUNTEER_ADMIN = "volunteer_admin"
    MSB = "msb"
    NPO = "npo"
    GOVERNMENT = "government"
    ADMINISTRATOR = "administrator"
    SUPER_ADMIN = "super_admin"

# Схемы для администратора
class AdminBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Имя администратора")
    login: str = Field(..., min_length=3, max_length=50, description="Логин администратора")
    email: Optional[str] = Field(None, description="Email для уведомлений")

class AdminRegister(AdminBase):
    password: str = Field(..., min_length=6, max_length=100, description="Пароль администратора")
    role: Optional[RoleEnum] = Field(default=RoleEnum.CLIENT, description="Роль администратора")

class AdminLogin(BaseModel):
    login: str = Field(..., description="Логин администратора")
    password: str = Field(..., description="Пароль администратора")

class AdminResponse(AdminBase):
    id: int
    email: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime
    approval_status: str = "pending"
    approval_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None

    class Config:
        from_attributes = True

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_data: AdminResponse

class AdminChangePassword(BaseModel):
    old_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=6, max_length=100, description="Новый пароль")

class AdminProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Имя администратора")
    email: Optional[str] = Field(None, description="Email для уведомлений")

class AdminApprovalUpdate(BaseModel):
    approval_status: str = Field(..., description="Status: approved or rejected")
    approval_reason: Optional[str] = Field(None, description="Optional reason for the decision")

class AdminApprovalResponse(BaseModel):
    message: str
    admin: AdminResponse

class AdminProfileResponse(BaseModel):
    id: int
    name: str
    login: str
    email: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime
    approval_status: str = "pending"
    approval_reason: Optional[str] = None