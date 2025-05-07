from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float,Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from typing import List, Optional
from enum import Enum as PyEnum

from app.database import Base
from pydantic_settings import BaseSettings
from sqlalchemy import Column, Integer, String, JSON

from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()



class Credentials(Base):
    __tablename__ = "credentials_"
    id = Column(Integer, primary_key=True, nullable=False)
    service_name = Column(String, nullable=False)
    token_type = Column(String, nullable=False)
    value = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))



class Otp(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, nullable=False)
    phone_number = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))




class Admin(Base):
    __tablename__ = "adminstrators_shaqyru"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    login = Column(String, nullable=True)
    password = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                            nullable=False, server_default=text('now()'))






class HashOtps(Base):
    __tablename__ = "hash_code"
    id = Column(Integer, primary_key=True, nullable=False)
    firm_id = Column(Integer)
    hash = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    otp = Column(String, nullable=False)
    pay_code = Column(String, nullable=True)
    test_code = Column(String, nullable=True)
    status = Column(String,nullable=False,server_default='start')







from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary,Date
from sqlalchemy.orm import relationship
from app.database import Base


class Vacancy(Base):
    __tablename__ = "vacancies_"

    id = Column(Integer, primary_key=True, index=True)
    # Multilingual fields
    title_kz = Column(String, nullable=False)
    title_ru = Column(String, nullable=False)
    location_kz = Column(String, nullable=True)
    location_ru = Column(String, nullable=True)
    description_kz = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)
    requirements_kz = Column(Text, nullable=True)
    requirements_ru = Column(Text, nullable=True)

    # Common fields
    employment_type = Column(String, nullable=True)
    work_type = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    deadline = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Отношение к откликам на вакансию
    applications = relationship("VacancyApplication", back_populates="vacancy", cascade="all, delete-orphan")



class VacancyApplication(Base):
    __tablename__ = "vacancy_applications_1"

    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies_.id"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    cover_letter = Column(Text, nullable=True)
    resume_filename = Column(String, nullable=False)
    resume_content = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False)
    # Add status field with default value
    status = Column(String, default="new")

    # Отношение к вакансии
    vacancy = relationship("Vacancy", back_populates="applications")


from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from uuid import uuid4


class Event(Base):
    __tablename__ = "events_"

    id = Column(Integer, primary_key=True, index=True)
    event_date = Column("date", DateTime, nullable=False)  # This maps 'event_date' to column 'date'
    title = Column(String, nullable=False)
    location = Column(String, nullable=False)
    format = Column(Enum("Online", "Offline", name="event_format"), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    programs = relationship("EventProgram", back_populates="event", cascade="all, delete-orphan")
    speakers = relationship("EventSpeaker", back_populates="event", cascade="all, delete-orphan")
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")


class EventProgram(Base):
    __tablename__ = "event_programs_"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events_.id"), nullable=False)
    time = Column(Integer, nullable=False)  # Time in minutes from event start or specific time
    description = Column(Text, nullable=False)

    event = relationship("Event", back_populates="programs")


class EventSpeaker(Base):
    __tablename__ = "event_speakers_"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events_.id"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    bio = Column(Text, nullable=False)
    photo_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)

    event = relationship("Event", back_populates="speakers")


class EventParticipant(Base):
    __tablename__ = "event_participants"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events_.id"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    registration_id = Column(String, default=lambda: str(uuid4()), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="participants")


from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Table, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from uuid import uuid4

# Таблица для связи многие-ко-многим между курсами и категориями
course_category = Table(
    "course_category",
    Base.metadata,
    Column("course_id", Integer, ForeignKey("courses.id")),
    Column("category_id", Integer, ForeignKey("course_categories.id"))
)


# Справочная таблица категорий курсов
class CourseCategory(Base):
    __tablename__ = "course_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Связь с курсами
    courses = relationship("Course", secondary=course_category, back_populates="categories")


# Основная модель курса
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    course_url = Column(String, nullable=False)
    language = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # Длительность в минутах
    skills = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    cover_image = Column(String, nullable=True)  # Путь к файлу изображения
    video_preview = Column(String, nullable=True)  # Путь к файлу видео

    # Дополнительные поля для отслеживания
    level = Column(String, nullable=True)
    is_free = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    is_recommended = Column(Boolean, default=False)
    views_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)

    # Статус модерации
    status = Column(Enum("pending", "approved", "rejected", name="course_status"), default="pending")
    status_comment = Column(Text, nullable=True)

    # Информация о создателе - вот здесь проблема
    # Заменяем 'user_bot___' на фактическое имя таблицы из вашей модели User
    author_id = Column(Integer, nullable=False)

    # Время создания и обновления
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    # Удаляем проблемную связь с User
    # author = relationship("User", backref="courses")
    categories = relationship("CourseCategory", secondary=course_category, back_populates="courses")
    chapters = relationship("CourseChapter", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")


# Разделы (главы) курса
class CourseChapter(Base):
    __tablename__ = "course_chapters"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, nullable=False)  # Порядок отображения

    # Связи
    course = relationship("Course", back_populates="chapters")
    lessons = relationship("CourseLesson", back_populates="chapter", cascade="all, delete-orphan")


# Уроки внутри разделов
class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("course_chapters.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    video_url = Column(String, nullable=False)  # Путь к файлу видео
    order = Column(Integer, nullable=False)  # Порядок отображения

    # Связи
    chapter = relationship("CourseChapter", back_populates="lessons")
    tests = relationship("CourseTest", back_populates="lesson", cascade="all, delete-orphan")


# Тесты к урокам
class CourseTest(Base):
    __tablename__ = "course_tests"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id"), nullable=False)
    question = Column(Text, nullable=False)
    image = Column(String, nullable=True)  # Путь к файлу изображения

    # Связи
    lesson = relationship("CourseLesson", back_populates="tests")
    answers = relationship("CourseTestAnswer", back_populates="test", cascade="all, delete-orphan")


# Варианты ответов к тестам
class CourseTestAnswer(Base):
    __tablename__ = "course_test_answers"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("course_tests.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    # Связь с тестом
    test = relationship("CourseTest", back_populates="answers")


# Модель для записи на курсы
class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Убираем ForeignKey тоже
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    progress = Column(Float, default=0.0)  # Процент выполнения от 0 до 100

    # Связи
    # Удаляем проблемную связь с User
    # user = relationship("User", backref="enrollments")
    course = relationship("Course", back_populates="enrollments")
    lesson_progress = relationship("CourseLessonProgress", back_populates="enrollment", cascade="all, delete-orphan")
    test_results = relationship("CourseTestResult", back_populates="enrollment", cascade="all, delete-orphan")


# Прогресс по урокам
class CourseLessonProgress(Base):
    __tablename__ = "course_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("course_enrollments.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    last_viewed_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    enrollment = relationship("CourseEnrollment", back_populates="lesson_progress")
    lesson = relationship("CourseLesson")


# Результаты тестов
class CourseTestResult(Base):
    __tablename__ = "course_test_results"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("course_enrollments.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("course_tests.id"), nullable=False)
    is_passed = Column(Boolean, default=False)
    score = Column(Float, nullable=False)  # Процент правильных ответов
    attempt_count = Column(Integer, default=1)
    last_attempt_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    enrollment = relationship("CourseEnrollment", back_populates="test_results")
    test = relationship("CourseTest")



class User(Base):
    __tablename__ = "user_bot_experts"
    id = Column(Integer, primary_key=True, nullable=False)
    phone_number = Column(String,  unique=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))


from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from uuid import uuid4


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    issuer = Column(String, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    certificate_url = Column(String, nullable=True)
    certificate_image = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    status = Column(Enum("pending", "approved", "rejected", name="certificate_status"), default="pending")
    status_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с курсом (если есть)
    course = relationship("Course", backref="certificates")


class CertificateApplication(Base):
    __tablename__ = "certificate_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String, default=lambda: str(uuid4()), unique=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum("pending", "approved", "rejected", name="application_status"), default="pending")

    # Связь с курсом (если есть)
    course = relationship("Course", backref="certificate_applications")



from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4


# SQLAlchemy модели
class Expert(Base):
    __tablename__ = "experts"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    specialization = Column(String, nullable=False)
    phone = Column(String)
    website = Column(String)
    city = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    avatar_url = Column(String, nullable=True)  # <-- НОВОЕ ПОЛЕ ДЛЯ URL АВАТАРА
    education = relationship("Education", back_populates="expert")
    experience = relationship("WorkExperience", back_populates="expert")
    collaboration_requests = relationship("CollaborationRequest", back_populates="expert")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    expert_id = Column(Integer, ForeignKey("experts.id"))
    university = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    specialization = Column(String)
    degree = Column(String)
    certificates = Column(String)

    expert = relationship("Expert", back_populates="education")


class WorkExperience(Base):
    __tablename__ = "work_experience"

    id = Column(Integer, primary_key=True, index=True)
    expert_id = Column(Integer, ForeignKey("experts.id"))
    company_name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    work_description = Column(Text)

    expert = relationship("Expert", back_populates="experience")


class CollaborationRequest(Base):
    __tablename__ = "collaboration_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, default=lambda: str(uuid4()), unique=True)
    expert_id = Column(Integer, ForeignKey("experts.id"))
    user_name = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    user_phone = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, approved, rejected

    expert = relationship("Expert", back_populates="collaboration_requests")
