"""
Manual trigger for moderation notification check
Run this to immediately check and send notifications without waiting for scheduler
"""
import asyncio
import sys
from app.database import SessionLocal
from app.moderation_notification_scheduler import check_and_notify_moderation

async def main():
    print("Manually triggering moderation notification check...")
    db = SessionLocal()
    try:
        result = await check_and_notify_moderation(db)
        if result:
            print("✅ Notification sent successfully!")
        else:
            print("ℹ️  No notification needed (no new items detected)")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
