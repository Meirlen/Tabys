"""
Analytics Statistics Viewer

Quick script to view current analytics data without starting the full application.
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Individual, Organization, Admin
from app.analytics_models import UserActivity, LoginHistory, SystemEvent


def print_separator(char="=", length=70):
    """Print a separator line"""
    print(char * length)


def print_section(title):
    """Print a section title"""
    print()
    print_separator()
    print(f"  {title}")
    print_separator()


def view_stats():
    """Display current analytics statistics"""
    db = SessionLocal()
    
    try:
        print_separator()
        print("  TABYS ANALYTICS - CURRENT STATISTICS")
        print_separator()
        print(f"  Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()
        
        # User Statistics
        print_section("USER STATISTICS")
        
        total_users = db.query(User).count()
        total_individuals = db.query(Individual).count()
        total_organizations = db.query(Organization).count()
        total_admins = db.query(Admin).count()
        verified_users = db.query(User).filter(User.is_verified == True).count()
        
        print(f"  Total Users:          {total_users:,}")
        print(f"    - Individuals:      {total_individuals:,} ({total_individuals/total_users*100:.1f}%)")
        print(f"    - Organizations:    {total_organizations:,} ({total_organizations/total_users*100:.1f}%)")
        print(f"  Total Admins:         {total_admins:,}")
        print(f"  Verified Users:       {verified_users:,} ({verified_users/total_users*100:.1f}%)")
        
        # Active Users
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = datetime.utcnow() - timedelta(days=7)
        month_start = datetime.utcnow() - timedelta(days=30)
        
        active_today = db.query(func.count(func.distinct(UserActivity.user_id))).filter(
            UserActivity.user_type == 'user',
            UserActivity.created_at >= today_start
        ).scalar() or 0
        
        active_week = db.query(func.count(func.distinct(UserActivity.user_id))).filter(
            UserActivity.user_type == 'user',
            UserActivity.created_at >= week_start
        ).scalar() or 0
        
        active_month = db.query(func.count(func.distinct(UserActivity.user_id))).filter(
            UserActivity.user_type == 'user',
            UserActivity.created_at >= month_start
        ).scalar() or 0
        
        print()
        print(f"  Active Today:         {active_today:,}")
        print(f"  Active This Week:     {active_week:,}")
        print(f"  Active This Month:    {active_month:,}")
        
        # New Registrations
        new_today = db.query(User).filter(User.created_at >= today_start).count()
        new_week = db.query(User).filter(User.created_at >= week_start).count()
        new_month = db.query(User).filter(User.created_at >= month_start).count()
        
        print()
        print(f"  New Registrations:")
        print(f"    - Today:            {new_today:,}")
        print(f"    - This Week:        {new_week:,}")
        print(f"    - This Month:       {new_month:,}")
        
        # Activity Statistics
        print_section("ACTIVITY STATISTICS")
        
        total_activities = db.query(UserActivity).count()
        activities_today = db.query(UserActivity).filter(UserActivity.created_at >= today_start).count()
        activities_week = db.query(UserActivity).filter(UserActivity.created_at >= week_start).count()
        activities_month = db.query(UserActivity).filter(UserActivity.created_at >= month_start).count()
        
        print(f"  Total Activities:     {total_activities:,}")
        print(f"    - Today:            {activities_today:,}")
        print(f"    - This Week:        {activities_week:,}")
        print(f"    - This Month:       {activities_month:,}")
        
        # Activity breakdown by type
        print()
        print("  Activity Breakdown (All Time):")
        
        activity_types = db.query(
            UserActivity.action_type,
            func.count(UserActivity.id)
        ).group_by(UserActivity.action_type).all()
        
        for action_type, count in sorted(activity_types, key=lambda x: x[1], reverse=True):
            percentage = count / total_activities * 100
            print(f"    - {action_type.capitalize():12} {count:,} ({percentage:.1f}%)")
        
        # Activity by resource
        print()
        print("  Top Resource Types:")
        
        resource_types = db.query(
            UserActivity.resource_type,
            func.count(UserActivity.id)
        ).filter(
            UserActivity.resource_type.isnot(None)
        ).group_by(UserActivity.resource_type).order_by(
            func.count(UserActivity.id).desc()
        ).limit(5).all()
        
        for resource_type, count in resource_types:
            print(f"    - {resource_type.capitalize():12} {count:,}")
        
        # Login Statistics
        print_section("LOGIN STATISTICS")
        
        total_logins = db.query(LoginHistory).count()
        logins_today = db.query(LoginHistory).filter(LoginHistory.created_at >= today_start).count()
        logins_week = db.query(LoginHistory).filter(LoginHistory.created_at >= week_start).count()
        logins_month = db.query(LoginHistory).filter(LoginHistory.created_at >= month_start).count()
        
        successful_logins = db.query(LoginHistory).filter(LoginHistory.status == 'success').count()
        failed_logins = db.query(LoginHistory).filter(LoginHistory.status == 'failed').count()
        
        print(f"  Total Logins:         {total_logins:,}")
        print(f"    - Today:            {logins_today:,}")
        print(f"    - This Week:        {logins_week:,}")
        print(f"    - This Month:       {logins_month:,}")
        print()
        print(f"  Login Success Rate:   {successful_logins/total_logins*100:.1f}%")
        print(f"    - Successful:       {successful_logins:,}")
        print(f"    - Failed:           {failed_logins:,}")
        
        # System Events
        print_section("SYSTEM EVENTS")
        
        total_events = db.query(SystemEvent).count()
        events_today = db.query(SystemEvent).filter(SystemEvent.created_at >= today_start).count()
        
        print(f"  Total Events:         {total_events:,}")
        print(f"  Events Today:         {events_today:,}")
        print()
        print("  Event Breakdown:")
        
        event_types = db.query(
            SystemEvent.event_type,
            func.count(SystemEvent.id)
        ).group_by(SystemEvent.event_type).all()
        
        for event_type, count in sorted(event_types, key=lambda x: x[1], reverse=True):
            percentage = count / total_events * 100
            print(f"    - {event_type.capitalize():12} {count:,} ({percentage:.1f}%)")
        
        # Database Size Info
        print_section("DATABASE INFO")
        
        print(f"  Table Row Counts:")
        print(f"    - users_2026_12:          {total_users:,}")
        print(f"    - individuals:            {total_individuals:,}")
        print(f"    - organizations:          {total_organizations:,}")
        print(f"    - adminstrators_shaqyru1: {total_admins:,}")
        print(f"    - user_activities:        {total_activities:,}")
        print(f"    - login_history:          {total_logins:,}")
        print(f"    - system_events:          {total_events:,}")
        
        total_rows = (total_users + total_individuals + total_organizations + 
                     total_admins + total_activities + total_logins + total_events)
        print()
        print(f"  Total Analytics Rows: {total_rows:,}")
        
        # Date Range
        print_section("DATA RANGE")
        
        oldest_user = db.query(func.min(User.created_at)).scalar()
        newest_user = db.query(func.max(User.created_at)).scalar()
        oldest_activity = db.query(func.min(UserActivity.created_at)).scalar()
        newest_activity = db.query(func.max(UserActivity.created_at)).scalar()
        
        if oldest_user and newest_user:
            print(f"  User Registrations:")
            print(f"    - Oldest: {oldest_user.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    - Newest: {newest_user.strftime('%Y-%m-%d %H:%M:%S')}")
            days_span = (newest_user - oldest_user).days
            print(f"    - Span:   {days_span} days")
        
        if oldest_activity and newest_activity:
            print()
            print(f"  Activity Data:")
            print(f"    - Oldest: {oldest_activity.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    - Newest: {newest_activity.strftime('%Y-%m-%d %H:%M:%S')}")
            days_span = (newest_activity - oldest_activity).days
            print(f"    - Span:   {days_span} days")
        
        print_separator()
        print()
        print("  📊 View analytics dashboard at:")
        print("     http://localhost:3001/kz/admin/analytics")
        print()
        print("  📚 API documentation at:")
        print("     http://localhost:8000/docs")
        print()
        print_separator()
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    view_stats()
