"""
Email Notification Service using Resend API

Handles sending email notifications using Resend.
Used for moderation notifications and other admin alerts.
"""

import logging
from typing import List, Optional
import resend
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via Resend API"""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.RESEND_API_KEY
        self.from_email = self.settings.RESEND_FROM_EMAIL
        self.from_name = self.settings.RESEND_FROM_NAME or "SARYARQA JASTARY"

        # Initialize Resend API
        if self.api_key:
            resend.api_key = self.api_key
            logger.info("Resend API initialized successfully")
        else:
            logger.warning("Resend API key not configured")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send a single email via Resend API

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body content (optional)

        Returns:
            bool: True if email sent successfully
        """
        if not self.api_key:
            logger.error("Resend API key not configured. Please set RESEND_API_KEY in .env")
            return False

        if not self.from_email:
            logger.error("From email not configured. Please set RESEND_FROM_EMAIL in .env")
            return False

        if not to_email:
            logger.warning("No recipient email provided")
            return False

        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": body_html,
            }

            # Add text version if provided
            if body_text:
                params["text"] = body_text

            # Send email via Resend API
            logger.info(f"Sending email to {to_email} via Resend API...")
            response = resend.Emails.send(params)

            if response and (isinstance(response, dict) and response.get('id')):
                logger.info(f"Email sent successfully to {to_email} (ID: {response.get('id')})")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: Invalid response")
                return False

        except resend.exceptions.ResendError as e:
            logger.error(f"Resend API error for {to_email}: {str(e)}")
            if hasattr(e, 'status_code'):
                logger.error(f"Status code: {e.status_code}")
            if hasattr(e, 'message'):
                logger.error(f"Error message: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def send_bulk_emails(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> dict:
        """
        Send the same email to multiple recipients

        Note: Resend allows up to 50 recipients per API call,
        so we send individually to track success/failure per recipient.

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body content (optional)

        Returns:
            dict: {"sent": count, "failed": count, "failed_emails": [emails]}
        """
        if not self.api_key:
            logger.error("Resend API key not configured")
            return {"sent": 0, "failed": len(recipients), "failed_emails": recipients}

        if not recipients:
            logger.warning("No recipients provided")
            return {"sent": 0, "failed": 0, "failed_emails": []}

        # Filter out None/empty emails
        valid_recipients = [email for email in recipients if email and email.strip()]

        if not valid_recipients:
            logger.warning("No valid email addresses in recipients list")
            return {"sent": 0, "failed": 0, "failed_emails": []}

        sent_count = 0
        failed_count = 0
        failed_emails = []

        logger.info(f"Sending bulk emails to {len(valid_recipients)} recipients...")

        for to_email in valid_recipients:
            try:
                success = self.send_email(to_email, subject, body_html, body_text)

                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    failed_emails.append(to_email)

            except Exception as e:
                failed_count += 1
                failed_emails.append(to_email)
                logger.error(f"Failed to send email to {to_email}: {str(e)}")

        logger.info(f"Bulk email send complete: {sent_count} sent, {failed_count} failed")

        return {
            "sent": sent_count,
            "failed": failed_count,
            "failed_emails": failed_emails
        }


def create_moderation_notification_email(pending_count: int, crm_url: str) -> tuple:
    """
    Create HTML and plain text email for moderation notification

    Args:
        pending_count: Number of pending moderation items
        crm_url: URL to the CRM moderation page

    Returns:
        tuple: (html_body, text_body)
    """
    # HTML version
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 15px;
                margin-bottom: 20px;
            }}
            .alert-icon {{
                font-size: 24px;
                margin-right: 10px;
            }}
            .count {{
                font-size: 32px;
                font-weight: bold;
                color: #007bff;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #dee2e6;
                font-size: 12px;
                color: #6c757d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="alert-icon">🚨</span>
                <strong>Новые заявки на модерацию</strong>
            </div>

            <p>Здравствуйте!</p>

            <p>В системе появились новые заявки, ожидающие модерации:</p>

            <div class="count">{pending_count} заявок</div>

            <p>Пожалуйста, проверьте их в панели администратора CRM.</p>

            <a href="{crm_url}" class="button">📋 Проверить модерацию</a>

            <div class="footer">
                <p>Это автоматическое уведомление от системы SARYARQA JASTARY.</p>
                <p>Если вы получили это письмо по ошибке, пожалуйста, проигнорируйте его.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_body = f"""
    🚨 НОВЫЕ ЗАЯВКИ НА МОДЕРАЦИЮ

    Здравствуйте!

    В системе появились новые заявки, ожидающие модерации:

    Ожидают проверки: {pending_count} заявок

    Пожалуйста, проверьте их в панели администратора CRM:
    {crm_url}

    ---
    Это автоматическое уведомление от системы SARYARQA JASTARY.
    Если вы получили это письмо по ошибке, пожалуйста, проигнорируйте его.
    """

    return (html_body, text_body)


# Create a singleton instance
email_service = EmailService()
