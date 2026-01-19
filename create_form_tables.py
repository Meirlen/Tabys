"""
Migration script to create form builder tables.

This script creates the new tables needed for the form builder feature:
- project_form_templates
- project_form_submissions

Run this script if tables don't auto-create on app startup.

Usage:
    python create_form_tables.py
"""

from app.database import engine, Base
from app.project_models import ProjectFormTemplate, ProjectFormSubmission, Project
from sqlalchemy import inspect

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def create_tables():
    """Create form builder tables"""
    print("🔍 Checking existing tables...")
    
    tables_to_create = [
        ('project_form_templates', ProjectFormTemplate),
        ('project_form_submissions', ProjectFormSubmission)
    ]
    
    tables_created = []
    tables_existing = []
    
    for table_name, model in tables_to_create:
        if check_table_exists(table_name):
            print(f"✅ Table '{table_name}' already exists")
            tables_existing.append(table_name)
        else:
            print(f"📝 Creating table '{table_name}'...")
            tables_created.append(table_name)
    
    if tables_created:
        # Create only the new tables
        print("\n🚀 Creating new tables...")
        Base.metadata.create_all(bind=engine, tables=[
            ProjectFormTemplate.__table__,
            ProjectFormSubmission.__table__
        ])
        print(f"✅ Successfully created {len(tables_created)} table(s): {', '.join(tables_created)}")
    else:
        print("\n✅ All tables already exist. No migration needed.")
    
    print("\n📊 Summary:")
    print(f"   Existing tables: {len(tables_existing)}")
    print(f"   Created tables: {len(tables_created)}")
    print(f"   Total tables: {len(tables_to_create)}")
    
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    print("=" * 60)
    print("Form Builder Tables Migration")
    print("=" * 60)
    print()
    
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        print("\nPlease check:")
        print("1. Database connection settings in .env")
        print("2. Database server is running")
        print("3. User has permission to create tables")
        exit(1)
    
    print("\n" + "=" * 60)
    print("You can now start the FastAPI server:")
    print("  cd Tabys/")
    print("  docker-compose up")
    print("=" * 60)
