"""
Test get_target_users function to debug why it returns empty list
"""
from app.database import SessionLocal
from app.broadcast_models import BroadcastTargetAudience
from app.routers.broadcasts import get_target_users

db = SessionLocal()
try:
    # Test with string value
    print("Testing with string 'admins_only'...")
    result1 = get_target_users(db, "admins_only", None)
    print(f"Result: {result1}")
    print(f"Count: {len(result1)}")

    # Test with enum value
    print("\nTesting with enum BroadcastTargetAudience.ADMINS_ONLY...")
    result2 = get_target_users(db, BroadcastTargetAudience.ADMINS_ONLY, None)
    print(f"Result: {result2}")
    print(f"Count: {len(result2)}")

    # Check what's in the database
    print("\nChecking database directly...")
    from app.telegram_otp_models import TelegramSession
    from app import models
    from app.rbac.roles import Role

    sessions = db.query(TelegramSession.telegram_user_id, models.Admin.role).join(
        models.Admin, TelegramSession.admin_id == models.Admin.id
    ).filter(
        TelegramSession.is_active == True
    ).all()

    print(f"All active sessions: {sessions}")

    # Test the specific query
    admin_sessions = db.query(TelegramSession.telegram_user_id, models.Admin.role).join(
        models.Admin, TelegramSession.admin_id == models.Admin.id
    ).filter(
        TelegramSession.is_active == True,
        models.Admin.role.in_([
            Role.SUPER_ADMIN.value,
            Role.ADMINISTRATOR.value,
            Role.GOVERNMENT.value,
            Role.NPO.value,
            Role.MSB.value,
            Role.VOLUNTEER_ADMIN.value
        ])
    ).all()

    print(f"Admin sessions: {admin_sessions}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
