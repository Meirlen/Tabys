"""
Script to reset Akbota admin password
Usage: python reset_akbota_password.py
"""
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Admin

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_password():
    # Create database connection
    DATABASE_URL = f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Find Akbota admin
        admin = db.query(Admin).filter(Admin.login == "Акбота").first()
        
        if not admin:
            print("❌ Admin 'Акбота' not found in database")
            return
        
        print(f"✅ Found admin: {admin.name} (ID: {admin.id})")
        print(f"   Login: {admin.login}")
        print(f"   Role: {admin.role}")
        print(f"   Current hashed password: {admin.password[:50]}...")
        print()
        
        # Ask for new password
        new_password = input("Enter new password for Акбота: ").strip()
        
        if not new_password:
            print("❌ Password cannot be empty")
            return
        
        confirm_password = input("Confirm new password: ").strip()
        
        if new_password != confirm_password:
            print("❌ Passwords do not match")
            return
        
        # Hash the new password
        hashed_password = pwd_context.hash(new_password)
        
        # Update in database
        admin.password = hashed_password
        db.commit()
        
        print()
        print("✅ Password successfully updated!")
        print(f"   Login: Акбота")
        print(f"   New password: {new_password}")
        print(f"   New hashed password: {hashed_password[:50]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Reset Password for Akbota Admin")
    print("=" * 60)
    print()
    reset_password()
