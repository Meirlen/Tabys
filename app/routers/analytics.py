from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast, Date
from datetime import datetime, timedelta
from typing import Optional, List
from app.database import get_db
from app import analytics_models, analytics_schemas, models, oauth2

router = APIRouter(
    prefix="/api/v2/admin/analytics",
    tags=["Analytics"]
)


def get_date_range(period: str = 'day', start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Helper to calculate date ranges"""
    if start_date and end_date:
        return start_date, end_date

    now = datetime.utcnow()
    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'year':
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=1)

    return start, now


@router.get("/dashboard", response_model=analytics_schemas.AnalyticsDashboard)
def get_analytics_dashboard(
    period: str = Query('month', description="Time period: day, week, month, year"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """Get complete analytics dashboard data"""

    start, end = get_date_range(period, start_date, end_date)

    # User Statistics
    total_users = db.query(models.User).count()

    # Active users (those who had activity in the period)
    active_today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_week_start = datetime.utcnow() - timedelta(days=7)
    active_month_start = datetime.utcnow() - timedelta(days=30)

    active_today = db.query(func.count(func.distinct(analytics_models.UserActivity.user_id))).filter(
        analytics_models.UserActivity.user_type == 'user',
        analytics_models.UserActivity.created_at >= active_today_start
    ).scalar() or 0

    active_week = db.query(func.count(func.distinct(analytics_models.UserActivity.user_id))).filter(
        analytics_models.UserActivity.user_type == 'user',
        analytics_models.UserActivity.created_at >= active_week_start
    ).scalar() or 0

    active_month = db.query(func.count(func.distinct(analytics_models.UserActivity.user_id))).filter(
        analytics_models.UserActivity.user_type == 'user',
        analytics_models.UserActivity.created_at >= active_month_start
    ).scalar() or 0

    # New registrations
    new_today = db.query(models.User).filter(
        models.User.created_at >= active_today_start
    ).count()

    new_week = db.query(models.User).filter(
        models.User.created_at >= active_week_start
    ).count()

    new_month = db.query(models.User).filter(
        models.User.created_at >= active_month_start
    ).count()

    user_stats = analytics_schemas.UserStats(
        total_users=total_users,
        active_today=active_today,
        active_week=active_week,
        active_month=active_month,
        new_registrations_today=new_today,
        new_registrations_week=new_week,
        new_registrations_month=new_month
    )

    # Role Distribution
    role_distribution_raw = db.query(
        models.User.user_type,
        func.count(models.User.id)
    ).group_by(models.User.user_type).all()

    role_distribution = [
        analytics_schemas.UserRoleDistribution(role=role or 'unknown', count=count)
        for role, count in role_distribution_raw
    ]

    # Add admin roles
    admin_count = db.query(models.Admin).count()
    if admin_count > 0:
        role_distribution.append(
            analytics_schemas.UserRoleDistribution(role='admin', count=admin_count)
        )

    # User Growth (last 30 days by default)
    growth_start = datetime.utcnow() - timedelta(days=30)
    user_growth_data = []

    for i in range(30):
        date = growth_start + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        count = db.query(models.User).filter(
            cast(models.User.created_at, Date) == date.date()
        ).count()

        cumulative = db.query(models.User).filter(
            models.User.created_at <= date
        ).count()

        user_growth_data.append(
            analytics_schemas.UserGrowthDataPoint(
                date=date_str,
                count=count,
                cumulative=cumulative
            )
        )

    # Login Activity
    total_logins = db.query(analytics_models.LoginHistory).filter(
        analytics_models.LoginHistory.created_at >= start,
        analytics_models.LoginHistory.created_at <= end
    ).count()

    successful_logins = db.query(analytics_models.LoginHistory).filter(
        analytics_models.LoginHistory.created_at >= start,
        analytics_models.LoginHistory.created_at <= end,
        analytics_models.LoginHistory.status == 'success'
    ).count()

    failed_logins = total_logins - successful_logins

    unique_users = db.query(func.count(func.distinct(
        func.coalesce(analytics_models.LoginHistory.user_id, analytics_models.LoginHistory.admin_id)
    ))).filter(
        analytics_models.LoginHistory.created_at >= start,
        analytics_models.LoginHistory.created_at <= end
    ).scalar() or 0

    # Login activity by day
    login_by_day_raw = db.query(
        cast(analytics_models.LoginHistory.created_at, Date).label('date'),
        func.count(analytics_models.LoginHistory.id)
    ).filter(
        analytics_models.LoginHistory.created_at >= start,
        analytics_models.LoginHistory.created_at <= end
    ).group_by('date').order_by('date').all()

    login_by_day = [
        {'date': str(date), 'count': count}
        for date, count in login_by_day_raw
    ]

    login_activity = analytics_schemas.LoginActivityStats(
        total_logins=total_logins,
        successful_logins=successful_logins,
        failed_logins=failed_logins,
        unique_users=unique_users,
        by_day=login_by_day
    )

    # Activity Statistics
    total_actions = db.query(analytics_models.UserActivity).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end
    ).count()

    creates = db.query(analytics_models.UserActivity).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end,
        analytics_models.UserActivity.action_type == 'create'
    ).count()

    updates = db.query(analytics_models.UserActivity).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end,
        analytics_models.UserActivity.action_type == 'update'
    ).count()

    deletes = db.query(analytics_models.UserActivity).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end,
        analytics_models.UserActivity.action_type == 'delete'
    ).count()

    views = db.query(analytics_models.UserActivity).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end,
        analytics_models.UserActivity.action_type == 'view'
    ).count()

    # Activity by resource type
    by_resource_raw = db.query(
        analytics_models.UserActivity.resource_type,
        func.count(analytics_models.UserActivity.id)
    ).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end,
        analytics_models.UserActivity.resource_type.isnot(None)
    ).group_by(analytics_models.UserActivity.resource_type).all()

    by_resource_type = [
        {'resource_type': resource or 'unknown', 'count': count}
        for resource, count in by_resource_raw
    ]

    activity_stats = analytics_schemas.ActivityStats(
        total_actions=total_actions,
        creates=creates,
        updates=updates,
        deletes=deletes,
        views=views,
        by_resource_type=by_resource_type
    )

    # Top Active Users
    top_users_raw = db.query(
        analytics_models.UserActivity.user_id,
        analytics_models.UserActivity.admin_id,
        analytics_models.UserActivity.user_type,
        func.count(analytics_models.UserActivity.id).label('action_count')
    ).filter(
        analytics_models.UserActivity.created_at >= start,
        analytics_models.UserActivity.created_at <= end
    ).group_by(
        analytics_models.UserActivity.user_id,
        analytics_models.UserActivity.admin_id,
        analytics_models.UserActivity.user_type
    ).order_by(func.count(analytics_models.UserActivity.id).desc()).limit(10).all()

    top_active_users = []
    for user_id, admin_id, user_type, action_count in top_users_raw:
        name = None
        if user_type == 'admin' and admin_id:
            admin = db.query(models.Admin).filter(models.Admin.id == admin_id).first()
            if admin:
                name = admin.name
        elif user_type == 'user' and user_id:
            # Try to get name from Individual table first
            individual = db.query(models.Individual).filter(models.Individual.user_id == user_id).first()
            if individual:
                name = individual.full_name
            else:
                organization = db.query(models.Organization).filter(models.Organization.user_id == user_id).first()
                if organization:
                    name = organization.name

        name = '-'

        top_active_users.append(
            analytics_schemas.TopActiveUser(
                user_id=user_id,
                admin_id=admin_id,
                user_type=user_type,
                name=name,
                action_count=action_count
            )
        )

    # System Events
    total_events = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.created_at >= start,
        analytics_models.SystemEvent.created_at <= end
    ).count()

    errors = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.created_at >= start,
        analytics_models.SystemEvent.created_at <= end,
        analytics_models.SystemEvent.event_type == 'error'
    ).count()

    warnings = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.created_at >= start,
        analytics_models.SystemEvent.created_at <= end,
        analytics_models.SystemEvent.event_type == 'warning'
    ).count()

    info = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.created_at >= start,
        analytics_models.SystemEvent.created_at <= end,
        analytics_models.SystemEvent.event_type == 'info'
    ).count()

    critical = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.created_at >= start,
        analytics_models.SystemEvent.created_at <= end,
        analytics_models.SystemEvent.event_type == 'critical'
    ).count()

    recent_errors = db.query(analytics_models.SystemEvent).filter(
        analytics_models.SystemEvent.event_type.in_(['error', 'critical'])
    ).order_by(analytics_models.SystemEvent.created_at.desc()).limit(10).all()

    system_events = analytics_schemas.SystemEventsStats(
        total_events=total_events,
        errors=errors,
        warnings=warnings,
        info=info,
        critical=critical,
        recent_errors=recent_errors
    )

    return analytics_schemas.AnalyticsDashboard(
        user_stats=user_stats,
        role_distribution=role_distribution,
        user_growth=user_growth_data,
        login_activity=login_activity,
        activity_stats=activity_stats,
        top_active_users=top_active_users,
        system_events=system_events
    )


@router.post("/activity/log")
def log_user_activity(
    activity: analytics_schemas.UserActivityCreate,
    db: Session = Depends(get_db)
):
    """Log a user activity"""
    new_activity = analytics_models.UserActivity(**activity.dict())
    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)
    return {"message": "Activity logged successfully", "id": new_activity.id}


@router.post("/login/log")
def log_login_attempt(
    login_data: analytics_schemas.LoginHistoryCreate,
    db: Session = Depends(get_db)
):
    """Log a login attempt"""
    new_login = analytics_models.LoginHistory(**login_data.dict())
    db.add(new_login)
    db.commit()
    db.refresh(new_login)
    return {"message": "Login logged successfully", "id": new_login.id}


@router.post("/event/log")
def log_system_event(
    event: analytics_schemas.SystemEventCreate,
    db: Session = Depends(get_db)
):
    """Log a system event"""
    new_event = analytics_models.SystemEvent(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return {"message": "Event logged successfully", "id": new_event.id}
