from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, timedelta, date
import logging
from app.database import get_db
from app import news_models, news_schemas, models, oauth2
from app.publication_config import PUBLICATION_SLOTS, SLOT_WINDOW_MINUTES

logger = logging.getLogger(__name__)

# Public router
router = APIRouter(
    prefix="/api/v2/news",
    tags=["News"]
)

# Admin router
admin_router = APIRouter(
    prefix="/api/v2/admin/news",
    tags=["News Admin"]
)

# Parser router (for news aggregator to submit articles)
parser_router = APIRouter(
    prefix="/api/v2/parser/news",
    tags=["News Parser"]
)

@router.get("/", response_model=List[news_schemas.NewsResponse])
def get_all_news(
    category: Optional[str] = Query(None, description="Filter news by category"),
    db: Session = Depends(get_db)
):
    """
    Get all published news articles (public endpoint).

    Shows news that are either:
    - Admin-created with status='published'
    - Parser-submitted with moderation_status='approved' (legacy support)
    """
    # News is visible if:
    # 1. It has status='published' (new scheduling system)
    # 2. OR it has moderation_status='approved' AND status is null/draft (legacy news)
    query = db.query(news_models.News).filter(
        (news_models.News.status == 'published') |
        (
            (news_models.News.moderation_status == 'approved') &
            (news_models.News.status.in_(['draft', None]))
        )
    )

    # Filter by category if provided
    if category:
        query = query.filter(news_models.News.category == category)

    news_list = query.order_by(news_models.News.date.desc()).all()
    return news_list

@router.get("/categories", response_model=List[str])
def get_all_categories(db: Session = Depends(get_db)):
    """Get all unique news categories"""
    categories = db.query(news_models.News.category).distinct().filter(
        news_models.News.category.isnot(None)
    ).all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/{id}", response_model=news_schemas.NewsResponse)
def get_news_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()
    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")
    return news_item

@router.post("/{id}/increment-view", response_model=news_schemas.NewsResponse)
def increment_news_view(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Increment the view count for a news article (public endpoint).

    This endpoint should be called when a user views a news article detail page.
    """
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()
    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    # Increment view count
    news_item.view_count = (news_item.view_count or 0) + 1

    db.commit()
    db.refresh(news_item)

    logger.info(f"Incremented view count for news ID={id} to {news_item.view_count}")

    return news_item

@admin_router.post("/", response_model=news_schemas.NewsResponse, status_code=status.HTTP_201_CREATED)
def create_news(
    news: news_schemas.NewsCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Create a new news article (admin endpoint).

    Admin-created news bypasses moderation and can be:
    - draft: Not ready for publication
    - scheduled: Will be auto-published at publish_at time
    - published: Immediately visible to public
    """
    news_data = news.dict(exclude_unset=True)

    # Mark as admin-created (bypasses moderation)
    news_data['is_admin_created'] = True

    # Handle status and moderation
    status_value = news_data.get('status', 'draft')

    if status_value == 'published':
        # Immediately publish - set moderation_status to approved
        news_data['moderation_status'] = 'approved'
        news_data['published_at'] = datetime.utcnow()
        news_data['moderated_at'] = datetime.utcnow()
        news_data['moderated_by'] = current_admin.id
    elif status_value == 'scheduled':
        # Validate publish_at is set
        if not news_data.get('publish_at'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="publish_at is required when status is 'scheduled'"
            )
        # Pre-approve for when scheduler publishes
        news_data['moderation_status'] = 'approved'
        news_data['moderated_at'] = datetime.utcnow()
        news_data['moderated_by'] = current_admin.id
    else:
        # Draft status - keep as pending until scheduled/published
        news_data['moderation_status'] = 'pending'

    new_news = news_models.News(**news_data)
    db.add(new_news)
    db.commit()
    db.refresh(new_news)

    logger.info(f"Admin {current_admin.id} created news ID={new_news.id} with status={status_value}")

    return new_news

@admin_router.put("/{id}", response_model=news_schemas.NewsResponse)
def update_news(
    id: int,
    news_update: news_schemas.NewsUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Update a news article (admin endpoint).

    Handles status transitions:
    - draft -> scheduled: Requires publish_at
    - draft -> published: Immediately visible
    - scheduled -> published: Immediately visible
    - published -> scheduled/draft: Not allowed (use delete instead)
    """
    news_query = db.query(news_models.News).filter(news_models.News.id == id)
    news_item = news_query.first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    update_data = news_update.dict(exclude_unset=True)

    # Handle status changes
    new_status = update_data.get('status')
    if new_status:
        # Prevent unpublishing already published news
        if news_item.status == 'published' and new_status in ['draft', 'scheduled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change status of already published news. Delete and create new instead."
            )

        if new_status == 'published':
            update_data['moderation_status'] = 'approved'
            update_data['published_at'] = datetime.utcnow()
            update_data['moderated_at'] = datetime.utcnow()
            update_data['moderated_by'] = current_admin.id
        elif new_status == 'scheduled':
            publish_at = update_data.get('publish_at') or news_item.publish_at
            if not publish_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="publish_at is required when status is 'scheduled'"
                )
            update_data['moderation_status'] = 'approved'
            update_data['moderated_at'] = datetime.utcnow()
            update_data['moderated_by'] = current_admin.id

    news_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(news_item)

    logger.info(f"Admin {current_admin.id} updated news ID={id}")

    return news_item

@admin_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(
    id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    news_query = db.query(news_models.News).filter(news_models.News.id == id)
    news_item = news_query.first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    news_query.delete(synchronize_session=False)
    db.commit()
    return None

# Moderation endpoints

@admin_router.get("/pending", response_model=List[news_schemas.NewsResponse])
def get_pending_news(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get all pending news articles awaiting moderation"""
    news_list = db.query(news_models.News).filter(
        news_models.News.moderation_status == 'pending'
    ).order_by(news_models.News.created_at.desc()).offset(skip).limit(limit).all()
    return news_list

@admin_router.get("/all-statuses", response_model=List[news_schemas.NewsResponse])
def get_all_news_with_status(
    moderation_status: Optional[news_schemas.ModerationStatus] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get all news articles with any status (admin only)"""
    query = db.query(news_models.News)

    if moderation_status:
        query = query.filter(news_models.News.moderation_status == moderation_status)

    if category:
        query = query.filter(news_models.News.category == category)

    news_list = query.order_by(news_models.News.created_at.desc()).offset(skip).limit(limit).all()
    return news_list

@admin_router.get("/stats", response_model=news_schemas.NewsStats)
def get_news_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get news moderation statistics"""
    total = db.query(news_models.News).count()
    pending = db.query(news_models.News).filter(
        news_models.News.moderation_status == 'pending'
    ).count()
    approved = db.query(news_models.News).filter(
        news_models.News.moderation_status == 'approved'
    ).count()
    rejected = db.query(news_models.News).filter(
        news_models.News.moderation_status == 'rejected'
    ).count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }

@admin_router.post("/{id}/approve", response_model=news_schemas.NewsResponse)
def approve_news(
    id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Approve a news article"""
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    news_item.moderation_status = 'approved'
    news_item.moderated_at = datetime.utcnow()
    news_item.moderated_by = current_admin.id

    db.commit()
    db.refresh(news_item)
    return news_item

@admin_router.post("/{id}/reject", response_model=news_schemas.NewsResponse)
def reject_news(
    id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Reject a news article"""
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    news_item.moderation_status = 'rejected'
    news_item.moderated_at = datetime.utcnow()
    news_item.moderated_by = current_admin.id

    db.commit()
    db.refresh(news_item)
    return news_item

# Parser endpoint

@parser_router.post("/submit", response_model=news_schemas.NewsResponse, status_code=status.HTTP_201_CREATED)
def submit_news_from_parser(
    news: news_schemas.NewsSubmit,
    db: Session = Depends(get_db)
):
    """Endpoint for news parser to submit articles (creates with pending status)"""

    # Check if URL already exists to prevent duplicates
    existing = db.query(news_models.News).filter(
        news_models.News.source_url == news.source_url
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="News article from this URL already exists"
        )

    # Create news article with pending status
    news_data = {
        "title_kz": news.title_kz,
        "title_ru": news.title_ru,
        "description_kz": news.description_kz,
        "description_ru": news.description_ru,
        "content_text_kz": news.content_text_kz,
        "content_text_ru": news.content_text_ru,
        "source_url": news.source_url,
        "source_name": news.source_name,
        "language": news.language,
        "category": news.category,
        "keywords_matched": news.keywords_matched,
        "photo_url": news.photo_url,
        "moderation_status": 'pending'
    }

    new_news = news_models.News(**news_data)
    db.add(new_news)
    db.commit()
    db.refresh(new_news)
    return new_news

# Publication scheduling endpoints

@admin_router.get("/schedule-status", response_model=news_schemas.ScheduleStatusResponse)
def get_schedule_status(
    target_date: Optional[str] = Query(None, description="Date to check (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Check the schedule status for a given date.

    Returns the status of each publication slot, including:
    - How many news are scheduled for each slot
    - Whether each slot meets its minimum requirement
    - Overall schedule status (ok/warning)
    """
    # Parse target date or use today
    if target_date:
        try:
            check_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        check_date = date.today()

    slots_status = []
    total_required = 0
    total_scheduled = 0

    for slot in PUBLICATION_SLOTS:
        slot_time = slot["time"]
        min_required = slot["min"]
        total_required += min_required

        # Parse slot time
        hour, minute = map(int, slot_time.split(":"))

        # Create datetime range for this slot (slot_time ± SLOT_WINDOW_MINUTES)
        slot_start = datetime.combine(check_date, datetime.min.time().replace(
            hour=hour, minute=minute
        )) - timedelta(minutes=SLOT_WINDOW_MINUTES)
        slot_end = datetime.combine(check_date, datetime.min.time().replace(
            hour=hour, minute=minute
        )) + timedelta(minutes=SLOT_WINDOW_MINUTES)

        # Count scheduled news for this slot
        scheduled_count = db.query(news_models.News).filter(
            news_models.News.status == 'scheduled',
            news_models.News.publish_at >= slot_start,
            news_models.News.publish_at <= slot_end
        ).count()

        total_scheduled += scheduled_count

        slots_status.append(news_schemas.SlotStatus(
            time=slot_time,
            required=min_required,
            scheduled=scheduled_count,
            status="ok" if scheduled_count >= min_required else "warning"
        ))

    overall_status = "ok" if total_scheduled >= total_required else "warning"

    return news_schemas.ScheduleStatusResponse(
        date=check_date.strftime("%Y-%m-%d"),
        slots=slots_status,
        total_required=total_required,
        total_scheduled=total_scheduled,
        overall_status=overall_status
    )

@admin_router.get("/scheduled", response_model=List[news_schemas.NewsResponse])
def get_scheduled_news(
    target_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get all scheduled news articles, optionally filtered by date"""
    query = db.query(news_models.News).filter(
        news_models.News.status == 'scheduled'
    )

    if target_date:
        try:
            check_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            # Filter news scheduled for this date
            start_of_day = datetime.combine(check_date, datetime.min.time())
            end_of_day = datetime.combine(check_date, datetime.max.time())
            query = query.filter(
                news_models.News.publish_at >= start_of_day,
                news_models.News.publish_at <= end_of_day
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    news_list = query.order_by(news_models.News.publish_at.asc()).offset(skip).limit(limit).all()
    return news_list

@admin_router.get("/drafts", response_model=List[news_schemas.NewsResponse])
def get_draft_news(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get all draft news articles (not yet scheduled or published)"""
    news_list = db.query(news_models.News).filter(
        news_models.News.status == 'draft',
        news_models.News.is_admin_created == True
    ).order_by(news_models.News.created_at.desc()).offset(skip).limit(limit).all()
    return news_list

@admin_router.post("/{id}/schedule", response_model=news_schemas.NewsResponse)
def schedule_news(
    id: int,
    schedule_data: news_schemas.NewsScheduleCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Schedule a draft news article for publication"""
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    if news_item.status == 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="News is already published"
        )

    # Update status to scheduled
    news_item.status = 'scheduled'
    news_item.publish_at = schedule_data.publish_at
    news_item.moderation_status = 'approved'
    news_item.moderated_at = datetime.utcnow()
    news_item.moderated_by = current_admin.id

    db.commit()
    db.refresh(news_item)

    logger.info(f"Admin {current_admin.id} scheduled news ID={id} for {schedule_data.publish_at}")

    return news_item

@admin_router.post("/{id}/publish-now", response_model=news_schemas.NewsResponse)
def publish_news_immediately(
    id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Immediately publish a draft or scheduled news article"""
    news_item = db.query(news_models.News).filter(news_models.News.id == id).first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    if news_item.status == 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="News is already published"
        )

    # Update status to published
    news_item.status = 'published'
    news_item.published_at = datetime.utcnow()
    news_item.moderation_status = 'approved'
    news_item.moderated_at = datetime.utcnow()
    news_item.moderated_by = current_admin.id

    db.commit()
    db.refresh(news_item)

    logger.info(f"Admin {current_admin.id} immediately published news ID={id}")

    return news_item
