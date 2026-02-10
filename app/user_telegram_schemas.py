from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConfirmLinkRequest(BaseModel):
    token: str
    telegram_chat_id: str
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None


class GenerateLinkResponse(BaseModel):
    link_url: str
    token: str
    expires_in_minutes: int = 10


class ConfirmLinkResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None


class TelegramStatusResponse(BaseModel):
    is_linked: bool
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    linked_at: Optional[datetime] = None
    has_pending_token: bool = False


class MessageResponse(BaseModel):
    message: str
