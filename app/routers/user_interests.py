from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.oauth2 import get_current_user
from app import models, news_models
from app.resume_models import Profession
from app.user_interest_models import UserInterest
from app.user_interest_schemas import (
    AvailableCategories,
    InterestItem,
    InterestItemResponse,
    UserInterestsUpdate,
)

router = APIRouter(prefix="/api/v2/interests", tags=["User Interests"])


@router.get("/categories", response_model=AvailableCategories)
def get_available_categories(db: Session = Depends(get_db)):
    """
    Return all available category values that users can subscribe to.
    - events: no sub-categories (empty list)
    - news: distinct values from news.category
    - vacancies: distinct profession categories
    - courses: distinct course category names
    - projects: no sub-categories (empty list)
    """
    # News categories
    news_cats = (
        db.query(news_models.News.category)
        .distinct()
        .filter(news_models.News.category.isnot(None))
        .all()
    )
    news_categories = sorted([row[0] for row in news_cats if row[0]])

    # Vacancy categories via Profession.category
    prof_cats = (
        db.query(Profession.category)
        .distinct()
        .filter(Profession.category.isnot(None), Profession.is_active == True)
        .all()
    )
    vacancy_categories = sorted([row[0] for row in prof_cats if row[0]])

    # Course categories via CourseCategory
    course_cats = db.query(models.CourseCategory.name).distinct().all()
    course_categories = sorted([row[0] for row in course_cats if row[0]])

    return AvailableCategories(
        events=[],
        news=news_categories,
        vacancies=vacancy_categories,
        courses=course_categories,
        projects=[],
    )


@router.get("/my", response_model=List[InterestItemResponse])
def get_my_interests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's interest subscriptions."""
    interests = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == current_user.id)
        .all()
    )
    return interests


@router.put("/my", response_model=List[InterestItemResponse])
def update_my_interests(
    payload: UserInterestsUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Replace all user interests. Deletes existing records and inserts new ones.
    Duplicate entries within the payload are silently deduplicated.
    """
    # Delete all existing interests for this user
    db.query(UserInterest).filter(UserInterest.user_id == current_user.id).delete()

    # Deduplicate by (interest_type, category_value)
    seen = set()
    new_interests = []
    for item in payload.interests:
        key = (item.interest_type, item.category_value)
        if key in seen:
            continue
        seen.add(key)
        new_interests.append(
            UserInterest(
                user_id=current_user.id,
                interest_type=item.interest_type,
                category_value=item.category_value,
            )
        )

    db.add_all(new_interests)
    db.commit()

    # Re-fetch to return with IDs
    saved = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == current_user.id)
        .all()
    )
    return saved
