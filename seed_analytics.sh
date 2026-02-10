#!/bin/bash

# Analytics Seed Script Runner
# Quick start script for seeding analytics data

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         TABYS Analytics Data Seeding Script               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with database credentials."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
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
echo "🚀 Starting seed process..."
echo ""

# Run the seed script
python3 seed_analytics.py

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Seeding completed successfully!"
    echo ""
    echo "📊 View analytics at: http://localhost:3001/kz/admin/analytics"
    echo "📚 API docs at: http://localhost:8000/docs"
    echo ""
else
    echo ""
    echo "❌ Seeding failed. Check the error messages above."
    exit 1
fi
