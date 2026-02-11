#!/usr/bin/env python3
"""
Script to delete user account by phone number
This allows users to re-register with the same phone number

Usage:
    python delete_user_by_phone.py <phone_number>
    python delete_user_by_phone.py 77001234567
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from config import get_settings


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number by removing non-digits"""
    return ''.join(filter(str.isdigit, phone))


def delete_user_by_phone(phone_number: str, db: Session) -> bool:
    """
    Delete user account and all related data by phone number
    Returns True if successful, False if user not found
    """
    # Normalize phone number
    normalized_phone = normalize_phone_number(phone_number)

    print(f"Looking for user with phone number: {normalized_phone}")

    # Find user
    user = db.query(models.User).filter(
        models.User.phone_number == normalized_phone
    ).first()

    if not user:
        print(f"❌ User not found with phone number: {normalized_phone}")
        return False

    print(f"✓ Found user: ID={user.id}, Type={user.user_type}, Phone={user.phone_number}")

    try:
        # Delete related Individual data if exists
        if user.user_type == "individual":
            individual = db.query(models.Individual).filter(
                models.Individual.user_id == user.id
            ).first()
            if individual:
                print(f"  - Deleting Individual record (Name: {individual.full_name})")
                db.delete(individual)

        # Delete related Organization data if exists
        elif user.user_type == "organization":
            organization = db.query(models.Organization).filter(
                models.Organization.user_id == user.id
            ).first()
            if organization:
                print(f"  - Deleting Organization record (Name: {organization.name})")
                db.delete(organization)

        # Delete all OTP codes for this phone number
        otp_count = db.query(models.OtpCode).filter(
            models.OtpCode.phone_number == normalized_phone
        ).delete()
        if otp_count > 0:
            print(f"  - Deleted {otp_count} OTP code(s)")

        # Delete the user account
        print(f"  - Deleting User account (ID: {user.id})")
        db.delete(user)

        # Commit all changes
        db.commit()

        print(f"\n✅ Successfully deleted user account: {normalized_phone}")
        print("User can now re-register with this phone number.")
        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error deleting user: {str(e)}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_user_by_phone.py <phone_number>")
        print("Example: python delete_user_by_phone.py 77001234567")
        sys.exit(1)

    phone_number = sys.argv[1]

    # Confirmation prompt
    normalized = normalize_phone_number(phone_number)
    print(f"\n⚠️  WARNING: You are about to PERMANENTLY DELETE the user account with phone number: {normalized}")
    print("This action CANNOT be undone!")
    confirm = input("Type 'DELETE' to confirm: ")

    if confirm != 'DELETE':
        print("❌ Deletion cancelled.")
        sys.exit(0)

    # Create database session
    db = SessionLocal()

    try:
        success = delete_user_by_phone(phone_number, db)
        sys.exit(0 if success else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
