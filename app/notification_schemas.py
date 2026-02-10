from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NotificationCreate(BaseModel):
    user_id: int
    title_kz: str
    title_ru: str
    message_kz: Optional[str] = None
    message_ru: Optional[str] = None
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    admin_comment: Optional[str] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title_kz: str
    title_ru: str
    message_kz: Optional[str] = None
    message_ru: Optional[str] = None
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    is_read: bool
    admin_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class AdminNotificationCreate(BaseModel):
    """Schema for admin to create custom notifications"""
    user_ids: List[int]  # List of user IDs to send to (or empty for all users)
    title_kz: str
    title_ru: str
    message_kz: Optional[str] = None
    message_ru: Optional[str] = None
    notification_type: str = "custom_message"
    send_to_all: bool = False  # If True, send to all users


class AdminNotificationBulkResponse(BaseModel):
    message: str
    notifications_created: int
    failed_users: List[int] = []
