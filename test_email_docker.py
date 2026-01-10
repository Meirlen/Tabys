"""Test email sending from Docker container"""
from app.email_service import email_service

result = email_service.send_email(
    to_email='sailybaevvv@gmail.com',
    subject='Test from Docker Container',
    body_html='<h1>Test Successful!</h1><p>Email service is working from Docker container.</p>',
    body_text='Test successful! Email service is working from Docker container.'
)

print(f'Email sent successfully: {result}')
