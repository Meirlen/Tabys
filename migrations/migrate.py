#!/usr/bin/env python3
"""
Database Migration Runner for Tabys
Runs SQL migrations against the PostgreSQL database
"""

import os
import sys
import psycopg2
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.config import settings
    DB_CONFIG = {
        'dbname': settings.postgres_db,
        'user': settings.postgres_user,
        'password': settings.postgres_password,
        'host': settings.postgres_host,
        'port': settings.postgres_port
    }
except ImportError:
    # Fallback to environment variables
    DB_CONFIG = {
        'dbname': os.getenv('POSTGRES_DB', 'alem'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432')
    }


class MigrationRunner:
    def __init__(self):
        self.migrations_dir = Path(__file__).parent
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to database: {DB_CONFIG['dbname']}")
            return True
        except psycopg2.Error as e:
            print(f"❌ Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Disconnected from database")

    def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW(),
                    description TEXT
                );
            """)
            self.conn.commit()
            print("✅ Migrations table ready")
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"❌ Failed to create migrations table: {e}")
            return False

    def is_migration_applied(self, migration_name):
        """Check if a migration has already been applied"""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM migrations WHERE migration_name = %s",
                (migration_name,)
            )
            count = self.cursor.fetchone()[0]
            return count > 0
        except psycopg2.Error as e:
            print(f"⚠️  Error checking migration status: {e}")
            return False

    def run_sql_file(self, sql_file):
        """Execute SQL commands from a file"""
        try:
            with open(sql_file, 'r') as f:
                sql = f.read()

            # Execute the SQL
            self.cursor.execute(sql)
            return True
        except psycopg2.Error as e:
            print(f"❌ SQL execution failed: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ Migration file not found: {sql_file}")
            return False

    def apply_migration(self, migration_file):
        """Apply a single migration"""
        migration_name = migration_file.stem.replace('_rollback', '')

        # Check if already applied
        if self.is_migration_applied(migration_name):
            print(f"⏭️  Migration '{migration_name}' already applied, skipping...")
            return True

        print(f"\n🚀 Applying migration: {migration_name}")

        try:
            # Run the SQL file
            if not self.run_sql_file(migration_file):
                self.conn.rollback()
                return False

            # Extract description from SQL file comments
            with open(migration_file, 'r') as f:
                first_lines = f.read().split('\n')[:5]
                description = next(
                    (line.replace('-- Description:', '').strip()
                     for line in first_lines if 'Description:' in line),
                    'No description'
                )

            # Record migration in database
            self.cursor.execute(
                """
                INSERT INTO migrations (migration_name, description)
                VALUES (%s, %s)
                """,
                (migration_name, description)
            )

            # Commit the transaction
            self.conn.commit()
            print(f"✅ Migration '{migration_name}' applied successfully!")
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to apply migration '{migration_name}': {e}")
            return False

    def rollback_migration(self, migration_name):
        """Rollback a migration"""
        rollback_file = self.migrations_dir / f"{migration_name}_rollback.sql"

        if not rollback_file.exists():
            print(f"❌ Rollback file not found: {rollback_file}")
            return False

        if not self.is_migration_applied(migration_name):
            print(f"⚠️  Migration '{migration_name}' is not applied, nothing to rollback")
            return True

        print(f"\n↩️  Rolling back migration: {migration_name}")

        try:
            # Run the rollback SQL file
            if not self.run_sql_file(rollback_file):
                self.conn.rollback()
                return False

            # Remove migration record
            self.cursor.execute(
                "DELETE FROM migrations WHERE migration_name = %s",
                (migration_name,)
            )

            # Commit the transaction
            self.conn.commit()
            print(f"✅ Migration '{migration_name}' rolled back successfully!")
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to rollback migration '{migration_name}': {e}")
            return False

    def list_migrations(self):
        """List all available migrations and their status"""
        print("\n📋 Available Migrations:\n")

        # Get all migration files (excluding rollback files)
        migration_files = sorted(
            [f for f in self.migrations_dir.glob("*.sql")
             if not f.name.endswith('_rollback.sql')]
        )

        if not migration_files:
            print("No migration files found.")
            return

        try:
            # Get applied migrations
            self.cursor.execute(
                "SELECT migration_name, applied_at FROM migrations ORDER BY applied_at"
            )
            applied = {row[0]: row[1] for row in self.cursor.fetchall()}

            for migration_file in migration_files:
                migration_name = migration_file.stem
                status = "✅ Applied" if migration_name in applied else "⏳ Pending"
                applied_at = f" ({applied[migration_name]})" if migration_name in applied else ""

                print(f"{status:15} {migration_name}{applied_at}")

        except psycopg2.Error as e:
            print(f"❌ Error listing migrations: {e}")

    def run_pending_migrations(self):
        """Run all pending migrations"""
        print("\n🔍 Checking for pending migrations...")

        # Get all migration files (excluding rollback files)
        migration_files = sorted(
            [f for f in self.migrations_dir.glob("*.sql")
             if not f.name.endswith('_rollback.sql')]
        )

        if not migration_files:
            print("No migration files found.")
            return True

        pending_count = 0
        for migration_file in migration_files:
            if not self.is_migration_applied(migration_file.stem):
                if not self.apply_migration(migration_file):
                    return False
                pending_count += 1

        if pending_count == 0:
            print("\n✅ No pending migrations. Database is up to date!")
        else:
            print(f"\n✅ Successfully applied {pending_count} migration(s)!")

        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Database Migration Runner')
    parser.add_argument(
        'command',
        choices=['migrate', 'rollback', 'list', 'status'],
        help='Command to execute'
    )
    parser.add_argument(
        '--migration',
        help='Specific migration name (for rollback)'
    )

    args = parser.parse_args()

    runner = MigrationRunner()

    # Connect to database
    if not runner.connect():
        sys.exit(1)

    # Create migrations table
    if not runner.create_migrations_table():
        runner.disconnect()
        sys.exit(1)

    # Execute command
    success = True

    if args.command == 'migrate':
        success = runner.run_pending_migrations()

    elif args.command == 'rollback':
        if not args.migration:
            print("❌ Please specify migration name with --migration")
            success = False
        else:
            success = runner.rollback_migration(args.migration)

    elif args.command in ['list', 'status']:
        runner.list_migrations()

    # Disconnect
    runner.disconnect()

    if not success:
        print("\n❌ Migration failed!")
        sys.exit(1)

    print("\n🎉 Done!")
    sys.exit(0)


if __name__ == '__main__':
    main()
