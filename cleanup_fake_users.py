"""
Cleanup Fake Users Script

This script removes fake/test users from the database.
It deletes the most recently created users (newest first),
assuming they are the fake users from seeding.

IMPORTANT: Handle foreign key constraints by deleting dependent data first.
"""

import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import User, Individual, Organization, Admin
from app.analytics_models import UserActivity, LoginHistory, SystemEvent
from app.project_models import ProjectFormSubmission
from app.user_telegram_models import UserTelegramLink


# Configuration
USERS_TO_DELETE = 3000


def cleanup_fake_users(db: Session, count: int = USERS_TO_DELETE):
    """
    Remove fake users (newest first) and their related data

    Args:
        db: Database session
        count: Number of users to delete (default: 3000)
    """
    print("=" * 60)
    print("CLEANUP FAKE USERS SCRIPT")
    print("=" * 60)
    print(f"Will delete: {count} users (newest first)")
    print("=" * 60)
    print()

    # Count current users
    total_users = db.query(User).count()
    print(f"Current users in database: {total_users}")

    if total_users < count:
        print(f"⚠️  WARNING: You only have {total_users} users, but requested to delete {count}")
        print(f"Will delete all {total_users} users instead.")
        count = total_users

    if total_users == 0:
        print("No users to delete!")
        return

    print(f"After deletion: {total_users - count} users will remain")
    print()

    # Confirm before proceeding
    print("⚠️  WARNING: This will permanently delete:")
    print(f"   - {count} users (and their profiles)")
    print(f"   - All related analytics data (logins, activities)")
    print(f"   - All related project submissions")
    print(f"   - All related Telegram links")
    print()
    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        return

    print()
    print("Starting cleanup...")
    print()

    # Get user IDs to delete (newest first)
    users_to_delete = db.query(User.id).order_by(User.created_at.desc()).limit(count).all()
    user_ids_to_delete = [user_id[0] for user_id in users_to_delete]

    print(f"Selected {len(user_ids_to_delete)} users for deletion")
    print()

    # Delete dependent data first (to handle foreign keys)

    # 1. Delete analytics data
    print("Deleting analytics data...")
    deleted_activities = db.query(UserActivity).filter(UserActivity.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_activities} user activities")

    deleted_logins = db.query(LoginHistory).filter(LoginHistory.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_logins} login records")

    # System events don't have FK constraint, but clean them up too
    deleted_events = db.query(SystemEvent).filter(SystemEvent.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_events} system events")

    db.commit()
    print()

    # 2. Delete project form submissions
    print("Deleting project form submissions...")
    deleted_submissions = db.query(ProjectFormSubmission).filter(ProjectFormSubmission.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_submissions} form submissions")
    db.commit()
    print()

    # 3. Delete Telegram links
    print("Deleting Telegram links...")
    deleted_telegram = db.query(UserTelegramLink).filter(UserTelegramLink.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_telegram} Telegram links")
    db.commit()
    print()

    # 4. Delete user profiles
    print("Deleting user profiles...")
    deleted_individuals = db.query(Individual).filter(Individual.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_individuals} individual profiles")

    deleted_organizations = db.query(Organization).filter(Organization.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_organizations} organization profiles")
    db.commit()
    print()

    # 5. Finally delete users
    print("Deleting users...")
    deleted_users = db.query(User).filter(User.id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_users} users")
    db.commit()
    print()

    # Final count
    remaining_users = db.query(User).count()
    print("=" * 60)
    print("CLEANUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Users deleted: {deleted_users}")
    print(f"Users remaining: {remaining_users}")
    print(f"Analytics records deleted: {deleted_activities + deleted_logins + deleted_events}")
    print(f"Form submissions deleted: {deleted_submissions}")
    print(f"Telegram links deleted: {deleted_telegram}")
    print("=" * 60)


def main():
    """Main cleanup function"""
    db = SessionLocal()

    try:
        cleanup_fake_users(db, USERS_TO_DELETE)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
