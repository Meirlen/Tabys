"""
Moderation Notification Models
Track notification state to prevent duplicate alerts
"""
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class ModerationNotificationState(Base):
    """
    Stores the last known state of moderation queue to prevent duplicate notifications

    This is a singleton table (only one row exists) that tracks:
    - Last count of pending moderation items
    - Last time a notification was sent
    """
    __tablename__ = "moderation_notification_state"

    id = Column(Integer, primary_key=True, default=1)  # Singleton - always ID 1

    # Last known pending count
    last_pending_count = Column(Integer, default=0, nullable=False)

    # Last notification timestamp
    last_notified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @staticmethod
    def get_or_create(db):
        """Get singleton instance or create if not exists"""
        state = db.query(ModerationNotificationState).filter(
            ModerationNotificationState.id == 1
        ).first()

        if not state:
            state = ModerationNotificationState(
                id=1,
                last_pending_count=0,
                last_notified_at=None
            )
            db.add(state)
            db.commit()
            db.refresh(state)

        return state

    def should_notify(self, current_pending_count: int) -> bool:
        """
        Determine if we should send a notification

        Send notification if:
        1. Current pending count > 0
        2. Current pending count > last known count (new items appeared)

        Args:
            current_pending_count: Current number of pending moderation items

        Returns:
            bool: True if notification should be sent
        """
        # Don't notify if there are no pending items
        if current_pending_count == 0:
            return False

        # Notify if there are more pending items than before
        if current_pending_count > self.last_pending_count:
            return True

        return False

    def mark_notified(self, pending_count: int):
        """
        Mark that notification was sent

        Args:
            pending_count: Current pending count at time of notification
        """
        self.last_pending_count = pending_count
        self.last_notified_at = datetime.utcnow()
