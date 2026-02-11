"""
Identify Fake Users Script

This script helps identify which users are likely fake/test users
by analyzing their data patterns.
"""

import sys
import os
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Individual, Organization


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


def identify_fake_users(db: Session):
    """Identify users that are likely fake based on patterns"""
    print("=" * 80)
    print("FAKE USER IDENTIFICATION")
    print("=" * 80)
    print()

    total_users = db.query(User).count()
    print(f"Total users in database: {total_users}")
    print()

    # Strategy 1: Check by fake names
    print("Checking for users with fake names from seed script...")
    print()

    fake_user_ids = set()

    # Check individuals
    individuals = db.query(Individual).all()
    fake_individuals = [ind for ind in individuals if ind.full_name in FAKE_NAMES]

    print(f"Found {len(fake_individuals)} individuals with fake names:")
    for ind in fake_individuals[:10]:  # Show first 10
        user = db.query(User).filter(User.id == ind.user_id).first()
        print(f"  - ID: {ind.user_id}, Name: {ind.full_name}, Phone: {user.phone_number if user else 'N/A'}, Created: {user.created_at if user else 'N/A'}")
        fake_user_ids.add(ind.user_id)

    if len(fake_individuals) > 10:
        print(f"  ... and {len(fake_individuals) - 10} more")
    print()

    # Check organizations
    organizations = db.query(Organization).all()
    fake_orgs = [org for org in organizations if org.name in FAKE_ORG_NAMES]

    print(f"Found {len(fake_orgs)} organizations with fake names:")
    for org in fake_orgs[:10]:  # Show first 10
        user = db.query(User).filter(User.id == org.user_id).first()
        print(f"  - ID: {org.user_id}, Name: {org.name}, Phone: {user.phone_number if user else 'N/A'}, Created: {user.created_at if user else 'N/A'}")
        fake_user_ids.add(org.user_id)

    if len(fake_orgs) > 10:
        print(f"  ... and {len(fake_orgs) - 10} more")
    print()

    print("=" * 80)
    print(f"TOTAL FAKE USERS IDENTIFIED: {len(fake_user_ids)}")
    print("=" * 80)
    print()

    # Show some real users for comparison
    print("Sample of users NOT identified as fake (likely real users):")
    all_user_ids = set(u.id for u in db.query(User.id).all())
    real_user_ids = all_user_ids - fake_user_ids

    for user_id in list(real_user_ids)[:10]:
        user = db.query(User).filter(User.id == user_id).first()
        individual = db.query(Individual).filter(Individual.user_id == user_id).first()
        org = db.query(Organization).filter(Organization.user_id == user_id).first()

        name = individual.full_name if individual else (org.name if org else "N/A")
        print(f"  - ID: {user.id}, Name: {name}, Phone: {user.phone_number}, Created: {user.created_at}")

    if len(real_user_ids) > 10:
        print(f"  ... and {len(real_user_ids) - 10} more")
    print()

    print("=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print()
    print(f"✓ Identified {len(fake_user_ids)} fake users based on name patterns")
    print(f"✓ {len(real_user_ids)} users appear to be real (different names)")
    print()
    print("To delete ONLY the identified fake users, I can create a targeted cleanup script.")
    print("This will be MUCH SAFER than deleting by date!")
    print()

    return fake_user_ids


def main():
    db = SessionLocal()
    try:
        fake_ids = identify_fake_users(db)

        # Save to file for reference
        with open('/tmp/fake_user_ids.txt', 'w') as f:
            f.write('\n'.join(str(uid) for uid in fake_ids))
        print(f"Fake user IDs saved to: /tmp/fake_user_ids.txt")

    finally:
        db.close()


if __name__ == "__main__":
    main()
