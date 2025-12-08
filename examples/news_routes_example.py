# Example: How to integrate RBAC into news.py
# Copy and paste the relevant parts into your actual route file

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.rbac import Module, Permission, require_permission, require_module_access
from app import models, schemas

router = APIRouter(prefix="/api/news", tags=["News"])


# ============================================================
# READ ROUTES - Allow read-only access
# ============================================================

@router.get("/")
def get_all_news(
    skip: int = 0,
    limit: int = 100,
    admin = Depends(require_module_access(Module.NEWS, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get all news
    - Accessible by: administrator, super_admin, government (read-only)
    """
    news = db.query(models.News).offset(skip).limit(limit).all()
    return news


# ============================================================
# CREATE ROUTES - Require create permission
# ============================================================

@router.post("/")
def create_news(
    news_data: schemas.NewsCreate,
    admin = Depends(require_permission(Module.NEWS, Permission.CREATE)),
    db: Session = Depends(get_db)
):
    """
    Create new news article
    - Accessible by: administrator, super_admin
    - Blocked for: government (read-only)
    """
    new_news = models.News(**news_data.dict())
    db.add(new_news)
    db.commit()
    db.refresh(new_news)

    return new_news


# ============================================================
# UPDATE ROUTES - Require update permission
# ============================================================

@router.put("/{news_id}")
def update_news(
    news_id: int,
    news_data: schemas.NewsUpdate,
    admin = Depends(require_permission(Module.NEWS, Permission.UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Update news article
    - Accessible by: administrator, super_admin
    """
    news = db.query(models.News).filter(models.News.id == news_id).first()

    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    for key, value in news_data.dict(exclude_unset=True).items():
        setattr(news, key, value)

    db.commit()
    db.refresh(news)

    return news


# ============================================================
# DELETE ROUTES - Require delete permission
# ============================================================

@router.delete("/{news_id}")
def delete_news(
    news_id: int,
    admin = Depends(require_permission(Module.NEWS, Permission.DELETE)),
    db: Session = Depends(get_db)
):
    """
    Delete news article
    - Accessible by: administrator, super_admin
    """
    news = db.query(models.News).filter(models.News.id == news_id).first()

    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    db.delete(news)
    db.commit()

    return {"message": "Новость удалена"}
