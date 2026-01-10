"""
Telegram Broadcasts Router
API endpoints for managing broadcasts to Telegram bot users
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from typing import List, Optional
import httpx

from app.database import get_db
from app import models
from app.broadcast_models import (
    Broadcast, BroadcastDelivery,
    BroadcastTargetAudience, BroadcastStatus, DeliveryStatus
)
from app.broadcast_schemas import (
    BroadcastCreateRequest, BroadcastUpdateRequest, BroadcastSendRequest,
    BroadcastResponse, BroadcastListResponse, BroadcastStatsResponse,
    BroadcastDeliveryResponse, MessageResponse
)
from app.telegram_otp_models import TelegramSession
from app.oauth2 import get_current_admin
from app.rbac.middleware import require_role
from app.rbac.roles import Role

router = APIRouter(
    prefix="/api/v1/broadcasts",
    tags=["Telegram Broadcasts"]
)


def get_target_users(
    db: Session,
    target_audience: BroadcastTargetAudience,
    target_role: Optional[str] = None
) -> List[str]:
    """
    Get list of telegram_user_ids based on target audience

    Args:
        db: Database session
        target_audience: Target audience filter (can be enum or string)
        target_role: Specific role (if BY_ROLE selected)

    Returns:
        List of telegram_user_ids to send broadcast to
    """
    # Convert string to enum if needed (when loaded from database)
    if isinstance(target_audience, str):
        try:
            target_audience = BroadcastTargetAudience(target_audience)
        except ValueError:
            # If invalid value, default to ACTIVE_SESSIONS
            target_audience = BroadcastTargetAudience.ACTIVE_SESSIONS

    query = db.query(TelegramSession.telegram_user_id).filter(
        TelegramSession.is_active == True
    )

    if target_audience == BroadcastTargetAudience.ACTIVE_SESSIONS:
        # Only active sessions (default filter above)
        pass

    elif target_audience == BroadcastTargetAudience.ADMINS_ONLY:
        # Only admin users (join with admins table)
        query = query.join(models.Admin, TelegramSession.admin_id == models.Admin.id).filter(
            models.Admin.role.in_([
                Role.SUPER_ADMIN,
                Role.ADMINISTRATOR,
                Role.GOVERNMENT,
                Role.NPO,
                Role.MSB,
                Role.VOLUNTEER_ADMIN
            ])
        )

    elif target_audience == BroadcastTargetAudience.BY_ROLE:
        # Filter by specific role
        if not target_role:
            raise ValueError("target_role must be specified for BY_ROLE audience")

        query = query.join(models.Admin, TelegramSession.admin_id == models.Admin.id).filter(
            models.Admin.role == target_role
        )

    elif target_audience == BroadcastTargetAudience.ALL_TELEGRAM_USERS:
        # All users with active sessions (default)
        pass

    # Get unique telegram_user_ids
    telegram_user_ids = [row[0] for row in query.distinct().all()]
    return telegram_user_ids


@router.post("/", response_model=BroadcastResponse)
def create_broadcast(
    request: BroadcastCreateRequest,
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Create new broadcast message

    **Permissions**: Super Admin or Administrator only

    Creates a broadcast in DRAFT status. Use /send endpoint to send it.
    """
    # Create broadcast
    broadcast = Broadcast(
        title=request.title,
        message=request.message,
        target_audience=request.target_audience.value if isinstance(request.target_audience, BroadcastTargetAudience) else request.target_audience,
        target_role=request.target_role,
        status=(BroadcastStatus.SCHEDULED if request.scheduled_at else BroadcastStatus.DRAFT).value,
        scheduled_at=request.scheduled_at,
        created_by=current_admin.id
    )

    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    return broadcast


@router.get("/", response_model=BroadcastListResponse)
def list_broadcasts(
    page: int = 1,
    page_size: int = 20,
    status: Optional[BroadcastStatus] = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all broadcasts with pagination

    **Permissions**: Any authenticated admin

    Returns broadcasts ordered by creation date (newest first).
    """
    query = db.query(Broadcast)

    # Filter by status if provided
    if status:
        query = query.filter(Broadcast.status == status)

    # Non-super admins can only see their own broadcasts
    if current_admin.role not in [Role.SUPER_ADMIN, Role.ADMINISTRATOR]:
        query = query.filter(Broadcast.created_by == current_admin.id)

    # Get total count
    total = query.count()

    # Pagination
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size

    broadcasts = query.order_by(desc(Broadcast.created_at)).offset(offset).limit(page_size).all()

    return BroadcastListResponse(
        items=broadcasts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{broadcast_id}", response_model=BroadcastResponse)
def get_broadcast(
    broadcast_id: int,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get single broadcast by ID"""
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Check permissions
    if (current_admin.role not in [Role.SUPER_ADMIN, Role.ADMINISTRATOR] and
            broadcast.created_by != current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return broadcast


@router.put("/{broadcast_id}", response_model=BroadcastResponse)
def update_broadcast(
    broadcast_id: int,
    request: BroadcastUpdateRequest,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update broadcast (only DRAFT or SCHEDULED broadcasts)

    **Permissions**: Creator or Super Admin/Administrator
    """
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Check permissions
    if (current_admin.role not in [Role.SUPER_ADMIN, Role.ADMINISTRATOR] and
            broadcast.created_by != current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Can only update draft or scheduled broadcasts
    if broadcast.status not in [BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update broadcast with status {broadcast.status}"
        )

    # Update fields
    if request.title is not None:
        broadcast.title = request.title
    if request.message is not None:
        broadcast.message = request.message
    if request.target_audience is not None:
        broadcast.target_audience = request.target_audience.value if isinstance(request.target_audience, BroadcastTargetAudience) else request.target_audience
    if request.target_role is not None:
        broadcast.target_role = request.target_role
    if request.scheduled_at is not None:
        broadcast.scheduled_at = request.scheduled_at
        broadcast.status = BroadcastStatus.SCHEDULED.value

    db.commit()
    db.refresh(broadcast)

    return broadcast


@router.post("/{broadcast_id}/send", response_model=MessageResponse)
async def send_broadcast(
    broadcast_id: int,
    background_tasks: BackgroundTasks,
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Send broadcast to target users

    **Permissions**: Super Admin or Administrator only

    Sends broadcast immediately and updates status to SENDING.
    Actual delivery happens in background.
    """
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Can only send draft or scheduled broadcasts
    if broadcast.status not in [BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send broadcast with status {broadcast.status}"
        )

    # Get target users
    try:
        telegram_user_ids = get_target_users(
            db,
            broadcast.target_audience,
            broadcast.target_role
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not telegram_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No users found matching the target audience"
        )

    # Create delivery records
    for telegram_user_id in telegram_user_ids:
        delivery = BroadcastDelivery(
            broadcast_id=broadcast.id,
            telegram_user_id=telegram_user_id,
            status=DeliveryStatus.PENDING.value
        )
        db.add(delivery)

    # Update broadcast status
    broadcast.status = BroadcastStatus.SENDING.value
    broadcast.total_recipients = len(telegram_user_ids)
    broadcast.sent_at = datetime.utcnow()

    db.commit()

    # Schedule background task to send messages
    background_tasks.add_task(process_broadcast_deliveries, broadcast_id)

    return MessageResponse(
        message=f"Broadcast queued for delivery to {len(telegram_user_ids)} users",
        success=True,
        data={
            "broadcast_id": broadcast_id,
            "total_recipients": len(telegram_user_ids)
        }
    )


@router.get("/{broadcast_id}/stats", response_model=BroadcastStatsResponse)
def get_broadcast_stats(
    broadcast_id: int,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get broadcast delivery statistics"""
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Calculate pending count
    pending_count = db.query(BroadcastDelivery).filter(
        BroadcastDelivery.broadcast_id == broadcast_id,
        BroadcastDelivery.status == DeliveryStatus.PENDING
    ).count()

    # Calculate success rate
    if broadcast.total_recipients > 0:
        success_rate = (broadcast.delivered_count / broadcast.total_recipients) * 100
    else:
        success_rate = 0.0

    return BroadcastStatsResponse(
        broadcast_id=broadcast.id,
        title=broadcast.title,
        status=broadcast.status,
        total_recipients=broadcast.total_recipients,
        sent_count=broadcast.sent_count,
        delivered_count=broadcast.delivered_count,
        read_count=broadcast.read_count,
        failed_count=broadcast.failed_count,
        pending_count=pending_count,
        success_rate=round(success_rate, 2),
        created_at=broadcast.created_at,
        sent_at=broadcast.sent_at,
        completed_at=broadcast.completed_at
    )


@router.delete("/{broadcast_id}", response_model=MessageResponse)
def delete_broadcast(
    broadcast_id: int,
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Delete broadcast (only DRAFT, SCHEDULED, or CANCELLED)

    **Permissions**: Super Admin or Administrator only
    """
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Can only delete draft, scheduled, or cancelled broadcasts
    if broadcast.status not in [BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED, BroadcastStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete broadcast with status {broadcast.status}. Cancel it first."
        )

    db.delete(broadcast)
    db.commit()

    return MessageResponse(
        message="Broadcast deleted successfully",
        success=True
    )


@router.post("/{broadcast_id}/retry", response_model=MessageResponse)
async def retry_broadcast(
    broadcast_id: int,
    background_tasks: BackgroundTasks,
    current_admin: models.Admin = Depends(require_role(Role.SUPER_ADMIN, Role.ADMINISTRATOR)),
    db: Session = Depends(get_db)
):
    """
    Retry sending a stuck or failed broadcast

    **Permissions**: Super Admin or Administrator only
    """
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broadcast not found"
        )

    # Reset status to SENDING
    broadcast.status = BroadcastStatus.SENDING.value
    db.commit()

    # Schedule background task to send messages
    background_tasks.add_task(process_broadcast_deliveries, broadcast_id)

    return MessageResponse(
        message=f"Broadcast {broadcast_id} retry queued",
        success=True,
        data={"broadcast_id": broadcast_id}
    )


# Background task to process deliveries
async def send_telegram_broadcast_message(
    telegram_user_id: str,
    message: str,
    broadcast_id: int,
    bot_token: str,
    broadcast_title: str = "",
    inline_keyboard: Optional[list] = None
) -> tuple[bool, Optional[str]]:
    """
    Send broadcast message via Telegram Bot API

    Args:
        telegram_user_id: Telegram user ID
        message: Message content (HTML formatted)
        broadcast_id: Broadcast ID
        bot_token: Telegram bot token
        broadcast_title: Title of broadcast (for conditional logic)
        inline_keyboard: Custom inline keyboard (optional)

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # Default inline keyboard - "Mark as read" button
        default_keyboard = {
            "inline_keyboard": [[
                {
                    "text": "✅ Отметить как прочитано",
                    "callback_data": f"broadcast:read:{broadcast_id}"
                }
            ]]
        }

        # Use custom keyboard if provided, otherwise use default
        reply_markup = inline_keyboard if inline_keyboard else default_keyboard

        payload = {
            "chat_id": telegram_user_id,
            "text": f"📢 <b>Объявление от администрации</b>\n\n{message}",
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        return True, None

    except Exception as e:
        return False, str(e)


async def process_broadcast_deliveries(broadcast_id: int):
    """
    Background task to send broadcast messages to users

    Sends messages directly via Telegram Bot API
    """
    import logging
    from app.database import SessionLocal
    from config import get_settings

    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting broadcast delivery for broadcast_id: {broadcast_id}")
    
    db = SessionLocal()

    try:
        broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
        if not broadcast:
            logger.error(f"Broadcast {broadcast_id} not found")
            return

        # Get bot token from settings
        bot_token = settings.telegram_bot_token if hasattr(settings, 'telegram_bot_token') else None
        if not bot_token:
            # Bot token not configured, mark as failed
            logger.error(f"Telegram bot token not configured")
            broadcast.status = BroadcastStatus.FAILED.value
            db.commit()
            return

        logger.info(f"Using bot token: {bot_token[:10]}... for broadcast {broadcast_id}")

        # Get pending deliveries
        deliveries = db.query(BroadcastDelivery).filter(
            BroadcastDelivery.broadcast_id == broadcast_id,
            BroadcastDelivery.status == DeliveryStatus.PENDING
        ).all()

        logger.info(f"Found {len(deliveries)} pending deliveries for broadcast {broadcast_id}")

        # Check if this is a moderation notification (by title)
        is_moderation_notification = "модерация" in broadcast.title.lower() or "moderation" in broadcast.title.lower()

        # Prepare inline keyboard for moderation notifications
        inline_keyboard = None
        if is_moderation_notification:
            from app.moderation_notification_config import CRM_MODERATION_URL, BUTTON_TEXT
            inline_keyboard = {
                "inline_keyboard": [[
                    {
                        "text": BUTTON_TEXT,
                        "url": CRM_MODERATION_URL
                    }
                ]]
            }
            logger.info(f"Moderation notification detected, using URL button to {CRM_MODERATION_URL}")

        sent_count = 0
        failed_count = 0

        # Send messages with rate limiting (30 messages per second max)
        for delivery in deliveries:
            logger.info(f"Sending message to telegram_user_id: {delivery.telegram_user_id}")

            success, error_msg = await send_telegram_broadcast_message(
                delivery.telegram_user_id,
                broadcast.message,
                broadcast.id,
                bot_token,
                broadcast_title=broadcast.title,
                inline_keyboard=inline_keyboard
            )

            if success:
                delivery.status = DeliveryStatus.SENT.value
                delivery.sent_at = datetime.utcnow()
                sent_count += 1
                logger.info(f"Successfully sent to {delivery.telegram_user_id}")
            else:
                delivery.status = DeliveryStatus.FAILED.value
                delivery.error_message = error_msg
                failed_count += 1
                logger.error(f"Failed to send to {delivery.telegram_user_id}: {error_msg}")

            # Rate limiting: 30 msg/sec = ~33ms between messages
            import asyncio
            await asyncio.sleep(0.05)

        # Update broadcast statistics
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count
        broadcast.status = BroadcastStatus.SENT.value
        broadcast.completed_at = datetime.utcnow()

        db.commit()
        logger.info(f"Broadcast {broadcast_id} completed: {sent_count} sent, {failed_count} failed")

    except Exception as e:
        logger.error(f"Error processing broadcast {broadcast_id}: {str(e)}")
        if broadcast:
            broadcast.status = BroadcastStatus.FAILED.value
            db.commit()
    finally:
        db.close()
