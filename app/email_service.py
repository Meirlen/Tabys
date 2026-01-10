"""
Email Notification Service

Handles sending email notifications using Gmail SMTP server.
Used for moderation notifications and other admin alerts.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via Gmail SMTP"""

    def __init__(self):
        self.settings = get_settings()
        self.smtp_server = self.settings.GMAIL_SMTP_SERVER
        self.smtp_port = self.settings.GMAIL_SMTP_PORT
        self.username = self.settings.GMAIL_USERNAME
        self.password = self.settings.GMAIL_APP_PASSWORD
        self.from_name = self.settings.GMAIL_FROM_NAME

    def _create_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """
        Create and return an authenticated SMTP connection

        Returns:
            SMTP connection or None if connection fails
        """
        try:
            # Create SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption

            # Login to Gmail
            server.login(self.username, self.password)

            logger.info("SMTP connection established successfully")
            return server

        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {str(e)}")
            return None

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send a single email

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body content (optional, will use HTML if not provided)

        Returns:
            bool: True if email sent successfully
        """
        if not self.username or not self.password:
            logger.error("Gmail credentials not configured. Please set GMAIL_USERNAME and GMAIL_APP_PASSWORD in .env")
            return False

        if not to_email:
            logger.warning("No recipient email provided")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.username}>"
            message["To"] = to_email

            # Add plain text version (fallback)
            if body_text:
                part1 = MIMEText(body_text, "plain")
                message.attach(part1)

            # Add HTML version
            part2 = MIMEText(body_html, "html")
            message.attach(part2)

            # Create SMTP connection and send
            server = self._create_smtp_connection()
            if not server:
                return False

            server.sendmail(self.username, to_email, message.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
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

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body content (optional)

        Returns:
            dict: {"sent": count, "failed": count, "failed_emails": [emails]}
        """
        if not self.username or not self.password:
            logger.error("Gmail credentials not configured")
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

        # Create SMTP connection once for all emails
        server = self._create_smtp_connection()
        if not server:
            return {"sent": 0, "failed": len(valid_recipients), "failed_emails": valid_recipients}

        try:
            for to_email in valid_recipients:
                try:
                    # Create message
                    message = MIMEMultipart("alternative")
                    message["Subject"] = subject
                    message["From"] = f"{self.from_name} <{self.username}>"
                    message["To"] = to_email

                    # Add plain text version (fallback)
                    if body_text:
                        part1 = MIMEText(body_text, "plain")
                        message.attach(part1)

                    # Add HTML version
                    part2 = MIMEText(body_html, "html")
                    message.attach(part2)

                    # Send email
                    server.sendmail(self.username, to_email, message.as_string())
                    sent_count += 1
                    logger.info(f"Email sent to {to_email}")

                except Exception as e:
                    failed_count += 1
                    failed_emails.append(to_email)
                    logger.error(f"Failed to send email to {to_email}: {str(e)}")

        finally:
            server.quit()

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
