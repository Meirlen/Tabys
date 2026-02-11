"""
Analytics Seed Script (Non-Destructive / Additive)

This script generates realistic analytics data for the Tabys platform:
- Adds 7,420 new users (~7,370 individuals, ~50 organizations)
- ~200-300 daily active users
- Realistic activity patterns, login history, and system events
- 90 days of historical data

IMPORTANT: This script is NON-DESTRUCTIVE. It will:
✓ Keep all existing users, admins, and data
✓ Add new test users and analytics data
✓ NOT delete anything

Safe to run on any database!
"""

import sys
import os
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import User, Individual, Organization, Admin
from app.analytics_models import UserActivity, LoginHistory, SystemEvent
from app.project_models import ProjectFormSubmission
from app.user_telegram_models import UserTelegramLink


# Configuration
TOTAL_USERS = 7420
DAILY_ACTIVE_USERS_MIN = 200
DAILY_ACTIVE_USERS_MAX = 300
DAYS_OF_HISTORY = 90
ADMIN_COUNT = 15

# User types and their distribution
USER_TYPES = [
    ("individual", 0.993),  # 99.3% individuals (~7,370)
    ("organization", 0.007)  # 0.7% organizations (~50)
]

# Action types and their probability
ACTION_TYPES = [
    ("view", 0.55),      # 55% views
    ("create", 0.15),    # 15% creates
    ("update", 0.20),    # 20% updates
    ("delete", 0.03),    # 3% deletes
    ("login", 0.07),     # 7% logins
]

# Resource types for activities
RESOURCE_TYPES = [
    ("course", 0.20),
    ("event", 0.18),
    ("vacancy", 0.15),
    ("news", 0.12),
    ("project", 0.10),
    ("expert", 0.08),
    ("volunteer", 0.07),
    ("leisure", 0.05),
    ("resume", 0.05),
]

# System event types
EVENT_TYPES = [
    ("info", 0.70),
    ("warning", 0.20),
    ("error", 0.08),
    ("critical", 0.02)
]

# Sample IP addresses (for variety)
SAMPLE_IPS = [
    "192.168.1.100", "10.0.0.50", "172.16.0.25", "203.0.113.45",
    "198.51.100.78", "192.0.2.123", "185.125.190.36", "91.201.67.89"
]

# Sample user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Android 13; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
]

# Sample names for individuals
SAMPLE_NAMES_KZ = [
    "Айдос Нұрлан", "Жанар Сәбит", "Асель Қанат", "Ерлан Болат", "Динара Алмас",
    "Арман Ержан", "Гүлнұр Дәулет", "Бекзат Нұрбол", "Айгерім Серік", "Данияр Мұрат",
    "Самал Ақжол", "Нұрлан Ғани", "Айым Темір", "Бауыржан Жақсылық", "Сәуле Әсем"
]

SAMPLE_NAMES_RU = [
    "Айдос Нурланов", "Жанар Сабитова", "Асель Канатова", "Ерлан Болатов", "Динара Алмасова",
    "Арман Ержанов", "Гульнур Даулетова", "Бекзат Нурболов", "Айгерим Сериков", "Данияр Муратов",
    "Самал Акжолова", "Нурлан Ганиев", "Айым Темирова", "Бауыржан Жаксылыков", "Сауле Асемова"
]

# Sample organization names
ORG_NAMES = [
    "ТОО 'Сарыарқа Даму'", "ЖШС 'Нұр Технология'", "АО 'Қазақстан Инновация'",
    "ТОО 'Жастар Орталығы'", "ЖШС 'Алтын Білім'", "АО 'Астана Цифр'",
    "ТОО 'Қызылорда Спорт'", "ЖШС 'Атырау Мәдениет'", "АО 'Ақтөбе Жастар'"
]


def weighted_choice(choices):
    """Select item based on weights"""
    items, weights = zip(*choices)
    return random.choices(items, weights=weights, k=1)[0]


def generate_users(db: Session):
    """Generate users with realistic distribution (additive - keeps existing users)"""

    # Count existing users
    existing_user_count = db.query(User).count()
    print(f"Found {existing_user_count} existing users")

    # Get all existing phone numbers to avoid duplicates
    print("  Loading existing phone numbers...")
    existing_phones = set(phone[0] for phone in db.query(User.phone_number).all())
    print(f"  Found {len(existing_phones)} existing phone numbers to avoid")

    print(f"Adding {TOTAL_USERS} new users...")

    users_created = 0

    # Generate users over the past year with growth pattern
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)

    for i in range(TOTAL_USERS):
        # Users are distributed over time with growth (more recent = more users)
        # Using quadratic growth curve
        progress = i / TOTAL_USERS
        days_ago = int((1 - progress ** 2) * 365)
        created_at = end_date - timedelta(days=days_ago)

        user_type = weighted_choice(USER_TYPES)

        # Generate unique phone number
        max_attempts = 100
        for attempt in range(max_attempts):
            phone_number = f"+77{random.randint(700000000, 799999999)}"
            if phone_number not in existing_phones:
                existing_phones.add(phone_number)  # Track it to avoid duplicates in this batch
                break
        else:
            # If we couldn't find a unique random number, use a sequential one
            phone_number = f"+77{700000000 + existing_user_count + users_created}"
            existing_phones.add(phone_number)

        # Create user
        user = User(
            phone_number=phone_number,
            user_type=user_type,
            is_verified=random.random() > 0.1,  # 90% verified
            created_at=created_at,
            updated_at=created_at
        )
        db.add(user)
        db.flush()
        
        # Create individual or organization profile
        if user_type == "individual":
            individual = Individual(
                user_id=user.id,
                full_name=random.choice(SAMPLE_NAMES_RU),
                id_document_photo=f"/uploads/ids/id_{user.id}.jpg",
                selfie_with_id_photo=f"/uploads/selfies/selfie_{user.id}.jpg",
                address=f"г. Астана, ул. Независимости {random.randint(1, 200)}",
                person_status_id=random.randint(1, 4),
                created_at=created_at
            )
            db.add(individual)
        else:
            organization = Organization(
                user_id=user.id,
                name=random.choice(ORG_NAMES),
                bin_number=f"{random.randint(100000000000, 999999999999)}",
                organization_type_id=random.randint(1, 4),
                email=f"info{user.id}@company.kz",
                address=f"г. Алматы, пр. Абая {random.randint(1, 300)}",
                created_at=created_at
            )
            db.add(organization)
        
        users_created += 1
        if users_created % 500 == 0:
            db.commit()
            print(f"  Created {users_created} users...")

    db.commit()
    total_users = existing_user_count + TOTAL_USERS
    print(f"✓ Created {TOTAL_USERS} new users")
    print(f"✓ Total users in database: {total_users}")
    return total_users


def generate_admins(db: Session):
    """Generate admin accounts"""
    print(f"Generating {ADMIN_COUNT} admins...")
    
    existing_admins = db.query(Admin).count()
    if existing_admins >= ADMIN_COUNT:
        print(f"✓ Already have {existing_admins} admins")
        return existing_admins
    
    admins_to_create = ADMIN_COUNT - existing_admins
    for i in range(admins_to_create):
        admin = Admin(
            name=f"Admin {existing_admins + i + 1}",
            login=f"admin{existing_admins + i + 1}",
            password="hashed_password_here",  # Would be properly hashed in production
            role="administrator",
            created_at=datetime.utcnow() - timedelta(days=random.randint(180, 365))
        )
        db.add(admin)
    
    db.commit()
    print(f"✓ Created {admins_to_create} new admins (total: {ADMIN_COUNT})")
    return ADMIN_COUNT


def generate_login_history(db: Session, user_count: int, admin_count: int):
    """Generate realistic login history (additive - keeps existing history)"""
    existing_login_count = db.query(LoginHistory).count()
    print(f"Found {existing_login_count} existing login records")
    print(f"Generating login history for {DAYS_OF_HISTORY} days...")

    end_date = datetime.utcnow()
    total_logins = 0
    
    # Get all user and admin IDs
    user_ids = [u.id for u in db.query(User.id).all()]
    admin_ids = [a.id for a in db.query(Admin.id).all()]
    
    for day in range(DAYS_OF_HISTORY):
        date = end_date - timedelta(days=day)
        
        # Users who will be active this day
        daily_active = random.randint(DAILY_ACTIVE_USERS_MIN, DAILY_ACTIVE_USERS_MAX)
        active_user_ids = random.sample(user_ids, min(daily_active, len(user_ids)))
        
        # Each active user logs in 1-3 times per day
        for user_id in active_user_ids:
            login_count = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1], k=1)[0]
            
            for _ in range(login_count):
                login_time = date.replace(
                    hour=random.randint(7, 22),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                # 95% successful logins
                status = "success" if random.random() > 0.05 else "failed"
                
                login = LoginHistory(
                    user_id=user_id,
                    user_type="user",
                    phone_number=f"+77{random.randint(700000000, 799999999)}",
                    status=status,
                    failure_reason="Неверный код" if status == "failed" else None,
                    ip_address=random.choice(SAMPLE_IPS),
                    user_agent=random.choice(USER_AGENTS),
                    created_at=login_time
                )
                db.add(login)
                total_logins += 1
        
        # Admin logins (5-10 per day)
        admin_login_count = random.randint(5, 10)
        for _ in range(admin_login_count):
            admin_id = random.choice(admin_ids)
            login_time = date.replace(
                hour=random.randint(8, 18),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            login = LoginHistory(
                admin_id=admin_id,
                user_type="admin",
                login=f"admin{admin_id}",
                status="success",
                ip_address=random.choice(SAMPLE_IPS),
                user_agent=random.choice(USER_AGENTS),
                created_at=login_time
            )
            db.add(login)
            total_logins += 1
        
        if day % 10 == 0:
            db.commit()
            print(f"  Processed {day} days...")

    db.commit()
    print(f"✓ Generated {total_logins:,} new login records")
    print(f"✓ Total login records: {existing_login_count + total_logins:,}")


def generate_user_activities(db: Session, user_count: int, admin_count: int):
    """Generate realistic user activities (additive - keeps existing activities)"""
    existing_activity_count = db.query(UserActivity).count()
    print(f"Found {existing_activity_count} existing activity records")
    print(f"Generating user activities for {DAYS_OF_HISTORY} days...")

    end_date = datetime.utcnow()
    total_activities = 0
    
    # Get all user and admin IDs
    user_ids = [u.id for u in db.query(User.id).all()]
    admin_ids = [a.id for a in db.query(Admin.id).all()]
    
    for day in range(DAYS_OF_HISTORY):
        date = end_date - timedelta(days=day)
        
        # Daily active users
        daily_active = random.randint(DAILY_ACTIVE_USERS_MIN, DAILY_ACTIVE_USERS_MAX)
        active_user_ids = random.sample(user_ids, min(daily_active, len(user_ids)))
        
        # Each active user performs 3-15 actions per day
        for user_id in active_user_ids:
            action_count = random.randint(3, 15)
            
            for _ in range(action_count):
                action_time = date.replace(
                    hour=random.randint(7, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                action_type = weighted_choice(ACTION_TYPES)
                resource_type = weighted_choice(RESOURCE_TYPES)
                
                activity = UserActivity(
                    user_id=user_id,
                    user_type="user",
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=random.randint(1, 1000),
                    description=f"{action_type.capitalize()} {resource_type}",
                    ip_address=random.choice(SAMPLE_IPS),
                    user_agent=random.choice(USER_AGENTS),
                    created_at=action_time
                )
                db.add(activity)
                total_activities += 1
        
        # Admin activities (50-100 per day)
        admin_action_count = random.randint(50, 100)
        for _ in range(admin_action_count):
            admin_id = random.choice(admin_ids)
            action_time = date.replace(
                hour=random.randint(8, 18),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            action_type = weighted_choice([
                ("create", 0.25),
                ("update", 0.35),
                ("delete", 0.10),
                ("view", 0.30)
            ])
            resource_type = weighted_choice(RESOURCE_TYPES)
            
            activity = UserActivity(
                admin_id=admin_id,
                user_type="admin",
                action_type=action_type,
                resource_type=resource_type,
                resource_id=random.randint(1, 1000),
                description=f"Admin {action_type} {resource_type}",
                ip_address=random.choice(SAMPLE_IPS),
                user_agent=random.choice(USER_AGENTS),
                created_at=action_time
            )
            db.add(activity)
            total_activities += 1
        
        if day % 10 == 0:
            db.commit()
            print(f"  Processed {day} days...")

    db.commit()
    print(f"✓ Generated {total_activities:,} new activity records")
    print(f"✓ Total activity records: {existing_activity_count + total_activities:,}")


def generate_system_events(db: Session):
    """Generate system events (additive - keeps existing events)"""
    existing_event_count = db.query(SystemEvent).count()
    print(f"Found {existing_event_count} existing system events")
    print(f"Generating system events for {DAYS_OF_HISTORY} days...")

    end_date = datetime.utcnow()
    total_events = 0
    
    # Event sources
    sources = [
        "authentication", "database", "api", "scheduler", 
        "file_upload", "email_service", "payment", "moderation"
    ]
    
    # Sample messages by event type
    messages = {
        "info": [
            "Система запущена успешно",
            "Плановая очистка кэша выполнена",
            "Резервное копирование завершено",
            "Статистика обновлена"
        ],
        "warning": [
            "Высокая нагрузка на сервер",
            "Медленный запрос к базе данных",
            "Превышен лимит запросов API",
            "Низкое место на диске"
        ],
        "error": [
            "Ошибка подключения к внешнему сервису",
            "Не удалось отправить email",
            "Ошибка при загрузке файла",
            "Таймаут запроса к базе данных"
        ],
        "critical": [
            "База данных недоступна",
            "Критическая ошибка аутентификации",
            "Сбой в системе платежей",
            "Утечка памяти обнаружена"
        ]
    }
    
    for day in range(DAYS_OF_HISTORY):
        date = end_date - timedelta(days=day)
        
        # 10-30 system events per day
        daily_events = random.randint(10, 30)
        
        for _ in range(daily_events):
            event_time = date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            event_type = weighted_choice(EVENT_TYPES)
            source = random.choice(sources)
            message = random.choice(messages[event_type])
            
            event = SystemEvent(
                event_type=event_type,
                source=source,
                message=message,
                details=f"Event details for {event_type}",
                created_at=event_time
            )
            db.add(event)
            total_events += 1
        
        if day % 10 == 0:
            db.commit()
            print(f"  Processed {day} days...")

    db.commit()
    print(f"✓ Generated {total_events:,} new system events")
    print(f"✓ Total system events: {existing_event_count + total_events:,}")


def main():
    """Main seeding function"""
    print("=" * 60)
    print("TABYS ANALYTICS SEED SCRIPT (NON-DESTRUCTIVE)")
    print("=" * 60)
    print(f"Mode: ADDITIVE - Will keep all existing data")
    print(f"Adding: {TOTAL_USERS:,} users (~7,370 individuals, ~50 organizations)")
    print(f"Daily Active: {DAILY_ACTIVE_USERS_MIN}-{DAILY_ACTIVE_USERS_MAX}")
    print(f"History: {DAYS_OF_HISTORY} days")
    print("=" * 60)
    print()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Step 1: Generate users
        user_count = generate_users(db)
        print()
        
        # Step 2: Generate admins
        admin_count = generate_admins(db)
        print()
        
        # Step 3: Generate login history
        generate_login_history(db, user_count, admin_count)
        print()
        
        # Step 4: Generate user activities
        generate_user_activities(db, user_count, admin_count)
        print()
        
        # Step 5: Generate system events
        generate_system_events(db)
        print()
        
        print("=" * 60)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"✓ {TOTAL_USERS:,} new users added")
        print(f"✓ Total users in database: {user_count:,}")
        print(f"✓ {admin_count} total admins")
        print(f"✓ Login history populated (90 days)")
        print(f"✓ User activities populated (90 days)")
        print(f"✓ System events populated (90 days)")
        print()
        print("NOTE: All existing data has been preserved!")
        print()
        print("You can now view the analytics dashboard at:")
        print("http://localhost:3001/kz/admin/analytics")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
