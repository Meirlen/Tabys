"""
Telegram OTP Pydantic Schemas
Request/Response models for OTP API endpoints
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


# Request Schemas

class OTPGenerateRequest(BaseModel):
    """Request to generate new OTP token"""
    expires_in_minutes: int = Field(default=10, ge=5, le=60, description="OTP expiry time in minutes (5-60)")


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP token from Telegram bot"""
    otp_token: str = Field(..., min_length=8, max_length=8, description="8-character OTP token")
    telegram_user_id: str = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, max_length=255)
    telegram_first_name: Optional[str] = Field(None, max_length=255)
    telegram_last_name: Optional[str] = Field(None, max_length=255)

    @validator('otp_token')
    def otp_uppercase(cls, v):
        """Ensure OTP is uppercase"""
        return v.upper().strip()

    @validator('telegram_user_id')
    def telegram_id_valid(cls, v):
        """Validate Telegram user ID is numeric"""
        if not v.isdigit():
            raise ValueError('telegram_user_id must be numeric')
        return v


class TelegramLogoutRequest(BaseModel):
    """Request to logout Telegram session"""
    telegram_user_id: str = Field(..., description="Telegram user ID")

    @validator('telegram_user_id')
    def telegram_id_valid(cls, v):
        if not v.isdigit():
            raise ValueError('telegram_user_id must be numeric')
        return v


class SessionRestoreRequest(BaseModel):
    """Request to restore session after bot restart"""
    telegram_user_id: str = Field(..., description="Telegram user ID")

    @validator('telegram_user_id')
    def telegram_id_valid(cls, v):
        if not v.isdigit():
            raise ValueError('telegram_user_id must be numeric')
        return v


class OTPRevokeRequest(BaseModel):
    """Request to revoke OTP token (admin action)"""
    otp_token: str = Field(..., min_length=8, max_length=8)

    @validator('otp_token')
    def otp_uppercase(cls, v):
        return v.upper().strip()


# Response Schemas

class OTPGenerateResponse(BaseModel):
    """Response after generating OTP"""
    otp_token: str = Field(..., description="8-character OTP token")
    command: str = Field(..., description="Command to send to Telegram bot")
    expires_at: datetime = Field(..., description="OTP expiration timestamp (UTC)")
    expires_in_seconds: int = Field(..., description="Seconds until expiry")

    class Config:
        json_schema_extra = {
            "example": {
                "otp_token": "A7B9C3D5",
                "command": "/login A7B9C3D5",
                "expires_at": "2025-12-28T10:15:00Z",
                "expires_in_seconds": 600
            }
        }


class OTPVerifyResponse(BaseModel):
    """Response after successful OTP verification"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")
    admin_id: int = Field(..., description="Backend admin ID")
    role: str = Field(..., description="Admin role")
    telegram_user_id: str = Field(..., description="Telegram user ID")
    session_created: bool = Field(..., description="Whether new session was created")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "admin_id": 42,
                "role": "administrator",
                "telegram_user_id": "123456789",
                "session_created": True
            }
        }


class OTPStatusResponse(BaseModel):
    """OTP token status information"""
    token: str
    is_used: bool
    is_revoked: bool
    is_expired: bool
    is_valid: bool
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime]

    class Config:
        from_attributes = True


class TelegramSessionResponse(BaseModel):
    """Telegram session information"""
    telegram_user_id: str
    telegram_username: Optional[str]
    admin_id: int
    admin_name: str
    admin_role: str
    is_active: bool
    created_at: datetime
    last_activity_at: datetime

    class Config:
        from_attributes = True


class TelegramSessionListResponse(BaseModel):
    """List of active Telegram sessions"""
    sessions: list[TelegramSessionResponse]
    total: int


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
