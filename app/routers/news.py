from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import news_models, news_schemas, models, oauth2

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
    """Get all approved news articles (public endpoint)"""
    query = db.query(news_models.News).filter(
        news_models.News.moderation_status == 'approved'
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

@admin_router.post("/", response_model=news_schemas.NewsResponse, status_code=status.HTTP_201_CREATED)
def create_news(
    news: news_schemas.NewsCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    news_data = news.dict(exclude_unset=True)
    new_news = news_models.News(**news_data)
    db.add(new_news)
    db.commit()
    db.refresh(new_news)
    return new_news

@admin_router.put("/{id}", response_model=news_schemas.NewsResponse)
def update_news(
    id: int,
    news_update: news_schemas.NewsUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    news_query = db.query(news_models.News).filter(news_models.News.id == id)
    news_item = news_query.first()

    if not news_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    update_data = news_update.dict(exclude_unset=True)
    
    news_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(news_item)
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
