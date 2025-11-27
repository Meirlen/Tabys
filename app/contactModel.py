from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class ContactTicket(Base):
    __tablename__ = "contact_ticket"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(255), nullable=False)
    date = Column(DateTime, default=func.now(), nullable=False)
    status = Column(String(255), nullable=False, default="pending")