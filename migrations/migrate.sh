#!/bin/bash

# Migration Runner Script for Tabys
# This script helps run database migrations easily

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
fi

# Default values
DB_NAME=${POSTGRES_DB:-alem}
DB_USER=${POSTGRES_USER:-postgres}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

print_help() {
    echo "Database Migration Runner for Tabys"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  migrate              Run all pending migrations"
    echo "  rollback [name]      Rollback a specific migration"
    echo "  list                 List all migrations and their status"
    echo "  status               Same as list"
    echo "  docker-migrate       Run migrations in Docker container"
    echo "  help                 Show this help message"
    echo ""
    echo "Options:"
    echo "  --db-name NAME       Database name (default: $DB_NAME)"
    echo "  --db-user USER       Database user (default: $DB_USER)"
    echo "  --db-host HOST       Database host (default: $DB_HOST)"
    echo "  --db-port PORT       Database port (default: $DB_PORT)"
    echo ""
    echo "Examples:"
    echo "  $0 migrate"
    echo "  $0 list"
    echo "  $0 rollback 001_add_news_view_count"
    echo "  $0 docker-migrate"
}

run_python_migration() {
    echo -e "${BLUE}🐍 Running Python migration script...${NC}"

    cd "$PROJECT_DIR"

    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    python3 migrations/migrate.py "$@"
}

run_docker_migration() {
    echo -e "${BLUE}🐳 Running migrations in Docker container...${NC}"

    cd "$PROJECT_DIR"

    # Check if Docker containers are running
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Docker containers not running. Starting them...${NC}"
        docker-compose up -d
        sleep 5
    fi

    # Run migration in Docker
    docker-compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -f /migrations/001_add_news_view_count.sql

    echo -e "${GREEN}✅ Migration completed in Docker${NC}"
}

run_sql_migration() {
    local migration_file="$1"

    echo -e "${BLUE}📄 Running SQL migration: $migration_file${NC}"

    if [ ! -f "$SCRIPT_DIR/$migration_file" ]; then
        echo -e "${RED}❌ Migration file not found: $migration_file${NC}"
        exit 1
    fi

    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/$migration_file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Migration completed successfully${NC}"
    else
        echo -e "${RED}❌ Migration failed${NC}"
        exit 1
    fi
}

# Parse command
COMMAND=${1:-help}

case "$COMMAND" in
    migrate)
        shift
        run_python_migration migrate "$@"
        ;;

    rollback)
        shift
        MIGRATION_NAME=$1
        if [ -z "$MIGRATION_NAME" ]; then
            echo -e "${RED}❌ Please specify migration name${NC}"
            echo "Usage: $0 rollback MIGRATION_NAME"
            exit 1
        fi
        run_python_migration rollback --migration "$MIGRATION_NAME"
        ;;

    list|status)
        run_python_migration list
        ;;

    docker-migrate)
        run_docker_migration
        ;;

    sql)
        shift
        SQL_FILE=${1:-001_add_news_view_count.sql}
        run_sql_migration "$SQL_FILE"
        ;;

    help|--help|-h)
        print_help
        ;;

    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac
