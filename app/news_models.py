from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    photo_url = Column(String(500), nullable=True)
    content_text = Column(Text, nullable=False)
    date = Column(DateTime, default=func.now(), nullable=False)
