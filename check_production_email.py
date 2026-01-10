"""
Production Email Configuration Checker

Run this script on your production server to diagnose email issues
"""

import smtplib
import socket
from email.mime.text import MIMEText
from config import get_settings
import os

def check_environment_variables():
    """Check if email environment variables are set"""
    print("\n" + "="*60)
    print("1. CHECKING ENVIRONMENT VARIABLES")
    print("="*60)

    try:
        settings = get_settings()

        vars_to_check = {
            'GMAIL_USERNAME': settings.GMAIL_USERNAME,
            'GMAIL_APP_PASSWORD': settings.GMAIL_APP_PASSWORD,
            'GMAIL_SMTP_SERVER': settings.GMAIL_SMTP_SERVER,
            'GMAIL_SMTP_PORT': settings.GMAIL_SMTP_PORT,
        }

        all_set = True
        for var_name, var_value in vars_to_check.items():
            if var_value and str(var_value).strip():
                if 'PASSWORD' in var_name:
                    print(f"✓ {var_name}: {'*' * 16} (set)")
                else:
                    print(f"✓ {var_name}: {var_value}")
            else:
                print(f"✗ {var_name}: NOT SET")
                all_set = False

        return all_set
    except Exception as e:
        print(f"✗ Error reading settings: {e}")
        return False


def check_network_connectivity():
    """Check if server can reach Gmail SMTP server"""
    print("\n" + "="*60)
    print("2. CHECKING NETWORK CONNECTIVITY")
    print("="*60)

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    print(f"Testing connection to {smtp_server}:{smtp_port}...")

    try:
        # Test DNS resolution
        ip_address = socket.gethostbyname(smtp_server)
        print(f"✓ DNS Resolution: {smtp_server} -> {ip_address}")

        # Test TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((smtp_server, smtp_port))
        sock.close()

        if result == 0:
            print(f"✓ Port {smtp_port} is OPEN and reachable")
            return True
        else:
            print(f"✗ Port {smtp_port} is BLOCKED or unreachable")
            print(f"  Error code: {result}")
            print("\n  Possible causes:")
            print("  - Firewall blocking outbound SMTP")
            print("  - Network security group blocking port 587")
            print("  - ISP blocking SMTP ports")
            return False

    except socket.gaierror as e:
        print(f"✗ DNS Resolution failed: {e}")
        print("  Check your internet connection")
        return False
    except socket.timeout:
        print(f"✗ Connection timeout")
        print("  Network might be blocking the connection")
        return False
    except Exception as e:
        print(f"✗ Network error: {e}")
        return False


def test_smtp_authentication():
    """Test SMTP authentication with Gmail"""
    print("\n" + "="*60)
    print("3. TESTING SMTP AUTHENTICATION")
    print("="*60)

    try:
        settings = get_settings()

        if not settings.GMAIL_USERNAME or not settings.GMAIL_APP_PASSWORD:
            print("✗ Cannot test - credentials not configured")
            return False

        print(f"Connecting to {settings.GMAIL_SMTP_SERVER}:{settings.GMAIL_SMTP_PORT}...")

        server = smtplib.SMTP(settings.GMAIL_SMTP_SERVER, settings.GMAIL_SMTP_PORT, timeout=30)
        server.set_debuglevel(0)  # Set to 1 for verbose output

        print("✓ Connected to SMTP server")

        server.starttls()
        print("✓ TLS encryption enabled")

        server.login(settings.GMAIL_USERNAME, settings.GMAIL_APP_PASSWORD)
        print("✓ Authentication successful")

        server.quit()
        print("✓ SMTP test completed successfully")

        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        print("\n  Possible causes:")
        print("  - Wrong username or app password")
        print("  - App password not generated (need 2FA enabled)")
        print("  - Gmail account blocked/suspended")
        print("\n  Solutions:")
        print("  1. Verify GMAIL_USERNAME is correct email")
        print("  2. Generate new app password: https://myaccount.google.com/apppasswords")
        print("  3. Check Gmail account for security alerts")
        return False

    except smtplib.SMTPException as e:
        print(f"✗ SMTP error: {e}")
        return False

    except socket.timeout:
        print("✗ Connection timeout")
        print("  SMTP server not responding - check firewall")
        return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_test_email():
    """Send an actual test email"""
    print("\n" + "="*60)
    print("4. SENDING TEST EMAIL")
    print("="*60)

    try:
        settings = get_settings()

        # Ask for test recipient
        test_email = input("\nEnter email address to receive test (or press Enter to skip): ").strip()

        if not test_email:
            print("Skipping test email send")
            return None

        print(f"\nSending test email to {test_email}...")

        # Create test message
        msg = MIMEText("This is a test email from SARYARQA JASTARY production server.\n\nIf you received this, email configuration is working correctly!")
        msg['Subject'] = "Test Email - SARYARQA JASTARY Production"
        msg['From'] = f"{settings.GMAIL_FROM_NAME} <{settings.GMAIL_USERNAME}>"
        msg['To'] = test_email

        # Send email
        server = smtplib.SMTP(settings.GMAIL_SMTP_SERVER, settings.GMAIL_SMTP_PORT, timeout=30)
        server.starttls()
        server.login(settings.GMAIL_USERNAME, settings.GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"✓ Test email sent successfully to {test_email}")
        print("  Check the inbox (and spam folder)")
        return True

    except Exception as e:
        print(f"✗ Failed to send test email: {e}")
        return False


def check_server_info():
    """Display server information"""
    print("\n" + "="*60)
    print("SERVER INFORMATION")
    print("="*60)

    print(f"Hostname: {socket.gethostname()}")
    try:
        print(f"IP Address: {socket.gethostbyname(socket.gethostname())}")
    except:
        print("IP Address: Unable to determine")

    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        print("Environment: Docker container")
    else:
        print("Environment: Direct Python")

    # Check .env file
    if os.path.exists('.env'):
        print(".env file: EXISTS")
    else:
        print(".env file: NOT FOUND (may be using environment variables)")


def main():
    print("="*60)
    print("PRODUCTION EMAIL CONFIGURATION DIAGNOSTICS")
    print("="*60)

    check_server_info()

    results = {
        "Environment Variables": check_environment_variables(),
        "Network Connectivity": check_network_connectivity(),
        "SMTP Authentication": test_smtp_authentication(),
    }

    # Only test email sending if previous tests passed
    if all(results.values()):
        results["Test Email Send"] = send_test_email()

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is None:
            status = "⊘ SKIPPED"
        elif result:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
        print(f"{status}: {test_name}")

    print("\n" + "="*60)

    if all(v for v in results.values() if v is not None):
        print("✓ ALL TESTS PASSED")
        print("\nEmail configuration is working correctly!")
        print("If moderation emails still don't send, check:")
        print("  1. Admins have email addresses in database")
        print("  2. Scheduler is running: docker-compose logs api | grep scheduler")
        print("  3. Run: python debug_scheduler.py")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nFix the failed tests above, then run again.")


if __name__ == "__main__":
    main()
