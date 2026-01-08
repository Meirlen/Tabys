#!/bin/bash

# =====================================================
# Run Moderation System Migrations
# =====================================================

echo "========================================"
echo "Moderation System Database Migration"
echo "========================================"
echo ""

# Check if .env file exists
if [ ! -f ../.env ]; then
    echo "ERROR: .env file not found in Tabys directory"
    exit 1
fi

# Source .env file
export $(cat ../.env | grep -v '^#' | xargs)

echo "Database: $POSTGRES_DB"
echo "Host: $POSTGRES_HOST"
echo "User: $POSTGRES_USER"
echo ""

read -p "Are you sure you want to run migrations? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Migration cancelled."
    exit 0
fi

echo ""
echo "Running migrations..."
echo ""

# Run migration via Docker
docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /docker-entrypoint-initdb.d/add_moderation_fields.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Migrations completed successfully!"
    echo ""
    echo "Running verification queries..."
    echo ""

    # Run verification
    docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
    SELECT 'events_' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM events_
    UNION ALL
    SELECT 'vacancies_new_2025_' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM vacancies_new_2025_
    UNION ALL
    SELECT 'courses' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM courses
    UNION ALL
    SELECT 'projects_multi_2' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM projects_multi_2
    UNION ALL
    SELECT 'places' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM places
    UNION ALL
    SELECT 'tickets' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM tickets
    UNION ALL
    SELECT 'promo_actions' AS table_name,
           COUNT(*) AS total_rows,
           COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
    FROM promo_actions;
    "

    echo ""
    echo "✓ All existing data has been marked as 'approved'"
    echo ""
    echo "Next steps:"
    echo "1. Update Python models (models.py, project_models.py, leisure_models.py)"
    echo "2. Restart the FastAPI application"
    echo ""
else
    echo ""
    echo "✗ Migration failed!"
    echo "Please check the error messages above"
    exit 1
fi
