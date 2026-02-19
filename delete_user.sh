#!/bin/bash
# Script to delete user by phone number (Docker version)
# Usage: ./delete_user.sh <phone_number>

if [ -z "$1" ]; then
    echo "Usage: ./delete_user.sh <phone_number>"
    echo "Example: ./delete_user.sh 77001234567"
    exit 1
fi

PHONE_NUMBER=$1

echo "Executing delete script inside Docker container..."
docker-compose exec api python delete_user_by_phone.py "$PHONE_NUMBER"
