import secrets
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class UserTelegramLink(Base):
    __tablename__ = "user_telegram_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_2026_12.id"), unique=True, nullable=False)
    telegram_chat_id = Column(String, unique=True, nullable=True)
    telegram_username = Column(String, nullable=True)
    telegram_first_name = Column(String, nullable=True)
    link_token = Column(String, unique=True, nullable=True, index=True)
    link_token_expires_at = Column(DateTime, nullable=True)
    is_linked = Column(Boolean, default=False, nullable=False)
    linked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="telegram_link")

    def generate_link_token(self):
        self.link_token = secrets.token_urlsafe(32)
        self.link_token_expires_at = datetime.utcnow() + timedelta(minutes=10)
        return self.link_token

    def is_token_valid(self):
        if not self.link_token or not self.link_token_expires_at:
            return False
        return datetime.utcnow() < self.link_token_expires_at

    def mark_linked(self, chat_id, username=None, first_name=None):
        self.telegram_chat_id = chat_id
        self.telegram_username = username
        self.telegram_first_name = first_name
        self.is_linked = True
        self.linked_at = datetime.utcnow()
        self.link_token = None
        self.link_token_expires_at = None

    def unlink(self):
        self.telegram_chat_id = None
        self.telegram_username = None
        self.telegram_first_name = None
        self.is_linked = False
        self.linked_at = None
        self.link_token = None
        self.link_token_expires_at = None
