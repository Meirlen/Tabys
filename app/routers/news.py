from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
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

@router.get("/", response_model=List[news_schemas.NewsResponse])
def get_all_news(
    category: Optional[str] = Query(None, description="Filter news by category"),
    db: Session = Depends(get_db)
):
    query = db.query(news_models.News)

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
