"""
Delete Identified Fake Users Script

This script deletes ONLY users that match the fake name patterns
from the seed script. This is MUCH SAFER than deleting by date.
"""

import sys
import os
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Individual, Organization
from app.analytics_models import UserActivity, LoginHistory, SystemEvent
from app.project_models import ProjectFormSubmission
from app.user_telegram_models import UserTelegramLink


# Fake names from the seed script
FAKE_NAMES = [
    "Айдос Нурланов", "Жанар Сабитова", "Асель Канатова", "Ерлан Болатов", "Динара Алмасова",
    "Арман Ержанов", "Гульнур Даулетова", "Бекзат Нурболов", "Айгерим Сериков", "Данияр Муратов",
    "Самал Акжолова", "Нурлан Ганиев", "Айым Темирова", "Бауыржан Жаксылыков", "Сауле Асемова"
]

FAKE_ORG_NAMES = [
    "ТОО 'Сарыарқа Даму'", "ЖШС 'Нұр Технология'", "АО 'Қазақстан Инновация'",
    "ТОО 'Жастар Орталығы'", "ЖШС 'Алтын Білім'", "АО 'Астана Цифр'",
    "ТОО 'Қызылорда Спорт'", "ЖШС 'Атырау Мәдениет'", "АО 'Ақтөбе Жастар'"
]


def delete_fake_users(db: Session, limit: int = None):
    """
    Delete users that match fake name patterns from seed script

    Args:
        db: Database session
        limit: Maximum number of users to delete (None = delete all identified fake users)
    """
    print("=" * 80)
    print("DELETE IDENTIFIED FAKE USERS")
    print("=" * 80)
    print()

    # Identify fake users by name patterns
    fake_user_ids = set()

    # Find individuals with fake names
    individuals = db.query(Individual).all()
    for ind in individuals:
        if ind.full_name in FAKE_NAMES:
            fake_user_ids.add(ind.user_id)

    # Find organizations with fake names
    organizations = db.query(Organization).all()
    for org in organizations:
        if org.name in FAKE_ORG_NAMES:
            fake_user_ids.add(org.user_id)

    total_fake = len(fake_user_ids)
    print(f"Identified {total_fake} fake users based on name patterns")

    if total_fake == 0:
        print("No fake users found to delete!")
        return

    # Apply limit if specified
    if limit and limit < total_fake:
        print(f"Limiting deletion to {limit} users (out of {total_fake} identified)")
        user_ids_to_delete = list(fake_user_ids)[:limit]
    else:
        user_ids_to_delete = list(fake_user_ids)
        print(f"Will delete all {total_fake} identified fake users")

    total_users = db.query(User).count()
    print(f"Current total users: {total_users}")
    print(f"After deletion: {total_users - len(user_ids_to_delete)} users will remain")
    print()

    # Show sample of users to be deleted
    print("Sample of users to be deleted:")
    for user_id in user_ids_to_delete[:10]:
        user = db.query(User).filter(User.id == user_id).first()
        individual = db.query(Individual).filter(Individual.user_id == user_id).first()
        org = db.query(Organization).filter(Organization.user_id == user_id).first()

        name = individual.full_name if individual else (org.name if org else "N/A")
        print(f"  - ID: {user.id}, Name: {name}, Phone: {user.phone_number}")

    if len(user_ids_to_delete) > 10:
        print(f"  ... and {len(user_ids_to_delete) - 10} more")
    print()

    # Confirm
    print("⚠️  WARNING: This will permanently delete:")
    print(f"   - {len(user_ids_to_delete)} users with FAKE NAMES from seed script")
    print(f"   - All their related data (analytics, submissions, etc.)")
    print()
    print("✓ Users with DIFFERENT NAMES will be PRESERVED")
    print()
    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() != 'yes':
        print("Deletion cancelled.")
        return

    print()
    print("Deleting fake users and related data...")
    print()

    # Delete dependent data first

    # 1. Analytics data
    print("Deleting analytics data...")
    deleted_activities = db.query(UserActivity).filter(UserActivity.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    deleted_logins = db.query(LoginHistory).filter(LoginHistory.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    deleted_events = db.query(SystemEvent).filter(SystemEvent.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_activities} activities, {deleted_logins} logins, {deleted_events} events")
    db.commit()

    # 2. Project submissions
    print("Deleting project form submissions...")
    deleted_submissions = db.query(ProjectFormSubmission).filter(ProjectFormSubmission.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_submissions} submissions")
    db.commit()

    # 3. Telegram links
    print("Deleting Telegram links...")
    deleted_telegram = db.query(UserTelegramLink).filter(UserTelegramLink.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_telegram} Telegram links")
    db.commit()

    # 4. User profiles
    print("Deleting user profiles...")
    deleted_individuals = db.query(Individual).filter(Individual.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    deleted_organizations = db.query(Organization).filter(Organization.user_id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_individuals} individuals, {deleted_organizations} organizations")
    db.commit()

    # 5. Users
    print("Deleting users...")
    deleted_users = db.query(User).filter(User.id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    print(f"  ✓ Deleted {deleted_users} users")
    db.commit()

    # Final summary
    remaining_users = db.query(User).count()
    print()
    print("=" * 80)
    print("DELETION COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Fake users deleted: {deleted_users}")
    print(f"Real users remaining: {remaining_users}")
    print(f"Total records deleted: {deleted_activities + deleted_logins + deleted_events + deleted_submissions + deleted_telegram + deleted_individuals + deleted_organizations + deleted_users}")
    print("=" * 80)


def main():
    db = SessionLocal()

    try:
        # Delete fake users (limit to 3000 if you want)
        # delete_fake_users(db, limit=3000)  # Limit to 3000
        delete_fake_users(db)  # Delete all identified fake users

    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
