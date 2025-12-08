"""
Test script for Mobizon SMS API integration
Run this to test the Mobizon service before starting the full application
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mobizon_service import MobizonService

def test_mobizon_connection():
    """Test basic Mobizon API connection"""
    print("=" * 60)
    print("Testing Mobizon SMS API Integration")
    print("=" * 60)

    try:
        # Initialize service
        print("\n1. Initializing Mobizon service...")
        mobizon = MobizonService()
        print("✓ Service initialized successfully")

        # Check balance
        print("\n2. Checking SMS balance...")
        balance = mobizon.check_balance()

        if balance is not None:
            print(f"✓ Balance check successful: {balance} KZT")
        else:
            print("✗ Failed to retrieve balance")
            print("  Please check your API key in .env file")
            return False

        # Test SMS sending (with a test number - update this!)
        print("\n3. Testing SMS sending...")
        test_phone = input("Enter test phone number (format: 77051234567) or press Enter to skip: ").strip()

        if test_phone:
            test_otp = "123456"
            result = mobizon.send_otp(test_phone, test_otp)

            if result.get("success"):
                print(f"✓ SMS sent successfully")
                print(f"  Message ID: {result.get('message_id')}")
            else:
                print(f"✗ SMS sending failed: {result.get('message')}")
                return False
        else:
            print("  Skipping SMS sending test")

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        print("\nPlease ensure:")
        print("  1. .env file exists with MOBIZON_API_KEY")
        print("  2. API key is valid")
        print("  3. requests library is installed (pip install requests)")
        return False

if __name__ == "__main__":
    success = test_mobizon_connection()
    sys.exit(0 if success else 1)
