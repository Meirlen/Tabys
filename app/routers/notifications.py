from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database import get_db
from app import models, oauth2
from app.notification_models import UserNotification
from app.notification_schemas import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    AdminNotificationCreate,
    AdminNotificationBulkResponse,
)
from app.notification_service import create_notification
from typing import List, Optional

router = APIRouter(prefix="/api/v2/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated notifications for the current user."""
    query = db.query(UserNotification).filter(
        UserNotification.user_id == current_user.id
    )

    if unread_only:
        query = query.filter(UserNotification.is_read == False)

    total = query.count()

    unread_count = (
        db.query(func.count(UserNotification.id))
        .filter(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read == False,
        )
        .scalar()
    )

    notifications = (
        query.order_by(desc(UserNotification.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count,
    }


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight endpoint for polling unread count."""
    count = (
        db.query(func.count(UserNotification.id))
        .filter(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read == False,
        )
        .scalar()
    )
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notification = (
        db.query(UserNotification)
        .filter(
            UserNotification.id == notification_id,
            UserNotification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    db.commit()

    return {"message": "Notification marked as read"}


@router.patch("/read-all")
def mark_all_as_read(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    db.query(UserNotification).filter(
        UserNotification.user_id == current_user.id,
        UserNotification.is_read == False,
    ).update({"is_read": True})

    db.commit()

    return {"message": "All notifications marked as read"}


# === ADMIN ENDPOINTS ===


@router.post("/admin/send", response_model=AdminNotificationBulkResponse)
def admin_send_notifications(
    notification_data: AdminNotificationCreate,
    current_admin: models.Admin = Depends(oauth2.get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to send custom notifications to specific users or all users.

    - If send_to_all is True, sends to all active users
    - Otherwise sends to users specified in user_ids list
    """

    # Determine recipient list
    if notification_data.send_to_all:
        # Get all active users
        users = db.query(models.User).filter(
            models.User.status == "ACTIVE"
        ).all()
        user_ids = [user.id for user in users]
    else:
        user_ids = notification_data.user_ids

    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No users specified and send_to_all is False"
        )

    # Create notifications for each user
    notifications_created = 0
    failed_users = []

    for user_id in user_ids:
        try:
            # Verify user exists
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                failed_users.append(user_id)
                continue

            # Create notification
            create_notification(
                db=db,
                user_id=user_id,
                title_kz=notification_data.title_kz,
                title_ru=notification_data.title_ru,
                notification_type=notification_data.notification_type,
                message_kz=notification_data.message_kz,
                message_ru=notification_data.message_ru,
            )
            notifications_created += 1
        except Exception as e:
            print(f"Failed to create notification for user {user_id}: {e}")
            failed_users.append(user_id)

    # Commit all notifications at once
    db.commit()

    return {
        "message": f"Successfully created {notifications_created} notifications",
        "notifications_created": notifications_created,
        "failed_users": failed_users,
    }


@router.get("/admin/all", response_model=NotificationListResponse)
def admin_get_all_notifications(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    current_admin: models.Admin = Depends(oauth2.get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to view all notifications (optionally filtered by user).
    """
    query = db.query(UserNotification)

    if user_id:
        query = query.filter(UserNotification.user_id == user_id)

    total = query.count()

    notifications = (
        query.order_by(desc(UserNotification.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    # For admin view, unread_count is not meaningful
    return {
        "notifications": notifications,
        "total": total,
        "unread_count": 0,
    }
