import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.notification_models import UserNotification
from app.user_interest_models import UserInterest
from app.user_telegram_models import UserTelegramLink
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: int,
    title_kz: str,
    title_ru: str,
    notification_type: str,
    message_kz: Optional[str] = None,
    message_ru: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    admin_comment: Optional[str] = None,
):
    """
    Create a notification record. Does db.add() but NOT db.commit(),
    so it joins the calling route's transaction atomically.
    """
    notification = UserNotification(
        user_id=user_id,
        title_kz=title_kz,
        title_ru=title_ru,
        message_kz=message_kz,
        message_ru=message_ru,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        admin_comment=admin_comment,
    )
    db.add(notification)
    return notification


def notify_interested_users_for_content(
    db: Session,  # kept for API compat but a fresh session is created internally
    content_type: str,
    category_value: Optional[str],
    title_kz: str,
    title_ru: str,
    message_kz: str,
    message_ru: str,
    entity_id: int,
    telegram_bot_token: str,
):
    """
    Find users interested in `content_type` (optionally filtered by `category_value`),
    create an in-site notification for each, and send a Telegram message if the user
    has a linked Telegram account.

    A fresh DB session is always opened so this is safe to run as a BackgroundTask.

    Matching logic:
      - A UserInterest row with category_value IS NULL subscribes to ALL categories
        of that content_type.
      - A row with a specific category_value matches only that category.
    """
    from sqlalchemy import or_

    fresh_db = SessionLocal()
    try:
        # Build query: match interest_type AND (category_value matches OR user subscribed to all)
        query = fresh_db.query(UserInterest).filter(
            UserInterest.interest_type == content_type,
        )

        if category_value is not None:
            query = query.filter(
                or_(
                    UserInterest.category_value.is_(None),
                    UserInterest.category_value == category_value,
                )
            )
        # If category_value is None, all subscribers for this type are matched

        interests = query.all()
        user_ids = list({i.user_id for i in interests})

        if not user_ids:
            return

        # Build Telegram message (bilingual HTML)
        type_labels = {
            "events": ("іс-шара", "мероприятие"),
            "news": ("жаңалық", "новость"),
            "vacancies": ("вакансия", "вакансия"),
            "courses": ("курс", "курс"),
            "projects": ("жоба", "проект"),
        }
        type_kz, type_ru = type_labels.get(content_type, (content_type, content_type))
        telegram_text = (
            f"🔔 <b>Жаңа {type_kz}</b> / <b>Новый {type_ru}</b>\n\n"
            f"<b>{title_kz}</b>\n{message_kz}"
        )

        for user_id in user_ids:
            # In-site notification (add without commit – batch commit below)
            notification = UserNotification(
                user_id=user_id,
                title_kz=title_kz,
                title_ru=title_ru,
                message_kz=message_kz,
                message_ru=message_ru,
                notification_type="new_content",
                entity_type=content_type,
                entity_id=entity_id,
            )
            fresh_db.add(notification)

            # Telegram notification (if linked)
            if telegram_bot_token:
                tg_link = (
                    fresh_db.query(UserTelegramLink)
                    .filter(
                        UserTelegramLink.user_id == user_id,
                        UserTelegramLink.is_linked == True,
                    )
                    .first()
                )
                if tg_link and tg_link.telegram_chat_id:
                    try:
                        with httpx.Client(timeout=5.0) as client:
                            client.post(
                                f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage",
                                json={
                                    "chat_id": tg_link.telegram_chat_id,
                                    "text": telegram_text,
                                    "parse_mode": "HTML",
                                },
                            )
                    except Exception as tg_err:
                        logger.warning(
                            f"Telegram send failed for user {user_id}: {tg_err}"
                        )

        fresh_db.commit()
        logger.info(
            f"Notified {len(user_ids)} users about new {content_type} (id={entity_id})"
        )

    except Exception as exc:
        logger.error(f"notify_interested_users_for_content error: {exc}")
        fresh_db.rollback()
    finally:
        fresh_db.close()
