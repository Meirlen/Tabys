"""
Test script to debug moderation email notifications

Run this script to check if moderation email notifications are working
"""

import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.moderation_notification_scheduler import (
    get_total_pending_count,
    get_admin_emails,
    send_email_notifications
)
from app.email_service import email_service
from config import get_settings

def test_database_connection():
    """Test 1: Check database connection"""
    print("\n=== Test 1: Database Connection ===")
    try:
        db = SessionLocal()
        result = db.execute("SELECT 1").fetchone()
        print("✓ Database connection successful")
        db.close()
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_email_column_exists():
    """Test 2: Check if email column exists in admins table"""
    print("\n=== Test 2: Email Column Exists ===")
    try:
        db = SessionLocal()
        # Try to query the email column
        admin = db.query(models.Admin).first()
        if admin:
            email = getattr(admin, 'email', None)
            print(f"✓ Email column exists")
            print(f"  Sample admin email: {email if email else 'NULL'}")
        else:
            print("  Warning: No admins found in database")
        db.close()
        return True
    except AttributeError as e:
        print(f"✗ Email column does NOT exist: {e}")
        print("  Run migration: migrations/005_add_admin_email.sql")
        return False
    except Exception as e:
        print(f"✗ Error checking email column: {e}")
        return False


def test_admins_with_emails():
    """Test 3: Check if any admins have email addresses"""
    print("\n=== Test 3: Admins with Email Addresses ===")
    try:
        db = SessionLocal()
        admins = get_admin_emails(db)

        if admins:
            print(f"✓ Found {len(admins)} admin(s) with email addresses:")
            for email in admins:
                print(f"  - {email}")
        else:
            print("✗ No admins have email addresses set")
            print("  Admins need to set their email in Profile page")

            # Show admins without emails
            all_admins = db.query(models.Admin).filter(
                models.Admin.role.in_(['administrator', 'super_admin'])
            ).all()

            print(f"\n  Total admin/super_admin accounts: {len(all_admins)}")
            for admin in all_admins:
                email_status = admin.email if admin.email else "NO EMAIL"
                print(f"  - {admin.name} ({admin.login}): {email_status}")

        db.close()
        return len(admins) > 0
    except Exception as e:
        print(f"✗ Error getting admin emails: {e}")
        return False


def test_gmail_smtp_config():
    """Test 4: Check Gmail SMTP configuration"""
    print("\n=== Test 4: Gmail SMTP Configuration ===")
    try:
        settings = get_settings()

        username = settings.GMAIL_USERNAME
        password = settings.GMAIL_APP_PASSWORD

        if username and password:
            print(f"✓ Gmail SMTP configured")
            print(f"  Username: {username}")
            print(f"  Password: {'*' * len(password)} (hidden)")
        else:
            print("✗ Gmail SMTP NOT configured")
            print("  Missing environment variables:")
            if not username:
                print("  - GMAIL_USERNAME")
            if not password:
                print("  - GMAIL_APP_PASSWORD")
            print("\n  Add these to .env file and restart")

        return bool(username and password)
    except Exception as e:
        print(f"✗ Error checking SMTP config: {e}")
        return False


def test_pending_moderation_count():
    """Test 5: Check if there are pending moderation items"""
    print("\n=== Test 5: Pending Moderation Items ===")
    try:
        db = SessionLocal()
        pending_count = get_total_pending_count(db)

        if pending_count > 0:
            print(f"✓ Found {pending_count} pending moderation item(s)")
        else:
            print("  No pending moderation items")
            print("  Create a test item to trigger notification")

        db.close()
        return True
    except Exception as e:
        print(f"✗ Error checking pending items: {e}")
        return False


async def test_send_email_notification():
    """Test 6: Try to send a test email notification"""
    print("\n=== Test 6: Send Test Email Notification ===")
    try:
        db = SessionLocal()

        # Check if we have admins with emails
        admin_emails = get_admin_emails(db)
        if not admin_emails:
            print("✗ Cannot send test - no admins with email addresses")
            db.close()
            return False

        print(f"  Sending test notification to {len(admin_emails)} admin(s)...")

        # Send test notification
        result = await send_email_notifications(pending_count=5, db=db)

        if result:
            print("✓ Test email notification sent successfully")
        else:
            print("✗ Failed to send email notification")
            print("  Check application logs for details")

        db.close()
        return result
    except Exception as e:
        print(f"✗ Error sending test notification: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)

    total = len(results)
    passed = sum(results.values())

    for test_name, passed_status in results.items():
        status = "✓ PASS" if passed_status else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Email notifications should work.")
    else:
        print("\n✗ Some tests failed. Fix the issues above.")


async def main():
    """Run all diagnostic tests"""
    print("="*50)
    print("MODERATION EMAIL NOTIFICATION DIAGNOSTICS")
    print("="*50)

    results = {}

    # Run tests
    results["Database Connection"] = test_database_connection()
    results["Email Column Exists"] = test_email_column_exists()
    results["Admins with Emails"] = test_admins_with_emails()
    results["Gmail SMTP Config"] = test_gmail_smtp_config()
    results["Pending Items Check"] = test_pending_moderation_count()
    results["Send Test Email"] = await test_send_email_notification()

    # Print summary
    print_summary(results)

    print("\n" + "="*50)
    print("NEXT STEPS")
    print("="*50)

    if not results["Email Column Exists"]:
        print("\n1. Run database migration:")
        print("   docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}")
        print("   Then run: \\i /migrations/005_add_admin_email.sql")

    if not results["Admins with Emails"]:
        print("\n2. Add email addresses to admin accounts:")
        print("   - Log in to CRM as admin")
        print("   - Go to Profile page")
        print("   - Add your email address")

    if not results["Gmail SMTP Config"]:
        print("\n3. Configure Gmail SMTP in .env:")
        print("   GMAIL_USERNAME=your-email@gmail.com")
        print("   GMAIL_APP_PASSWORD=your-app-password")
        print("   Then restart: docker-compose restart api")

    print("\n4. Check logs for errors:")
    print("   docker-compose logs -f api | grep -i email")


if __name__ == "__main__":
    asyncio.run(main())
