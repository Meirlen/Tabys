"""
Moderation Notification Scheduler

Background task that monitors the moderation queue and sends Telegram notifications
to admins and superadmins when new items appear.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.project_models import Project
from app.leisure_models import Place, Ticket, PromoAction
from app.moderation_notification_models import ModerationNotificationState
from app.broadcast_models import Broadcast, BroadcastTargetAudience, BroadcastStatus
from app.moderation_notification_config import (
    MODERATION_CHECK_INTERVAL_MINUTES,
    CRM_MODERATION_URL,
    NOTIFICATION_MESSAGE,
    BROADCAST_TITLE,
    BUTTON_TEXT
)
from config import get_settings
from app.email_service import email_service, create_moderation_notification_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag to control scheduler
_scheduler_running = False
_scheduler_task: Optional[asyncio.Task] = None


def get_db_session() -> Session:
    """Create a new database session"""
    return SessionLocal()


def get_total_pending_count(db: Session) -> int:
    """
    Get total count of pending moderation items across all entity types

    Args:
        db: Database session

    Returns:
        int: Total number of pending items
    """
    total_pending = 0

    # Query each entity type for pending items
    entity_models = [
        models.Event,
        models.Vacancy,
        models.Course,
        Project,
        Place,
        Ticket,
        PromoAction
    ]

    for model_class in entity_models:
        try:
            pending_count = db.query(model_class).filter(
                model_class.moderation_status == 'pending'
            ).count()
            total_pending += pending_count
        except Exception as e:
            logger.error(f"Error counting pending items for {model_class.__name__}: {str(e)}")

    return total_pending


def get_admin_emails(db: Session) -> list:
    """
    Get email addresses of all administrators and super_admins

    Args:
        db: Database session

    Returns:
        list: List of email addresses (only admins with email field populated)
    """
    try:
        # Query admins and super_admins who have email addresses
        admins = db.query(models.Admin).filter(
            models.Admin.role.in_(['administrator', 'super_admin']),
            models.Admin.email.isnot(None),
            models.Admin.email != ''
        ).all()

        # Extract email addresses
        emails = [admin.email for admin in admins if admin.email and admin.email.strip()]

        logger.info(f"Found {len(emails)} admin email addresses for notifications")
        return emails

    except Exception as e:
        logger.error(f"Error fetching admin emails: {str(e)}")
        return []


async def send_email_notifications(pending_count: int, db: Session) -> bool:
    """
    Send email notifications to all administrators and super_admins

    Args:
        pending_count: Number of pending moderation items
        db: Database session

    Returns:
        bool: True if at least one email sent successfully
    """
    try:
        # Get admin email addresses
        admin_emails = get_admin_emails(db)

        if not admin_emails:
            logger.warning("No admin emails found for email notifications")
            return False

        # Create email content
        html_body, text_body = create_moderation_notification_email(
            pending_count,
            CRM_MODERATION_URL
        )

        # Send emails
        result = email_service.send_bulk_emails(
            recipients=admin_emails,
            subject=BROADCAST_TITLE,
            body_html=html_body,
            body_text=text_body
        )

        logger.info(
            f"Email notification result: {result['sent']} sent, "
            f"{result['failed']} failed"
        )

        # Return True if at least one email was sent
        return result['sent'] > 0

    except Exception as e:
        logger.error(f"Failed to send email notifications: {str(e)}")
        return False


async def send_broadcast_via_api(broadcast_id: int, db: Session) -> bool:
    """
    Send broadcast by creating delivery records and triggering background task

    Args:
        broadcast_id: ID of broadcast to send
        db: Database session

    Returns:
        bool: True if sent successfully
    """
    try:
        from app.routers.broadcasts import process_broadcast_deliveries, get_target_users
        from app.broadcast_models import Broadcast, BroadcastDelivery, BroadcastStatus, DeliveryStatus
        from datetime import datetime

        # Get broadcast
        broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
        if not broadcast:
            logger.error(f"Broadcast {broadcast_id} not found")
            return False

        # Get target users
        telegram_user_ids = get_target_users(
            db,
            broadcast.target_audience,
            broadcast.target_role
        )

        if not telegram_user_ids:
            logger.error(f"No target users found for broadcast {broadcast_id}")
            return False

        logger.info(f"Found {len(telegram_user_ids)} target users for broadcast {broadcast_id}")

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

        # Schedule the delivery processing
        asyncio.create_task(process_broadcast_deliveries(broadcast_id))

        logger.info(f"Scheduled broadcast {broadcast_id} for delivery to {len(telegram_user_ids)} users")
        return True

    except Exception as e:
        logger.error(f"Failed to send broadcast {broadcast_id}: {str(e)}")
        db.rollback()
        return False


def create_moderation_notification_broadcast(db: Session, pending_count: int) -> Optional[int]:
    """
    Create a broadcast notification for new moderation items

    Args:
        db: Database session
        pending_count: Number of pending moderation items

    Returns:
        Optional[int]: Broadcast ID if created successfully, None otherwise
    """
    try:
        # Format the message with pending count
        message = NOTIFICATION_MESSAGE.format(count=pending_count)

        # Create broadcast targeting ADMINS_ONLY (includes all admin roles)
        # We'll filter to only administrator and super_admin in the get_target_users_for_moderation function
        broadcast = Broadcast(
            title=BROADCAST_TITLE,
            message=message,
            target_audience=BroadcastTargetAudience.ADMINS_ONLY.value,
            target_role=None,
            status=BroadcastStatus.DRAFT.value,
            created_by=1  # System-generated notification (use admin ID 1 or system admin)
        )

        db.add(broadcast)
        db.commit()
        db.refresh(broadcast)

        logger.info(f"Created moderation notification broadcast ID={broadcast.id} for {pending_count} pending items")
        return broadcast.id

    except Exception as e:
        logger.error(f"Failed to create moderation notification broadcast: {str(e)}")
        db.rollback()
        return None


async def check_and_notify_moderation(db: Session) -> bool:
    """
    Check moderation queue and send notification if new items detected
    Sends both Telegram and email notifications

    Args:
        db: Database session

    Returns:
        bool: True if at least one notification was sent
    """
    try:
        # Get current pending count
        current_pending = get_total_pending_count(db)

        # Get or create notification state
        state = ModerationNotificationState.get_or_create(db)

        # Check if we should notify
        if not state.should_notify(current_pending):
            logger.debug(f"No notification needed. Current: {current_pending}, Last: {state.last_pending_count}")
            return False

        logger.info(f"New moderation items detected: {current_pending} pending (was {state.last_pending_count})")

        # Track if any notification method succeeded
        telegram_success = False
        email_success = False

        # Send Telegram notification
        try:
            # Create broadcast
            broadcast_id = create_moderation_notification_broadcast(db, current_pending)

            if broadcast_id:
                # Send broadcast via API (pass db session)
                telegram_success = await send_broadcast_via_api(broadcast_id, db)
                if telegram_success:
                    logger.info(f"Telegram notification sent successfully (broadcast ID={broadcast_id})")
                else:
                    logger.error("Failed to send Telegram broadcast")
            else:
                logger.error("Failed to create Telegram broadcast")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")

        # Send email notification
        try:
            email_success = await send_email_notifications(current_pending, db)
            if email_success:
                logger.info("Email notifications sent successfully")
            else:
                logger.warning("Failed to send email notifications (no emails sent)")
        except Exception as e:
            logger.error(f"Error sending email notifications: {str(e)}")

        # Update state if at least one notification method succeeded
        if telegram_success or email_success:
            state.mark_notified(current_pending)
            db.commit()
            logger.info(
                f"Moderation notification complete: "
                f"Telegram={'✓' if telegram_success else '✗'}, "
                f"Email={'✓' if email_success else '✗'}"
            )
            return True
        else:
            logger.error("All notification methods failed")
            return False

    except Exception as e:
        logger.error(f"Error in check_and_notify_moderation: {str(e)}")
        return False


async def scheduler_loop():
    """
    Main scheduler loop that runs periodically to check moderation queue
    """
    global _scheduler_running

    logger.info(f"Moderation notification scheduler started (interval: {MODERATION_CHECK_INTERVAL_MINUTES} minute(s))")

    while _scheduler_running:
        try:
            db = get_db_session()
            try:
                await check_and_notify_moderation(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Moderation notification scheduler error (will retry): {str(e)}")

        # Wait for the next interval
        await asyncio.sleep(MODERATION_CHECK_INTERVAL_MINUTES * 60)


def start_scheduler():
    """
    Start the background scheduler.
    Should be called when the application starts.
    """
    global _scheduler_running, _scheduler_task

    if _scheduler_running:
        logger.warning("Moderation notification scheduler is already running")
        return

    _scheduler_running = True

    # Ensure the notification state table exists
    try:
        db = get_db_session()
        try:
            # This will create the table if it doesn't exist and initialize state
            ModerationNotificationState.get_or_create(db)
            logger.info("Moderation notification state initialized")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not initialize moderation notification state: {str(e)}")

    # Start the background task
    try:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        logger.info("Moderation notification scheduler task created")
    except Exception as e:
        logger.error(f"Failed to create moderation notification scheduler task: {str(e)}")
        _scheduler_running = False


def stop_scheduler():
    """
    Stop the background scheduler.
    Should be called when the application shuts down.
    """
    global _scheduler_running, _scheduler_task

    _scheduler_running = False

    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Moderation notification scheduler stopped")
