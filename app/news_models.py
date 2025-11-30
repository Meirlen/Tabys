from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)

    # Original fields (kept for backward compatibility, now nullable)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)

    # Kazakh language fields (new)
    title_kz = Column(String(255), nullable=True)
    description_kz = Column(Text, nullable=True)
    content_text_kz = Column(Text, nullable=True)

    # Russian language fields (new)
    title_ru = Column(String(255), nullable=True)
    description_ru = Column(Text, nullable=True)
    content_text_ru = Column(Text, nullable=True)

    # Common fields
    photo_url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True, default=None)
    date = Column(DateTime, default=func.now(), nullable=False)
