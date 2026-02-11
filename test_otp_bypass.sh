#!/bin/bash

# Test OTP Bypass Feature
# This script demonstrates the OTP bypass functionality

echo "======================================"
echo "OTP Bypass Test Script"
echo "======================================"
echo ""

# Test phone number (must exist in database)
PHONE="77474334661"
BYPASS_CODE="950826"
API_URL="http://localhost:8000"

echo "Step 1: Requesting OTP for phone: $PHONE"
echo "--------------------------------------"
curl -s -X POST "$API_URL/api/v2/auth/check-profile" \
  -H "Content-Type: application/json" \
  -d "{\"phone_number\": \"$PHONE\"}" | jq '.'

echo ""
echo ""
echo "Step 2: Verifying with BYPASS code: $BYPASS_CODE"
echo "--------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL/api/v2/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{\"phone_number\": \"$PHONE\", \"code\": \"$BYPASS_CODE\"}")

echo "$RESPONSE" | jq '.'

# Check if we got a token
if echo "$RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    echo ""
    echo "✅ SUCCESS! OTP Bypass is working!"
    echo ""
    echo "Access Token received:"
    echo "$RESPONSE" | jq -r '.access_token' | head -c 50
    echo "..."
else
    echo ""
    echo "❌ FAILED! OTP Bypass is not working."
    echo "Check the response above for error details."
fi

echo ""
echo "======================================"
echo "Test Complete"
echo "======================================"
