"""
Debug script to check scheduler state and trigger notification manually
"""

import asyncio
from app.database import SessionLocal
from app.moderation_notification_scheduler import (
    get_total_pending_count,
    get_admin_emails,
    check_and_notify_moderation
)
from app.moderation_notification_models import ModerationNotificationState

def check_notification_state():
    """Check the current notification state"""
    print("\n=== Moderation Notification State ===")
    db = SessionLocal()
    try:
        state = ModerationNotificationState.get_or_create(db)

        print(f"Last pending count: {state.last_pending_count}")
        print(f"Last notified at: {state.last_notified_at}")

        current_pending = get_total_pending_count(db)
        print(f"\nCurrent pending count: {current_pending}")

        should_notify = state.should_notify(current_pending)
        print(f"Should notify: {should_notify}")

        if not should_notify:
            print("\nReason: Notification won't trigger because:")
            if current_pending == 0:
                print("  - No pending items")
            elif current_pending <= state.last_pending_count:
                print(f"  - Current count ({current_pending}) is not greater than last count ({state.last_pending_count})")
            print("\n  To reset state and force notification:")
            print("  1. Add a new pending item, OR")
            print("  2. Reset the state with: reset_state()")

        admin_emails = get_admin_emails(db)
        print(f"\nAdmins with emails: {len(admin_emails)}")
        for email in admin_emails:
            print(f"  - {email}")

    finally:
        db.close()

def reset_state():
    """Reset notification state to force next check to send"""
    print("\n=== Resetting Notification State ===")
    db = SessionLocal()
    try:
        state = ModerationNotificationState.get_or_create(db)
        state.last_pending_count = 0
        state.last_notified_at = None
        db.commit()
        print("✓ State reset! Next check will send notification if there are pending items.")
    finally:
        db.close()

async def trigger_notification_now():
    """Manually trigger notification check"""
    print("\n=== Triggering Notification Check ===")
    db = SessionLocal()
    try:
        result = await check_and_notify_moderation(db)
        if result:
            print("✓ Notification sent successfully!")
        else:
            print("✗ Notification was not sent (check logs above)")
    finally:
        db.close()

async def main():
    print("="*60)
    print("MODERATION NOTIFICATION SCHEDULER DEBUG")
    print("="*60)

    # Check current state
    check_notification_state()

    # Ask user what to do
    print("\n" + "="*60)
    print("Options:")
    print("  1. Trigger notification check now")
    print("  2. Reset state and trigger")
    print("  3. Just reset state")
    print("="*60)

    choice = input("\nEnter choice (1/2/3) or press Enter to exit: ").strip()

    if choice == "1":
        await trigger_notification_now()
    elif choice == "2":
        reset_state()
        await trigger_notification_now()
    elif choice == "3":
        reset_state()
    else:
        print("Exiting...")

if __name__ == "__main__":
    asyncio.run(main())
