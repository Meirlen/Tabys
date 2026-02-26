from typing import List, Optional
from pydantic import BaseModel


class InterestItem(BaseModel):
    interest_type: str  # "events", "news", "vacancies", "courses", "projects"
    category_value: Optional[str] = None  # None = all; specific string = filtered


class UserInterestsUpdate(BaseModel):
    interests: List[InterestItem]


class InterestItemResponse(InterestItem):
    id: int

    class Config:
        from_attributes = True


class AvailableCategories(BaseModel):
    events: List[str] = []
    news: List[str] = []
    vacancies: List[str] = []
    courses: List[str] = []
    projects: List[str] = []
