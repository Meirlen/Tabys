from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from typing import List
from typing import Dict, List, Optional, Any, Union

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




# Pydantic model to serialize User data with additional fields
class UserResponse(BaseModel):
    id: int
    phone_number: Optional[str]
    user_name: Optional[str]
    role: str
    country: Optional[str]
    city: Optional[str]
    status: str
    created_at: str
    booking_count: int = 0
    skyscanner_count: int = 0

    class Config:
        orm_mode = True

class TemplateCreate(BaseModel):
    title: str
    message: str

class TemplateUpdate(BaseModel):
    title: str
    message: str

class Chat_Gpt_config_Create(BaseModel):
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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


class ExpertDetail(ExpertBase):
    id: int
    education: List[Education] = []
    experience: List[WorkExperience] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


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
        orm_mode = True


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

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime, date


# Базовый класс для вакансий
class VacancyBase(BaseModel):
    # Multilingual fields
    title_kz: str
    title_ru: str
    description_kz: str
    description_ru: str
    location_kz: Optional[str] = None
    location_ru: Optional[str] = None
    requirements_kz: Optional[str] = None
    requirements_ru: Optional[str] = None

    # Common fields
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    deadline: Optional[date] = None

    # Валидаторы для проверки длины описаний
    @validator('description_kz', 'description_ru')
    def validate_description_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError("Описание вакансии не должно превышать 1000 символов")
        return v


# Класс для создания вакансии
class VacancyCreate(VacancyBase):
    pass


# Класс для ответа при получении деталей вакансии
class VacancyDetail(VacancyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# Класс для краткого представления вакансии в списке
class VacancyList(BaseModel):
    id: int
    title_kz: str
    title_ru: str
    location_kz: Optional[str] = None
    location_ru: Optional[str] = None
    salary: Optional[str] = None
    created_at: datetime
    is_active: bool
    deadline: Optional[date] = None

    class Config:
        orm_mode = True

class VacancyCreate(VacancyBase):
    pass


class VacancyUpdate(BaseModel):
    title: Optional[str] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None

    @validator('description')
    def validate_description_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Описание вакансии не должно превышать 1000 символов')
        return v


class VacancyList(VacancyBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class VacancyDetail(VacancyList):
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class VacancyFilter(BaseModel):
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    city: Optional[str] = None
    search: Optional[str] = None




class VacancyApplicationBase(BaseModel):
    vacancy_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    cover_letter: Optional[str] = None
    resume_filename: str


class VacancyApplicationCreate(VacancyApplicationBase):
    pass


class VacancyApplication(VacancyApplicationBase):
    id: int
    created_at: datetime
    status: Optional[str] = "new"

    class Config:
        orm_mode = True





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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


# Event schemas
class EventBase(BaseModel):
    title: str
    event_date: datetime
    location: str
    format: Literal["Online", "Offline"]
    description: str


class EventCreate(EventBase):
    programs: List[EventProgramCreate] = []
    speakers: List[EventSpeakerCreate] = []


class EventList(EventBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class EventDetail(EventBase):
    id: int
    programs: List[EventProgram] = []
    speakers: List[EventSpeaker] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class EventUpdate(BaseModel):
    title: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    format: Optional[Literal["Online", "Offline"]] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True


# Схема для подробного отображения курса
class CourseDetail(CourseList):
    course_url: str
    skills: str
    video_preview: Optional[str]
    author_id: int
    updated_at: datetime
    chapters: List[CourseChapter]

    class Config:
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True




from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CertificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CertificateBase(BaseModel):
    title: str
    description: str
    course_id: Optional[int] = None
    issuer: str
    issue_date: datetime


class CertificateCreate(CertificateBase):
    pass


class CertificateDetail(CertificateBase):
    id: int
    certificate_url: Optional[str] = None
    certificate_image: Optional[str] = None
    user_id: int
    status: CertificationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class CertificateList(BaseModel):
    id: int
    title: str
    issuer: str
    issue_date: datetime
    status: CertificationStatus
    certificate_url: Optional[str] = None
    certificate_image: Optional[str] = None

    class Config:
        orm_mode = True


class CertificateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[int] = None
    issuer: Optional[str] = None
    issue_date: Optional[datetime] = None
    certificate_url: Optional[str] = None
    certificate_image: Optional[str] = None


class CertificateStatusUpdate(BaseModel):
    status: CertificationStatus
    status_comment: Optional[str] = None


class CertificateApplicationBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    message: Optional[str] = None
    course_id: Optional[int] = None


class CertificateApplicationCreate(CertificateApplicationBase):
    pass


class CertificateApplication(CertificateApplicationBase):
    id: int
    user_id: int
    application_id: str
    created_at: datetime
    status: CertificationStatus

    class Config:
        orm_mode = True


class CertificateFilter(BaseModel):
    course_id: Optional[int] = None
    status: Optional[CertificationStatus] = None
    search: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None