from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Enum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


# Enums
class GenderEnum(enum.Enum):
    MALE = "male"
    FEMALE = "female"


class EducationLevelEnum(enum.Enum):
    SECONDARY = "secondary"
    VOCATIONAL = "vocational"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


# Справочные таблицы
class Profession(Base):
    __tablename__ = "professions"

    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String(255), nullable=False)
    name_kz = Column(String(255), nullable=False)
    category = Column(String(255), nullable=True)  # IT, Медицина, Образование и т.д.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String(255), nullable=False)
    name_kz = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)  # Связь с областью
    name_ru = Column(String(255), nullable=False)
    name_kz = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String(255), nullable=False)
    name_kz = Column(String(255), nullable=False)
    category = Column(String(255), nullable=True)  # Технические, Мягкие навыки и т.д.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


# Основная таблица резюме
class Resume(Base):
    __tablename__ = "resumes_"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)

    # Основная информация
    profession_id = Column(Integer, nullable=False)
    full_name = Column(String(255), nullable=False)
    gender =  Column(String(255), nullable=False)
    city_id = Column(Integer, nullable=False)
    phone_number = Column(String(20), nullable=False)
    birth_date = Column(Date, nullable=False)
    citizenship = Column(String(100), nullable=False)

    # Дополнительная информация
    about_me = Column(Text, nullable=True)
    salary_expectation = Column(String(100), nullable=True)
    employment_type = Column(String(50), nullable=True)  # Полная, частичная, удаленная

    # Статус
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Образование
class ResumeEducation(Base):
    __tablename__ = "resume_education"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, nullable=False)

    institution_name = Column(String(255), nullable=False)
    specialization = Column(String(255), nullable=False)
    education_level = Column(String(50), nullable=False)  # "secondary", "vocational", "bachelor", "master", "phd"
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=True)
    is_current = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())


# Опыт работы
class ResumeWorkExperience(Base):
    __tablename__ = "resume_work_experience"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, nullable=False)

    company_name = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    responsibilities = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())


# Навыки резюме
class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, nullable=False)
    skill_id = Column(Integer, nullable=False)
    skill_level = Column(String(20), nullable=True)  # Начинающий, Средний, Продвинутый

    created_at = Column(DateTime, default=func.now())