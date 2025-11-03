# v_schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# === EVENT SCHEMAS ===
class EventBase(BaseModel):
    title: str
    title_kz: Optional[str] = None
    description: Optional[str] = None
    description_kz: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None
    direction_id: Optional[int] = None
    v_coins_reward: int = 10
    photo_bonus: int = 5
    whatsapp_group_link: Optional[str] = None


class EventCreate(EventBase):
    required_volunteers: int = 0
    required_team_leaders: int = 0
    required_supervisors: int = 0


class EventResponse(EventBase):
    id: int
    status: str
    is_active: bool
    required_volunteers: int
    required_team_leaders: int
    required_supervisors: int
    created_at: datetime

    class Config:
        from_attributes = True


# === APPLICATION SCHEMAS ===
class EventApplicationCreate(BaseModel):
    role: str = "VOLUNTEER"

# Добавь эту схему в начало файла (или в v_schemas.py)
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    for_role: str = "ALL"
    is_required: bool = True
    v_coins_bonus: int = 0


class EventApplicationResponse(BaseModel):
    id: int
    event_id: int
    volunteer_id: int
    applied_role: str
    status: str
    attended: Optional[bool] = None
    missed: Optional[bool] = None
    report_submitted: Optional[bool] = None
    v_coins_earned: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# === REPORT SCHEMAS ===
class ReportSubmit(BaseModel):
    report_text: Optional[str] = None


# === BENEFIT SCHEMAS ===
class BenefitResponse(BaseModel):
    id: int
    title: str
    title_kz: Optional[str]
    description: Optional[str]
    v_coins_cost: int
    min_status: str
    category: Optional[str]
    icon_url: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class BenefitPurchaseCreate(BaseModel):
    benefit_id: int


# === PROMOTION SCHEMAS ===
class PromotionRequestCreate(BaseModel):
    requested_status: str