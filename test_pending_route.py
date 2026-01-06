"""
Test script to check if the pending route is working
"""
from sqlalchemy import create_engine, inspect, text
from app.config import settings

# Create engine
engine = create_engine(settings.database_url)

# Check if approval_status column exists
with engine.connect() as conn:
    inspector = inspect(engine)
    columns = inspector.get_columns('adminstrators_shaqyru1')
    
    print("Columns in adminstrators_shaqyru1 table:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Check if approval_status column exists
    approval_status_exists = any(col['name'] == 'approval_status' for col in columns)
    
    if approval_status_exists:
        print("\n✓ approval_status column EXISTS")
        
        # Check for pending admins
        result = conn.execute(text("SELECT id, name, login, role, approval_status FROM adminstrators_shaqyru1 WHERE approval_status = 'pending'"))
        pending_admins = result.fetchall()
        
        print(f"\nPending admins count: {len(pending_admins)}")
        for admin in pending_admins:
            print(f"  - ID: {admin[0]}, Name: {admin[1]}, Login: {admin[2]}, Role: {admin[3]}, Status: {admin[4]}")
    else:
        print("\n✗ approval_status column DOES NOT EXIST")
        print("Please run the migration: migrations/003_add_admin_approval_status.sql")

print("\nDone!")
