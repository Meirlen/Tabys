import re
from datetime import datetime
from app.entity.FlightInfo import *
from app.entity.HotelSearchInfo import *

def remove_action_info(text):
    # Regex to match and remove any part of the text that starts with "[[" and ends with "]]"
    cleaned_text = re.sub(r"\[\[.*?\]\]", "", text)
    return cleaned_text.strip()

def identify_action(text):
    # Search for the pattern [action = '...'] in the text
    action_match = re.search(r"\[action = '(\w+)'\]", text)
    # If the pattern is found, return the action; otherwise, return None
    return action_match.group(1) if action_match else None


def parse_flight_info(text):
    # Инициализируем переменные значениями по умолчанию

    print("Start Scanning.....")
    print("Start Scanning.....")
    print(text)
    print("Start Scanning.....")
    print("Start Scanning.....")

    passenger_count = None
    date = None
    from_city = None
    to_city = None
    action = None
    lang = None

    # Паттерны для поиска данных в тексте
    passenger_pattern = re.compile(r'passenger_count\s*=\s*(\d+)')
    date_pattern = re.compile(r'date\s*=\s*([\d\s\w]+)')
    from_city_pattern = re.compile(r'from_city\s*=\s*[\'"]?([\w\s]+)[\'"]?')
    to_city_pattern = re.compile(r'to_city\s*=\s*[\'"]?([\w\s]+)[\'"]?')
    action_pattern = re.compile(r'action\s*=\s*[\'"]?([\w\s]+)[\'"]?')
    lang_pattern = re.compile(r'language\s*=\s*[\'"]?([\w\s]+)[\'"]?')

    # Ищем соответствия в тексте и присваиваем значения переменным
    passenger_match = passenger_pattern.search(text)
    date_match = date_pattern.search(text)
    from_city_match = from_city_pattern.search(text)
    to_city_match = to_city_pattern.search(text)
    action_match = action_pattern.search(text)
    lang_match = lang_pattern.search(text)

    if passenger_match:
        passenger_count = int(passenger_match.group(1))

    if date_match:
        try:
            date = datetime.strptime(date_match.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            date = date_match.group(1)
    date = "2024-12-04"
    if from_city_match:
        from_city = from_city_match.group(1)

    if to_city_match:
        to_city = to_city_match.group(1)

    if action_match:
        action = action_match.group(1)

    if lang_match:
        lang = lang_match.group(1)

    # Вывод результатов
    print(f"Количество пассажиров: {passenger_count}")
    print(f"Дата: {date}")
    print(f"Откуда: {from_city}")
    print(f"Куда: {to_city}")
    print(f"Action: {action}")


    if from_city == None:

        return None


    trip_info = FlightInfo(passenger_count=passenger_count, date=date, from_city=from_city, to_city=to_city, lang=lang)

    return trip_info



import re
from dataclasses import dataclass

# Define the HotelSearchInfo dataclass
@dataclass
class HotelSearchInfo:
    guest_count: int
    from_date: str
    to_date: str
    city: str




def parse_hotel_search_info(text):
    # Improved regex pattern with flexible spaces and escaped brackets
    action_match = re.search(
        r"\[\[\s*action\s*=\s*'(\w+)'\s*\]\s*,\s*\[\s*city\s*=\s*'([\w\s]+)'\s*\]\s*,\s*\[\s*from_date\s*=\s*'([\d\w\s]+)'\s*\]\s*,\s*\[\s*to_date\s*=\s*'([\d\w\s]+)'\s*\]",
        text
    )

    if action_match:
        action = action_match.group(1)
        city = action_match.group(2)
        from_date = action_match.group(3)
        to_date = action_match.group(4)

        try:
            from_date = datetime.strptime(from_date, "%d %B %Y").strftime("%Y-%m-%d")
            to_date = datetime.strptime(to_date, "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

        # Set guest_count to 1
        guest_count = 1

        # Create and return the HotelSearchInfo object if the action is 'hotel'
        if action == 'hotel':
            return HotelSearchInfo(guest_count, from_date, to_date, city)

    return None


# Test the function with the provided example
test = (
    "Отлично, я уже на верном пути! 😊 Подождите минутку, начинаю поиск доступных отелей на сайте booking.com: "
    "Город — Ташкент  Дата — с 15 ноября до 31 ноября  Количество человек — 1 "
    "[[action = 'hotel'],[city = 'Tasasxashkent'], [from_date = '15 november 2024'],[to_date = '31 november 2024']]"
    "  Скоро вернусь с самыми интересными вариантами! 🏨✨"
)

# print(parse_hotel_search_info(test))


import requests
def send_sms(code,phone):

    print(f"Code sended {code}  {phone}")

    app_hash = "UgngZHxDDxj" # prod
    mobizone_token = "kza1fe1aef2adaf485a3cfdf69c89f6ba61cfe23ca2fb47c7601efdc8d34760fc30e21"
    # app_hash = "jg9AkTD8yOw" # debug


    message  = 'Tyra  код: '+str(code)+' '+app_hash
    print(message)

    response = requests.get(
            url='https://api.mobizon.kz/service/message/sendsmsmessage?apiKey='+mobizone_token+'&recipient='+phone+'&text='+message,
        )

    print(response)

# send_sms("776766","77711474766")


def send_sms_bookids(code,phone):

    print(f"Code sended {code}  {phone}")

    app_hash = "UgngZHxDDxj" # prod
    mobizone_token = "kza1fe1aef2adaf485a3cfdf69c89f6ba61cfe23ca2fb47c7601efdc8d34760fc30e21"
    # app_hash = "jg9AkTD8yOw" # debug

    message  = 'BOOKIDS код: '+str(code)+' '+app_hash
    print(message)

    response = requests.get(
            url='https://api.mobizon.kz/service/message/sendsmsmessage?apiKey='+mobizone_token+'&recipient='+phone+'&text='+message,
        )

    print(response)


from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from fastapi import HTTPException, status
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Получение переменных окружения для настройки SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "noreply@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")


async def send_email(recipient_email: str, subject: str, message: str, html_message: str = None):
    """
    Отправляет электронное письмо пользователю.

    Args:
        recipient_email: Email получателя
        subject: Тема письма
        message: Текстовое сообщение
        html_message: HTML-версия сообщения (опционально)
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = DEFAULT_FROM_EMAIL
        msg['To'] = recipient_email

        # Текстовая версия
        part1 = MIMEText(message, 'plain')
        msg.attach(part1)

        # HTML версия (если указана)
        if html_message:
            part2 = MIMEText(html_message, 'html')
            msg.attach(part2)

        # Подключение к SMTP серверу и отправка
        server = SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email успешно отправлен на адрес {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при отправке email: {str(e)}")
        # Не выбрасываем исключение, т.к. функция может быть вызвана в фоновом режиме
        return False


def generate_welcome_template(user_name: str):
    """
    Генерирует HTML-шаблон для приветственного сообщения.

    Args:
        user_name: Имя пользователя

    Returns:
        str: HTML-шаблон
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Добро пожаловать</title>
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
                background-color: #4CAF50;
                padding: 20px;
                color: white;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Добро пожаловать!</h1>
            </div>
            <div class="content">
                <h2>Здравствуйте, {user_name}!</h2>
                <p>Благодарим вас за регистрацию на нашей платформе экспертов.</p>
                <p>Теперь вы можете найти специалистов в различных областях и отправлять запросы на сотрудничество.</p>
                <p>Если у вас возникнут вопросы, не стесняйтесь обращаться в службу поддержки.</p>
            </div>
            <div class="footer">
                <p>С уважением, Команда поддержки</p>
                <p>© 2025 Платформа экспертов. Все права защищены.</p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_collaboration_notification_template(expert_name: str, user_name: str, user_email: str,
                                                 user_phone: str, message: str, request_id: str):
    """
    Генерирует HTML-шаблон для уведомления о запросе на сотрудничество.

    Args:
        expert_name: Имя эксперта
        user_name: Имя пользователя
        user_email: Email пользователя
        user_phone: Телефон пользователя
        message: Сообщение от пользователя
        request_id: ID запроса

    Returns:
        str: HTML-шаблон
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Новый запрос на сотрудничество</title>
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
                background-color: #2196F3;
                padding: 20px;
                color: white;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .message-box {{
                background-color: #fff;
                border-left: 4px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Новый запрос на сотрудничество</h1>
            </div>
            <div class="content">
                <h2>Здравствуйте, {expert_name}!</h2>
                <p>Вы получили новый запрос на сотрудничество от пользователя:</p>

                <h3>Информация о запросе:</h3>
                <ul>
                    <li><strong>Имя:</strong> {user_name}</li>
                    <li><strong>Email:</strong> {user_email}</li>
                    <li><strong>Телефон:</strong> {user_phone or "Не указан"}</li>
                </ul>

                <div class="message-box">
                    <h3>Сообщение:</h3>
                    <p>{message or "Сообщение не указано"}</p>
                </div>

                <p>Для ответа на запрос используйте кнопки ниже:</p>

                <div style="text-align: center;">
                    <a href="https://example.com/approve/{request_id}" class="button">Одобрить</a>
                    <a href="https://example.com/reject/{request_id}" class="button" style="background-color: #f44336;">Отклонить</a>
                </div>

                <p>Или вы можете войти в личный кабинет для управления запросами.</p>
            </div>
            <div class="footer">
                <p>С уважением, Команда поддержки</p>
                <p>© 2025 Платформа экспертов. Все права защищены.</p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_approval_notification_template(user_name: str, expert_name: str):
    """
    Генерирует HTML-шаблон для уведомления об одобрении запроса.

    Args:
        user_name: Имя пользователя
        expert_name: Имя эксперта

    Returns:
        str: HTML-шаблон
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Запрос на сотрудничество одобрен</title>
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
                background-color: #4CAF50;
                padding: 20px;
                color: white;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Запрос одобрен!</h1>
            </div>
            <div class="content">
                <h2>Здравствуйте, {user_name}!</h2>
                <p>Хорошие новости! Ваш запрос на сотрудничество с экспертом {expert_name} был одобрен.</p>
                <p>Эксперт свяжется с вами в ближайшее время по указанным вами контактным данным.</p>
                <p>Если у вас возникнут вопросы, не стесняйтесь обращаться в службу поддержки.</p>
            </div>
            <div class="footer">
                <p>С уважением, Команда поддержки</p>
                <p>© 2025 Платформа экспертов. Все права защищены.</p>
            </div>
        </div>
    </body>
    </html>
    """


import os
from typing import List


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Проверяет, соответствует ли расширение файла списку разрешенных расширений

    Args:
        filename: Имя файла с расширением
        allowed_extensions: Список разрешенных расширений (без точки в начале)

    Returns:
        bool: True, если расширение файла входит в список разрешенных, иначе False
    """
    if not filename:
        return False

    # Получаем расширение файла (без точки)
    ext = os.path.splitext(filename)[1][1:].lower()

    # Проверяем, входит ли расширение в список разрешенных
    return ext in [extension.lower() for extension in allowed_extensions]


import os
import uuid
from typing import List, Optional
from fastapi import UploadFile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import aiofiles



async def save_upload_file(upload_file: UploadFile, upload_dir: str) -> str:
    """
    Сохраняет загруженный файл на диск и возвращает путь к сохраненному файлу
    """
    # Создаем уникальное имя файла
    filename = f"{uuid.uuid4()}-{upload_file.filename}"
    file_path = os.path.join(upload_dir, filename)

    # Создаем директорию, если она не существует
    os.makedirs(upload_dir, exist_ok=True)

    # Сохраняем файл
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await upload_file.read()
        await out_file.write(content)

    # Возвращаем путь к файлу
    return file_path

