from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float,Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from typing import List, Optional
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary,Date
from sqlalchemy.sql import func

from app.database import Base
from pydantic_settings import BaseSettings
from sqlalchemy import Column, Integer, String, JSON

from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from sqlalchemy.ext.declarative import declarative_base
import enum

# app/v_models.py
# Модели для волонтёров БЕЗ foreign key и relationship
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, Float
from sqlalchemy.sql import func
from app.database import Base
import enum

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base
import enum



# Модель волонтёра БЕЗ foreign key
class Volunteer(Base):
    __tablename__ = "volunteers_13"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)  # БЕЗ ForeignKey!

    # Основные данные
    ava_url = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    bio =  Column(String, nullable=False)
    age =  Column(Integer, nullable=False)
    direction_id = Column(Integer, nullable=False)

    # Статус волонтёра (простая строка)
    volunteer_status = Column(String, nullable=False, default="VOLUNTEER")

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Volunteer {self.full_name} - {self.volunteer_status}>"


# === МЕРОПРИЯТИЯ ===
class VolunteerEvent(Base):
    __tablename__ = "volunteer_events_"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    title_kz = Column(String)
    description = Column(Text)
    description_kz = Column(Text)

    # Детали мероприятия
    event_date = Column(DateTime, nullable=False)
    location = Column(String)
    direction_id = Column(Integer)  # Ссылка на направление

    # V-coins
    v_coins_reward = Column(Integer, default=10)
    photo_bonus = Column(Integer, default=5)  # Бонус за фото в отчете

    # Роли и квоты
    required_volunteers = Column(Integer, default=0)
    required_team_leaders = Column(Integer, default=0)
    required_supervisors = Column(Integer, default=0)

    # Статус
    is_active = Column(Boolean, default=True)
    status = Column(String, default="upcoming")  # upcoming, ongoing, completed, cancelled

    # WhatsApp
    whatsapp_group_link = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# === ЗАЯВКИ НА МЕРОПРИЯТИЯ ===
class EventApplication(Base):
    __tablename__ = "event_applications2"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False)
    volunteer_id = Column(Integer, nullable=False)  # ID из таблицы volunteers_

    # Роль
    applied_role = Column(String, default="VOLUNTEER")  # VOLUNTEER, TEAM_LEADER, SUPERVISOR

    # Статус заявки
    status = Column(String, default="pending")  # pending, approved, rejected, cancelled

    # Присутствие
    attended = Column(Boolean, default=False)
    missed = Column(Boolean, default=False)

    # Отчет
    report_submitted = Column(Boolean, default=False)
    report_text = Column(Text)
    report_photo_url = Column(String)

    # V-coins
    v_coins_earned = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# === ЗАДАЧИ К МЕРОПРИЯТИЯМ (Чек-лист) ===
class EventTask(Base):
    __tablename__ = "event_tasks"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False)

    title = Column(String, nullable=False)
    title_kz = Column(String)
    description = Column(Text)

    # Для какой роли задача
    for_role = Column(String, default="VOLUNTEER")  # VOLUNTEER, TEAM_LEADER, SUPERVISOR, ALL

    is_required = Column(Boolean, default=True)
    v_coins_bonus = Column(Integer, default=0)  # Доп баллы за выполнение

    created_at = Column(DateTime(timezone=True), server_default=func.now())


from datetime import datetime
# === ВЫПОЛНЕНИЕ ЗАДАЧ ===
class TaskCompletion(Base):
    __tablename__ = "task_completions_2"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("event_tasks.id"))
    application_id = Column(Integer, ForeignKey("event_applications2.id"))

    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # ========== ДОБАВЬ ЭТИ ПОЛЯ ==========
    report_text = Column(Text, nullable=True)  # Текст отчёта по задаче
    report_photo_url = Column(String, nullable=True)  # Фото отчёта
    report_status = Column(String, default="not_submitted")  # not_submitted, pending, approved, rejected
    admin_comment = Column(Text, nullable=True)  # Комментарий админа
    v_coins_earned = Column(Integer, default=0)  # Сколько получил за задачу

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# === V-COINS ИСТОРИЯ ===
class VCoinTransaction(Base):
    __tablename__ = "vcoin_transactions"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, nullable=False)

    amount = Column(Integer, nullable=False)  # Может быть отрицательным (трата)
    transaction_type = Column(String)  # earned, spent, bonus, penalty

    description = Column(String)
    description_kz = Column(String)

    # Связь с источником
    event_id = Column(Integer)
    benefit_id = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# === БАЛАНС V-COINS ===
class VolunteerBalance(Base):
    __tablename__ = "volunteer_balances"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, unique=True, nullable=False)

    total_earned = Column(Integer, default=0)  # Всего заработано
    current_balance = Column(Integer, default=0)  # Текущий баланс
    total_spent = Column(Integer, default=0)  # Всего потрачено

    # Статистика
    events_participated = Column(Integer, default=0)
    events_missed = Column(Integer, default=0)  # Счетчик пропусков

    # Статус (цветовой индикатор)
    warning_level = Column(String, default="green")  # green, yellow, orange, red

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# === ПЛЮШКИ/БОНУСЫ ===
class Benefit(Base):
    __tablename__ = "volunteer_benefits"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    title_kz = Column(String)
    description = Column(Text)
    description_kz = Column(Text)

    v_coins_cost = Column(Integer, nullable=False)

    # Доступность по статусу
    min_status = Column(String, default="VOLUNTEER")  # Минимальный статус для доступа

    category = Column(String)  # professional_video, culture, recommendation, etc
    icon_url = Column(String)

    is_active = Column(Boolean, default=True)
    stock_limit = Column(Integer)  # Ограничение количества (null = безлимит)
    stock_available = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# === ПОКУПКИ ПЛЮШЕК ===
class BenefitPurchase(Base):
    __tablename__ = "benefit_purchases"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, nullable=False)
    benefit_id = Column(Integer, nullable=False)

    v_coins_spent = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, approved, completed, cancelled

    # Для рекомендательных писем
    letter_type = Column(String)  # mrc, uvmp, deputy_akim

    admin_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime)


# === ЗАПРОСЫ НА ПОВЫШЕНИЕ ===
class PromotionRequest(Base):
    __tablename__ = "promotion_requests"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, nullable=False)

    current_status = Column(String, nullable=False)
    requested_status = Column(String, nullable=False)

    status = Column(String, default="pending")  # pending, approved, rejected

    # V-coins на момент запроса
    v_coins_at_request = Column(Integer)

    admin_comment = Column(Text)
    reviewed_by = Column(Integer)  # ID админа
    reviewed_at = Column(DateTime)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# === БЕЙДЖИ/ДОСТИЖЕНИЯ ===
class Achievement(Base):
    __tablename__ = "volunteer_achievements"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    title_kz = Column(String)
    description = Column(Text)

    icon_url = Column(String)
    badge_color = Column(String)  # green, blue, purple, gold

    # Условия получения
    condition_type = Column(String)  # events_count, v_coins, status_reached, etc
    condition_value = Column(Integer)

    is_active = Column(Boolean, default=True)


# === ПОЛУЧЕННЫЕ БЕЙДЖИ ===
class VolunteerAchievement(Base):
    __tablename__ = "volunteer_achievements_earned"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, nullable=False)
    achievement_id = Column(Integer, nullable=False)

    earned_at = Column(DateTime(timezone=True), server_default=func.now())


# Добавьте ЭТИ МОДЕЛИ в v_models.py в самом начале после импортов:

# === КОРПУСА ===
class Corps(Base):
    __tablename__ = "volunteer_corps"

    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String, nullable=False)
    name_kz = Column(String)
    name_en = Column(String)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# === НАПРАВЛЕНИЯ ===
class Direction(Base):
    __tablename__ = "volunteer_directions"

    id = Column(Integer, primary_key=True, index=True)
    name_ru = Column(String, nullable=False)
    name_kz = Column(String)
    name_en = Column(String)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Добавь эту модель в твой v_models.py

# === ТРЕБОВАНИЯ ДЛЯ СТАТУСОВ ===
class StatusRequirement(Base):
    """
    Хранит требования V-coins для каждого статуса волонтёра
    """
    __tablename__ = "status_requirements"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, unique=True, nullable=False)  # VOLUNTEER, TEAM_LEADER, SUPERVISOR, COORDINATOR

    # Название статуса
    title_ru = Column(String, nullable=False)
    title_kz = Column(String, nullable=False)
    level = Column(Integer, nullable=False)  # 1, 2, 3, 4

    # Требования для ПОЛУЧЕНИЯ этого статуса
    v_coins_required = Column(Integer, default=0)  # Сколько нужно V-coins

    # Описание преимуществ статуса
    benefits_ru = Column(Text)  # JSON или текст через запятую
    benefits_kz = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<StatusRequirement {self.status}: {self.v_coins_required} V-coins>"