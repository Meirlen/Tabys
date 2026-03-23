from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class TechTask(Base):
    __tablename__ = "tech_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title_kz = Column(String(500), nullable=False)
    title_ru = Column(String(500), nullable=False)
    description_kz = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    preferred_technologies = Column(JSON, nullable=True)  # list of strings
    field_of_application = Column(String(255), nullable=True)
    deadline = Column(Date, nullable=True)
    budget_from = Column(Integer, nullable=True)
    budget_to = Column(Integer, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="collecting_offers", index=True)
    user_id = Column(Integer, ForeignKey("users_2026_12.id"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


class TechTaskSolution(Base):
    __tablename__ = "tech_task_solutions"

    id = Column(Integer, primary_key=True, index=True)
    tech_task_id = Column(Integer, ForeignKey("tech_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    description_kz = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)
    proposed_budget = Column(Integer, nullable=True)
    proposed_timeline = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users_2026_12.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


class TechTaskSolutionFile(Base):
    __tablename__ = "tech_task_solution_files"

    id = Column(Integer, primary_key=True, index=True)
    solution_id = Column(Integer, ForeignKey("tech_task_solutions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    original_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())


class TechTaskFile(Base):
    __tablename__ = "tech_task_files"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tech_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    original_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
