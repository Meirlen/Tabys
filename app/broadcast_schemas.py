"""
Telegram Broadcast Pydantic Schemas
Request/Response models for Broadcast API endpoints
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from app.broadcast_models import BroadcastTargetAudience, BroadcastStatus, DeliveryStatus


# Request Schemas

class BroadcastCreateRequest(BaseModel):
    """Request to create new broadcast"""
    title: str = Field(..., min_length=1, max_length=255, description="Broadcast title")
    message: str = Field(..., min_length=1, description="Message content (supports HTML)")
    target_audience: BroadcastTargetAudience = Field(
        default=BroadcastTargetAudience.ALL_TELEGRAM_USERS,
        description="Target audience filter"
    )
    target_role: Optional[str] = Field(None, description="Specific role (if target_audience=BY_ROLE)")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule for later (optional)")

    @validator('target_role')
    def validate_target_role(cls, v, values):
        """Ensure target_role is provided when target_audience is BY_ROLE"""
        if values.get('target_audience') == BroadcastTargetAudience.BY_ROLE and not v:
            raise ValueError('target_role is required when target_audience is BY_ROLE')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Важное объявление",
                "message": "<b>Уважаемые пользователи!</b>\n\nИнформируем вас о важном обновлении...",
                "target_audience": "admins_only",
                "target_role": None,
                "scheduled_at": None
            }
        }


class BroadcastUpdateRequest(BaseModel):
    """Request to update broadcast (only draft broadcasts)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    message: Optional[str] = Field(None, min_length=1)
    target_audience: Optional[BroadcastTargetAudience] = None
    target_role: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class BroadcastSendRequest(BaseModel):
    """Request to send broadcast immediately"""
    send_now: bool = Field(default=True, description="Send immediately (ignore scheduled_at)")


# Response Schemas

class BroadcastDeliveryResponse(BaseModel):
    """Individual delivery status"""
    id: int
    telegram_user_id: str
    status: DeliveryStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class BroadcastResponse(BaseModel):
    """Broadcast details"""
    id: int
    title: str
    message: str
    target_audience: BroadcastTargetAudience
    target_role: Optional[str]
    status: BroadcastStatus

    # Statistics
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int

    # Metadata
    created_by: int
    created_at: datetime
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BroadcastListResponse(BaseModel):
    """List of broadcasts with pagination"""
    items: List[BroadcastResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BroadcastStatsResponse(BaseModel):
    """Broadcast delivery statistics"""
    broadcast_id: int
    title: str
    status: BroadcastStatus
    total_recipients: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    pending_count: int
    success_rate: float  # Percentage of successful deliveries
    created_at: datetime
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True
    data: Optional[dict] = None
