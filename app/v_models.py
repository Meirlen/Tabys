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

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base
import enum



# Модель волонтёра БЕЗ foreign key
class Volunteer(Base):
    __tablename__ = "volunteers_"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)  # БЕЗ ForeignKey!

    # Основные данные
    full_name = Column(String, nullable=False)
    corps_id = Column(Integer, nullable=False)
    direction_id = Column(Integer, nullable=False)

    # Статус волонтёра (простая строка)
    volunteer_status = Column(String, nullable=False, default="VOLUNTEER")

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Volunteer {self.full_name} - {self.volunteer_status}>"
