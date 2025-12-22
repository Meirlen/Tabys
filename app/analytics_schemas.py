from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# Activity Schemas
class UserActivityBase(BaseModel):
    user_id: Optional[int] = None
    admin_id: Optional[int] = None
    user_type: str
    action_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class UserActivityCreate(UserActivityBase):
    pass


class UserActivityResponse(UserActivityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Login History Schemas
class LoginHistoryBase(BaseModel):
    user_id: Optional[int] = None
    admin_id: Optional[int] = None
    user_type: str
    phone_number: Optional[str] = None
    login: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LoginHistoryCreate(LoginHistoryBase):
    pass


class LoginHistoryResponse(LoginHistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# System Event Schemas
class SystemEventBase(BaseModel):
    event_type: str
    source: str
    message: str
    details: Optional[str] = None
    user_id: Optional[int] = None
    admin_id: Optional[int] = None


class SystemEventCreate(SystemEventBase):
    pass


class SystemEventResponse(SystemEventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics Response Schemas
class UserStats(BaseModel):
    total_users: int
    active_today: int
    active_week: int
    active_month: int
    new_registrations_today: int
    new_registrations_week: int
    new_registrations_month: int


class UserRoleDistribution(BaseModel):
    role: str
    count: int


class UserGrowthDataPoint(BaseModel):
    date: str
    count: int
    cumulative: int


class LoginActivityStats(BaseModel):
    total_logins: int
    successful_logins: int
    failed_logins: int
    unique_users: int
    by_day: List[dict]


class ActivityStats(BaseModel):
    total_actions: int
    creates: int
    updates: int
    deletes: int
    views: int
    by_resource_type: List[dict]


class TopActiveUser(BaseModel):
    user_id: Optional[int]
    admin_id: Optional[int]
    user_type: str
    name: Optional[str]
    action_count: int


class SystemEventsStats(BaseModel):
    total_events: int
    errors: int
    warnings: int
    info: int
    critical: int
    recent_errors: List[SystemEventResponse]


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard data"""
    user_stats: UserStats
    role_distribution: List[UserRoleDistribution]
    user_growth: List[UserGrowthDataPoint]
    login_activity: LoginActivityStats
    activity_stats: ActivityStats
    top_active_users: List[TopActiveUser]
    system_events: SystemEventsStats


class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = 'day'  # 'day', 'week', 'month'
