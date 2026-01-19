from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum
from app.database import Base


# Enums для типов проектов
class ProjectTypeEnum(enum.Enum):
    VOTING = "voting"  # Голосовалка
    APPLICATION = "application"  # Прием заявок


class ProjectStatusEnum(enum.Enum):
    DRAFT = "draft"  # Черновик
    ACTIVE = "active"  # Активный
    COMPLETED = "completed"  # Завершенный
    CANCELLED = "cancelled"  # Отмененный


# Основная модель проекта
class Project(Base):
    __tablename__ = "projects_multi_2"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    title_ru = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    # Используйте:
    project_type = Column(String(50), nullable=False)  # "voting" или "application"
    status = Column(String(50), default="draft")
    # Даты
    created_at = Column(DateTime, nullable=False, default=func.now())
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Медиа файлы
    photo_url = Column(String(500), nullable=True)  # Основное фото
    video_url = Column(String(500), nullable=True)  # YouTube ссылка

    # Owner tracking for RBAC
    admin_id = Column(Integer, ForeignKey('adminstrators_shaqyru1.id'), nullable=True, index=True)  # ID of admin who created this project

    # Moderation fields
    moderation_status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    moderated_at = Column(DateTime, nullable=True)  # Timestamp when moderation action was taken
    moderated_by = Column(Integer, nullable=True)  # Admin ID who performed moderation
    moderation_comment = Column(Text, nullable=True)  # Optional comment/reason for rejection
    is_admin_created = Column(Boolean, default=False, nullable=False)  # True if created by administrator/super_admin


# Фотогалерея проекта
class ProjectGallery(Base):
    __tablename__ = "project_gallery"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects_multi_2.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())


# Участники голосовалки
class VotingParticipant(Base):
    __tablename__ = "voting_participants_multi"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer,  nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)  # YouTube ссылка

    # Социальные сети
    instagram_url = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)

    # Статистика
    votes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


# Голоса пользователей
class Vote(Base):
    __tablename__ = "votes_"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer,  nullable=False)
    participant_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)  # ID пользователя из таблицы users_
    user_phone = Column(String(20), nullable=False)  # Для дополнительной проверки
    created_at = Column(DateTime, default=func.now())


# Заявки на проекты типа "Прием заявок"
class ProjectApplication(Base):
    __tablename__ = "project_applications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects_multi_2.id"), nullable=False)

    # Данные заявителя
    phone_number = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    document_url = Column(String(500), nullable=True)  # Загруженный документ

    # Дополнительные поля (могут понадобиться)
    applicant_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Статус заявки
    status = Column(String(50), default="pending")  # pending, approved, rejected
    admin_comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)  # ID админа, который рассмотрел


# Результаты голосования (можно использовать для статистики)
class VotingResults(Base):
    __tablename__ = "voting_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects_multi_2.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("voting_participants_multi.id"), nullable=False)
    participant_name = Column(String(255), nullable=False)
    votes_count = Column(Integer, default=0)
    percentage = Column(String(10), nullable=True)  # Процент от общего числа голосов
    position = Column(Integer, nullable=True)  # Место в рейтинге
    calculated_at = Column(DateTime, default=func.now())


# Custom Form Templates for Application Projects
class ProjectFormTemplate(Base):
    __tablename__ = "project_form_templates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects_multi_2.id"), unique=True, nullable=False, index=True)
    
    # Multilingual titles and descriptions
    title_kz = Column(String(255), nullable=False)
    title_ru = Column(String(255), nullable=False)
    description_kz = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    
    # Form field definitions stored as JSONB array
    # Structure: [{"id": "uuid", "type": "text|textarea|dropdown|...", "label_kz": "...", "label_ru": "...", ...}]
    fields = Column(JSONB, nullable=False, default=list)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# Form Submissions from Participants
class ProjectFormSubmission(Base):
    __tablename__ = "project_form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects_multi_2.id"), nullable=False, index=True)
    form_template_id = Column(Integer, ForeignKey("project_form_templates.id"), nullable=False)
    
    # Submitter information
    user_id = Column(Integer, ForeignKey("users_2026_12.id"), nullable=True)  # If authenticated
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    applicant_name = Column(String(255), nullable=True)
    
    # Form responses stored as JSONB
    # Structure: {"field_uuid_1": "response", "field_uuid_2": ["multiple", "values"], ...}
    responses = Column(JSONB, nullable=False, default=dict)
    
    # Submission status
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, approved, rejected
    admin_comment = Column(Text, nullable=True)
    
    # Review tracking
    reviewed_by = Column(Integer, ForeignKey("adminstrators_shaqyru1.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    class Config:
        indexes = [
            {'fields': ['project_id', 'status']},
            {'fields': ['project_id', 'submitted_at']},
        ]