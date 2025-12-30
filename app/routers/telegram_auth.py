"""
Telegram Bot Authentication Router
Provides OTP generation, verification, and session management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app import models
from app.telegram_otp_models import TelegramOTP, TelegramSession
from app.telegram_otp_schemas import (
    OTPGenerateRequest,
    OTPGenerateResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
    TelegramLogoutRequest,
    SessionRestoreRequest,
    OTPRevokeRequest,
    OTPStatusResponse,
    TelegramSessionResponse,
    TelegramSessionListResponse,
    MessageResponse,
)
from app.oauth2 import get_current_admin, create_admin_access_token
from app.rbac.middleware import require_role
from app.rbac.roles import Role

router = APIRouter(
    prefix="/api/v1/telegram-auth",
    tags=["Telegram Authentication"]
)


@router.post("/generate-otp", response_model=OTPGenerateResponse)
def generate_otp(
    request: OTPGenerateRequest,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Generate OTP token for Telegram bot login

    **Authentication Required**: Backend admin must be logged in

    **Flow**:
    1. Authenticated admin calls this endpoint
    2. Backend generates unique OTP token
    3. Admin copies the `/login <OTP>` command
    4. Admin sends command to Telegram bot
    5. Bot verifies OTP via `/verify-otp` endpoint

    **Security**:
    - OTP expires in 5-60 minutes (default: 10)
    - One-time use only
    - Cryptographically secure random generation
    - Cannot be reused or extended
    """
    # Clean up expired OTPs for this admin
    db.query(TelegramOTP).filter(
        TelegramOTP.admin_id == current_admin.id,
        TelegramOTP.is_used == False,
        TelegramOTP.is_revoked == False,
        TelegramOTP.expires_at < datetime.utcnow()
    ).update({"is_revoked": True})

    # Generate unique OTP token
    max_attempts = 10
    for _ in range(max_attempts):
        token = TelegramOTP.generate_token()
        existing = db.query(TelegramOTP).filter(TelegramOTP.token == token).first()
        if not existing:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique OTP token"
        )

    # Create OTP record
    expires_at = TelegramOTP.get_expiry_time(minutes=request.expires_in_minutes)
    otp_record = TelegramOTP(
        token=token,
        admin_id=current_admin.id,
        expires_at=expires_at,
        ip_address=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("User-Agent") if http_request else None
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    # Calculate remaining seconds
    expires_in_seconds = int((expires_at - datetime.utcnow()).total_seconds())

    return OTPGenerateResponse(
        otp_token=token,
        command=f"/login {token}",
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds
    )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP token and create Telegram session

    **Called by**: Telegram bot only (no authentication required)

    **Flow**:
    1. Bot receives `/login <OTP>` from user
    2. Bot calls this endpoint with OTP + telegram_user_id
    3. Backend validates OTP and creates session binding
    4. Backend returns JWT token for bot to store in Redis
    5. OTP is immediately invalidated

    **Security**:
    - OTP must be valid (not used, not revoked, not expired)
    - One telegram_user_id can only bind to one admin_id
    - JWT token follows existing backend expiry rules
    """
    # Find OTP record
    otp_record = db.query(TelegramOTP).filter(
        TelegramOTP.token == request.otp_token
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP token"
        )

    # Validate OTP
    if not otp_record.is_valid():
        reasons = []
        if otp_record.is_used:
            reasons.append("already used")
        if otp_record.is_revoked:
            reasons.append("revoked")
        if datetime.utcnow() > otp_record.expires_at:
            reasons.append("expired")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OTP token is invalid: {', '.join(reasons)}"
        )

    # Get admin from OTP
    admin = db.query(models.Admin).filter(models.Admin.id == otp_record.admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin account not found"
        )

    # Check if Telegram user already has a session
    existing_session = db.query(TelegramSession).filter(
        TelegramSession.telegram_user_id == request.telegram_user_id
    ).first()

    session_created = False

    if existing_session:
        # Update existing session
        existing_session.admin_id = admin.id
        existing_session.telegram_username = request.telegram_username
        existing_session.telegram_first_name = request.telegram_first_name
        existing_session.telegram_last_name = request.telegram_last_name
        existing_session.is_active = True
        existing_session.update_activity()
    else:
        # Create new session
        new_session = TelegramSession(
            telegram_user_id=request.telegram_user_id,
            telegram_username=request.telegram_username,
            telegram_first_name=request.telegram_first_name,
            telegram_last_name=request.telegram_last_name,
            admin_id=admin.id,
            is_active=True
        )
        db.add(new_session)
        session_created = True

    # Mark OTP as used
    otp_record.mark_used()

    db.commit()

    # Generate JWT token (same as backend admin login)
    admin_role = admin.role.value if hasattr(admin.role, 'value') else admin.role
    access_token = create_admin_access_token(
        data={
            "admin_id": admin.id,
            "user_type": "admin",
            "role": admin_role
        }
    )

    return OTPVerifyResponse(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.id,
        role=admin_role,
        telegram_user_id=request.telegram_user_id,
        session_created=session_created
    )


@router.post("/logout", response_model=MessageResponse)
def telegram_logout(
    request: TelegramLogoutRequest,
    db: Session = Depends(get_db)
):
    """
    Logout Telegram bot session

    **Called by**: Telegram bot when user sends `/logout`

    Deactivates the session binding. Bot should also clear Redis session.
    """
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_user_id == request.telegram_user_id,
        TelegramSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )

    session.deactivate()
    db.commit()

    return MessageResponse(
        message="Telegram session logged out successfully",
        success=True
    )


@router.post("/restore-session", response_model=OTPVerifyResponse)
def restore_session(
    request: SessionRestoreRequest,
    db: Session = Depends(get_db)
):
    """
    Restore session after bot restart

    **Called by**: Telegram bot when it needs to restore a session
    from the database after a restart (in-memory cache was cleared)

    **Flow**:
    1. Bot checks if user has an active session in the database
    2. If active session exists, backend generates new JWT token
    3. Bot caches the session locally

    **Security**:
    - Only restores active sessions
    - Updates last_activity timestamp
    - Generates fresh JWT token
    """
    # Find active session for this Telegram user
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_user_id == request.telegram_user_id,
        TelegramSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found for this Telegram user"
        )

    # Get the admin associated with this session
    admin = db.query(models.Admin).filter(models.Admin.id == session.admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin account not found"
        )

    # Update last activity
    session.update_activity()
    db.commit()

    # Generate fresh JWT token
    admin_role = admin.role.value if hasattr(admin.role, 'value') else admin.role
    access_token = create_admin_access_token(
        data={
            "admin_id": admin.id,
            "user_type": "admin",
            "role": admin_role
        }
    )

    return OTPVerifyResponse(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.id,
        role=admin_role,
        telegram_user_id=request.telegram_user_id,
        session_created=False  # Session was restored, not created
    )


@router.post("/revoke-otp", response_model=MessageResponse)
def revoke_otp(
    request: OTPRevokeRequest,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke OTP token (admin action)

    **Authentication Required**: Backend admin

    Allows admin to invalidate their own OTP tokens before they expire.
    """
    otp_record = db.query(TelegramOTP).filter(
        TelegramOTP.token == request.otp_token,
        TelegramOTP.admin_id == current_admin.id
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OTP token not found or does not belong to you"
        )

    if otp_record.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke OTP that has already been used"
        )

    otp_record.revoke()
    db.commit()

    return MessageResponse(
        message="OTP token revoked successfully",
        success=True
    )


@router.get("/my-otps", response_model=List[OTPStatusResponse])
def get_my_otps(
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all OTP tokens for current admin

    **Authentication Required**: Backend admin

    Returns list of OTP tokens (active and expired) for audit purposes.
    """
    otps = db.query(TelegramOTP).filter(
        TelegramOTP.admin_id == current_admin.id
    ).order_by(TelegramOTP.created_at.desc()).limit(50).all()

    return [
        OTPStatusResponse(
            token=otp.token,
            is_used=otp.is_used,
            is_revoked=otp.is_revoked,
            is_expired=datetime.utcnow() > otp.expires_at,
            is_valid=otp.is_valid(),
            created_at=otp.created_at,
            expires_at=otp.expires_at,
            used_at=otp.used_at
        )
        for otp in otps
    ]


@router.get("/sessions", response_model=TelegramSessionListResponse)
def get_telegram_sessions(
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Get all active Telegram sessions

    **Authentication Required**: Administrator or Super Admin

    Returns list of all Telegram bot sessions for monitoring.
    """
    sessions = db.query(TelegramSession).filter(
        TelegramSession.is_active == True
    ).order_by(TelegramSession.last_activity_at.desc()).all()

    session_responses = []
    for session in sessions:
        admin = db.query(models.Admin).filter(models.Admin.id == session.admin_id).first()
        if admin:
            admin_role = admin.role.value if hasattr(admin.role, 'value') else admin.role
            session_responses.append(
                TelegramSessionResponse(
                    telegram_user_id=session.telegram_user_id,
                    telegram_username=session.telegram_username,
                    admin_id=session.admin_id,
                    admin_name=admin.name,
                    admin_role=admin_role,
                    is_active=session.is_active,
                    created_at=session.created_at,
                    last_activity_at=session.last_activity_at
                )
            )

    return TelegramSessionListResponse(
        sessions=session_responses,
        total=len(session_responses)
    )


@router.delete("/sessions/{telegram_user_id}", response_model=MessageResponse)
def revoke_telegram_session(
    telegram_user_id: str,
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Revoke Telegram session (admin action)

    **Authentication Required**: Administrator or Super Admin

    Forcefully deactivates a Telegram bot session.
    """
    session = db.query(TelegramSession).filter(
        TelegramSession.telegram_user_id == telegram_user_id,
        TelegramSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found"
        )

    session.deactivate()
    db.commit()

    return MessageResponse(
        message=f"Telegram session for user {telegram_user_id} revoked successfully",
        success=True
    )
