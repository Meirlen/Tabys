from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class UserActivity(Base):
    """Track user and admin activities in the system"""
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # User ID if regular user
    admin_id = Column(Integer, nullable=True)  # Admin ID if admin action
    user_type = Column(String(20), nullable=False)  # 'user', 'admin'
    action_type = Column(String(50), nullable=False)  # 'create', 'update', 'delete', 'view', 'login', 'logout'
    resource_type = Column(String(50), nullable=True)  # 'course', 'vacancy', 'news', 'event', etc.
    resource_id = Column(Integer, nullable=True)  # ID of the affected resource
    description = Column(Text, nullable=True)  # Additional details about the action
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)  # Browser/device info
    created_at = Column(DateTime, default=func.now(), nullable=False)


class LoginHistory(Base):
    """Track user and admin login attempts"""
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # User ID if regular user
    admin_id = Column(Integer, nullable=True)  # Admin ID if admin
    user_type = Column(String(20), nullable=False)  # 'user', 'admin'
    phone_number = Column(String(20), nullable=True)
    login = Column(String(100), nullable=True)  # For admins
    status = Column(String(20), nullable=False)  # 'success', 'failed'
    failure_reason = Column(String(200), nullable=True)  # If failed
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class SystemEvent(Base):
    """Track system-level events and errors"""
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # 'error', 'warning', 'info', 'critical'
    source = Column(String(100), nullable=False)  # Where the event originated
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON or additional details
    user_id = Column(Integer, nullable=True)
    admin_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
