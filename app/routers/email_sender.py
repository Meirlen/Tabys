"""
Email Sender Router

Allows administrators to send custom emails via Gmail SMTP
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.database import get_db
from app import models, oauth2
from app.email_service import email_service
import logging

router = APIRouter(prefix="/api/v2/admin/emails", tags=["Email Sender"])

logger = logging.getLogger(__name__)


class EmailRecipient(BaseModel):
    """Email recipient model"""
    email: EmailStr
    name: Optional[str] = None


class SendEmailRequest(BaseModel):
    """Request model for sending custom emails"""
    recipients: List[EmailStr] = Field(..., min_items=1, max_items=100, description="List of recipient email addresses")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    body_html: str = Field(..., min_length=1, description="Email body in HTML format")
    body_text: Optional[str] = Field(None, description="Plain text version of email body")


class SendEmailResponse(BaseModel):
    """Response model for email sending"""
    success: bool
    sent_count: int
    failed_count: int
    failed_emails: List[str]
    message: str


@router.post("/send", response_model=SendEmailResponse)
async def send_custom_email(
    email_data: SendEmailRequest,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Send custom email to specified recipients

    Only accessible to super_admin and administrator roles.
    """
    # Check if user has permission (only super_admin and administrator)
    if current_admin.role not in ['super_admin', 'administrator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав для отправки email рассылок"
        )

    try:
        # Send emails using the email service
        result = email_service.send_bulk_emails(
            recipients=email_data.recipients,
            subject=email_data.subject,
            body_html=email_data.body_html,
            body_text=email_data.body_text
        )

        # Log the activity
        logger.info(
            f"Admin {current_admin.login} (ID: {current_admin.id}) sent email to {result['sent']} recipients. "
            f"Subject: {email_data.subject}"
        )

        return SendEmailResponse(
            success=result['sent'] > 0,
            sent_count=result['sent'],
            failed_count=result['failed'],
            failed_emails=result['failed_emails'],
            message=f"Отправлено: {result['sent']}, Ошибок: {result['failed']}"
        )

    except Exception as e:
        logger.error(f"Error sending custom email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отправке email: {str(e)}"
        )


@router.get("/recipients")
async def get_available_recipients(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Get list of available email recipients (admins with email addresses)

    Only accessible to super_admin and administrator roles.
    """
    # Check if user has permission
    if current_admin.role not in ['super_admin', 'administrator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав для просмотра списка получателей"
        )

    try:
        # Get all admins with email addresses
        admins = db.query(models.Admin).filter(
            models.Admin.email.isnot(None),
            models.Admin.email != ''
        ).all()

        recipients = [
            {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "role": admin.role
            }
            for admin in admins
        ]

        return {
            "recipients": recipients,
            "total": len(recipients)
        }

    except Exception as e:
        logger.error(f"Error fetching recipients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении списка получателей: {str(e)}"
        )


@router.post("/test")
async def send_test_email(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Send a test email to the current admin's email address

    Useful for testing SMTP configuration.
    """
    # Check if user has permission
    if current_admin.role not in ['super_admin', 'administrator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав для отправки тестовых email"
        )

    # Check if admin has email
    if not current_admin.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас не указан email адрес в профиле"
        )

    try:
        # Create test email
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
                .content {{
                    padding: 20px 0;
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
                    <h2>Тестовое сообщение</h2>
                </div>

                <div class="content">
                    <p>Здравствуйте, {current_admin.name}!</p>

                    <p>Это тестовое письмо для проверки настроек Gmail SMTP.</p>

                    <p>Если вы получили это письмо, значит система отправки email работает корректно.</p>

                    <p><strong>Детали:</strong></p>
                    <ul>
                        <li>Отправитель: SARYARQA JASTARY</li>
                        <li>Получатель: {current_admin.email}</li>
                        <li>Ваша роль: {current_admin.role}</li>
                    </ul>
                </div>

                <div class="footer">
                    <p>Это автоматическое тестовое сообщение от системы SARYARQA JASTARY.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Тестовое сообщение

        Здравствуйте, {current_admin.name}!

        Это тестовое письмо для проверки настроек Gmail SMTP.

        Если вы получили это письмо, значит система отправки email работает корректно.

        Детали:
        - Отправитель: SARYARQA JASTARY
        - Получатель: {current_admin.email}
        - Ваша роль: {current_admin.role}

        ---
        Это автоматическое тестовое сообщение от системы SARYARQA JASTARY.
        """

        # Send test email
        success = email_service.send_email(
            to_email=current_admin.email,
            subject="Тестовое письмо - SARYARQA JASTARY",
            body_html=html_body,
            body_text=text_body
        )

        if success:
            logger.info(f"Test email sent to {current_admin.email} by admin {current_admin.login}")
            return {
                "success": True,
                "message": f"Тестовое письмо успешно отправлено на {current_admin.email}",
                "recipient": current_admin.email
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось отправить тестовое письмо. Проверьте настройки SMTP."
            )

    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отправке тестового email: {str(e)}"
        )
