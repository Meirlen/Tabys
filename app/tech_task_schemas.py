from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date


# ── Tech Task Schemas ──────────────────────────────────────────────────────────

class TechTaskCreate(BaseModel):
    title_kz: str
    title_ru: str
    description_kz: str
    description_ru: str
    category: str
    preferred_technologies: Optional[List[str]] = None
    field_of_application: Optional[str] = None
    deadline: Optional[date] = None
    budget_from: Optional[int] = None
    budget_to: Optional[int] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class TechTaskUpdate(BaseModel):
    title_kz: Optional[str] = None
    title_ru: Optional[str] = None
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    category: Optional[str] = None
    preferred_technologies: Optional[List[str]] = None
    field_of_application: Optional[str] = None
    deadline: Optional[date] = None
    budget_from: Optional[int] = None
    budget_to: Optional[int] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None


class TechTaskList(BaseModel):
    id: int
    title_kz: str
    title_ru: str
    description_kz: str
    description_ru: str
    category: str
    preferred_technologies: Optional[List[str]] = None
    field_of_application: Optional[str] = None
    deadline: Optional[date] = None
    budget_from: Optional[int] = None
    budget_to: Optional[int] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    user_id: int
    solutions_count: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


class TechTaskDetail(TechTaskList):
    updated_at: Optional[datetime] = None
    files: Optional[List["TechTaskFileResponse"]] = []


# ── Task File Schemas ──────────────────────────────────────────────────────────

class TechTaskFileResponse(BaseModel):
    id: int
    task_id: int
    file_path: str
    original_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Solution File Schemas ──────────────────────────────────────────────────────

class TechTaskSolutionFileResponse(BaseModel):
    id: int
    solution_id: int
    file_path: str
    original_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Solution Schemas ───────────────────────────────────────────────────────────

class TechTaskSolutionCreate(BaseModel):
    description_kz: str
    description_ru: str
    proposed_budget: Optional[int] = None
    proposed_timeline: Optional[str] = None


class TechTaskSolutionUpdate(BaseModel):
    description_kz: Optional[str] = None
    description_ru: Optional[str] = None
    proposed_budget: Optional[int] = None
    proposed_timeline: Optional[str] = None


class TechTaskSolutionResponse(BaseModel):
    id: int
    tech_task_id: int
    description_kz: str
    description_ru: str
    proposed_budget: Optional[int] = None
    proposed_timeline: Optional[str] = None
    user_id: int
    status: str
    files: Optional[List[TechTaskSolutionFileResponse]] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
