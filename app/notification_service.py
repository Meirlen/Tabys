from sqlalchemy.orm import Session
from app.notification_models import UserNotification
from typing import Optional


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
