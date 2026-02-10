from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.oauth2 import get_current_user
from app import models
from app.user_telegram_models import UserTelegramLink
from app.user_telegram_schemas import (
    ConfirmLinkRequest,
    ConfirmLinkResponse,
    GenerateLinkResponse,
    MessageResponse,
    TelegramStatusResponse,
)
from config import get_settings

router = APIRouter(
    prefix="/api/v2/telegram",
    tags=["User Telegram"],
)


@router.post("/generate-link", response_model=GenerateLinkResponse)
def generate_link(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    bot_username = settings.TELEGRAM_BOT_USERNAME
    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram bot is not configured",
        )

    link_record = (
        db.query(UserTelegramLink)
        .filter(UserTelegramLink.user_id == current_user.id)
        .first()
    )

    if link_record and link_record.is_linked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account is already linked",
        )

    if not link_record:
        link_record = UserTelegramLink(user_id=current_user.id)
        db.add(link_record)

    token = link_record.generate_link_token()
    db.commit()
    db.refresh(link_record)

    link_url = f"https://t.me/{bot_username}?start=link_{token}"

    return GenerateLinkResponse(
        link_url=link_url,
        token=token,
        expires_in_minutes=10,
    )


@router.post("/confirm-link", response_model=ConfirmLinkResponse)
def confirm_link(
    request: ConfirmLinkRequest,
    x_bot_secret: str = Header(..., alias="X-Bot-Secret"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if x_bot_secret != settings.TELEGRAM_BOT_LINK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bot secret",
        )

    link_record = (
        db.query(UserTelegramLink)
        .filter(UserTelegramLink.link_token == request.token)
        .first()
    )

    if not link_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired token",
        )

    if not link_record.is_token_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired",
        )

    # Check if this telegram_chat_id is already linked to another user
    existing = (
        db.query(UserTelegramLink)
        .filter(
            UserTelegramLink.telegram_chat_id == request.telegram_chat_id,
            UserTelegramLink.is_linked == True,
            UserTelegramLink.id != link_record.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Telegram account is already linked to another user",
        )

    link_record.mark_linked(
        chat_id=request.telegram_chat_id,
        username=request.telegram_username,
        first_name=request.telegram_first_name,
    )
    db.commit()

    return ConfirmLinkResponse(
        success=True,
        message="Telegram account linked successfully",
        user_id=link_record.user_id,
    )


@router.get("/status", response_model=TelegramStatusResponse)
def get_telegram_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link_record = (
        db.query(UserTelegramLink)
        .filter(UserTelegramLink.user_id == current_user.id)
        .first()
    )

    if not link_record:
        return TelegramStatusResponse(is_linked=False)

    return TelegramStatusResponse(
        is_linked=link_record.is_linked,
        telegram_username=link_record.telegram_username if link_record.is_linked else None,
        telegram_first_name=link_record.telegram_first_name if link_record.is_linked else None,
        linked_at=link_record.linked_at,
        has_pending_token=link_record.link_token is not None and link_record.is_token_valid(),
    )


@router.delete("/unlink", response_model=MessageResponse)
def unlink_telegram(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link_record = (
        db.query(UserTelegramLink)
        .filter(UserTelegramLink.user_id == current_user.id)
        .first()
    )

    if not link_record or not link_record.is_linked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Telegram account is linked",
        )

    link_record.unlink()
    db.commit()

    return MessageResponse(message="Telegram account unlinked successfully")
