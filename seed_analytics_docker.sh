#!/bin/bash

# Analytics Seed Script Runner for Docker Environment
# Quick start script for seeding analytics data in Docker

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         TABYS Analytics Data Seeding (Docker)              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Check if the API container is running
if ! docker-compose ps api | grep -q "Up"; then
    echo "⚠️  Warning: API container is not running."
    echo "Starting Docker Compose services..."
    docker-compose up -d
    echo "Waiting for services to be ready..."
    sleep 5
fi

echo "📋 Configuration:"
echo "   - Total Users: 7,420 (~7,370 individuals, ~50 organizations)"
echo "   - Daily Active: 200-300"
echo "   - History: 90 days"
echo ""

# Ask for confirmation
read -p "⚠️  This will DELETE existing analytics data. Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting seed process in Docker container..."
echo ""

# Run the seed script inside the Docker container
docker-compose exec -T api python seed_analytics.py

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Seeding completed successfully!"
    echo ""
    echo "📊 View analytics at: http://localhost:3001/kz/admin/analytics"
    echo "📚 API docs at: http://localhost:8000/docs"
    echo ""
    echo "To view current stats, run:"
    echo "   docker-compose exec api python view_analytics_stats.py"
    echo ""
else
    echo ""
    echo "❌ Seeding failed. Check the error messages above."
    echo ""
    echo "To debug, check Docker logs:"
    echo "   docker-compose logs api"
    exit 1
fi
