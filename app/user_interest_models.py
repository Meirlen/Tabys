from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    # "events", "news", "vacancies", "courses", "projects"
    interest_type = Column(String(50), nullable=False)
    # null = subscribe to ALL; or a specific category string
    category_value = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "interest_type", "category_value", name="uq_user_interest"),
    )
