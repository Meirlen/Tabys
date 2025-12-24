"""
News publication scheduler.

This module handles automatic publishing of scheduled news articles.
It runs as a background task and publishes news when their publish_at time arrives.
"""

import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import news_models
from app.publication_config import SCHEDULER_INTERVAL_MINUTES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag to control scheduler
_scheduler_running = False
_scheduler_task: Optional[asyncio.Task] = None


def get_db_session() -> Session:
    """Create a new database session"""
    return SessionLocal()


def publish_scheduled_news(db: Session) -> int:
    """
    Publish all news articles that are scheduled and past their publish_at time.

    This function is idempotent - calling it multiple times will not cause issues.

    Returns:
        int: Number of news articles published
    """
    now = datetime.utcnow()

    # Find all scheduled news with publish_at <= now
    scheduled_news = db.query(news_models.News).filter(
        news_models.News.status == 'scheduled',
        news_models.News.publish_at <= now
    ).all()

    published_count = 0

    for news in scheduled_news:
        try:
            # Update status to published
            news.status = 'published'
            news.published_at = now

            # Also update moderation_status to approved for consistency
            news.moderation_status = 'approved'

            db.commit()
            published_count += 1

            logger.info(f"Published news article ID={news.id}, title='{news.title_kz or news.title_ru}'")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to publish news ID={news.id}: {str(e)}")

    return published_count


def publish_overdue_news_on_startup(db: Session) -> int:
    """
    Called on application startup to publish any news that should have been
    published while the server was down.

    Returns:
        int: Number of overdue news articles published
    """
    try:
        logger.info("Checking for overdue scheduled news on startup...")
        count = publish_scheduled_news(db)
        if count > 0:
            logger.info(f"Published {count} overdue news articles")
        else:
            logger.info("No overdue news articles found")
        return count
    except Exception as e:
        # Handle case where columns don't exist yet (migration not run)
        logger.warning(f"Could not check for overdue news (migration may be needed): {str(e)}")
        return 0


async def scheduler_loop():
    """
    Main scheduler loop that runs periodically to publish scheduled news.
    """
    global _scheduler_running

    logger.info(f"News scheduler started (interval: {SCHEDULER_INTERVAL_MINUTES} minute(s))")

    while _scheduler_running:
        try:
            db = get_db_session()
            try:
                count = publish_scheduled_news(db)
                if count > 0:
                    logger.info(f"Scheduler published {count} news article(s)")
            finally:
                db.close()
        except Exception as e:
            # Log error but continue running - might be temporary DB issue or missing migration
            logger.error(f"Scheduler error (will retry): {str(e)}")

        # Wait for the next interval
        await asyncio.sleep(SCHEDULER_INTERVAL_MINUTES * 60)


def start_scheduler():
    """
    Start the background scheduler.
    Should be called when the application starts.
    """
    global _scheduler_running, _scheduler_task

    if _scheduler_running:
        logger.warning("Scheduler is already running")
        return

    _scheduler_running = True

    # Publish any overdue news first (handle errors gracefully)
    try:
        db = get_db_session()
        try:
            publish_overdue_news_on_startup(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not process overdue news on startup: {str(e)}")

    # Start the background task
    try:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        logger.info("News scheduler task created")
    except Exception as e:
        logger.error(f"Failed to create scheduler task: {str(e)}")
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
        logger.info("News scheduler stopped")


@asynccontextmanager
async def scheduler_lifespan():
    """
    Context manager for scheduler lifecycle.
    Use with FastAPI lifespan events.
    """
    start_scheduler()
    yield
    stop_scheduler()
