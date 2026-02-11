from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, oauth2, analytics_models
from config import get_settings
from datetime import datetime, timedelta
import os
import uuid
import random
from typing import List
from PIL import Image
import io
from app.routers.whatsapp_sender import send_whatsapp_message
from app.services.mobizon_service import get_mobizon_service

settings = get_settings()

router = APIRouter(prefix="/api/v2/auth", tags=["Authentication"])


@router.get("/me")
def get_current_user(current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    """
    Get current authenticated user information
    """
    # Get additional user data based on user type
    user_details = {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "user_type": current_user.user_type,
        "service_status": current_user.service_status.value,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

    # Add type-specific data
    if current_user.user_type == "individual":
        individual = db.query(models.Individual).filter(
            models.Individual.user_id == current_user.id
        ).first()
        if individual:
            user_details["full_name"] = individual.full_name
            user_details["address"] = individual.address

    elif current_user.user_type == "organization":
        organization = db.query(models.Organization).filter(
            models.Organization.user_id == current_user.id
        ).first()
        if organization:
            user_details["name"] = organization.name
            user_details["bin_number"] = organization.bin_number
            user_details["email"] = organization.email
            user_details["address"] = organization.address

    return user_details


@router.get("/sms-balance")
def check_sms_balance():
    """
    Проверяет баланс SMS на аккаунте Mobizon (для администраторов)
    """
    mobizon = get_mobizon_service()
    balance = mobizon.check_balance()

    if balance is not None:
        return {
            "success": True,
            "balance": balance,
            "currency": "KZT"
        }
    else:
        return {
            "success": False,
            "message": "Не удалось получить баланс"
        }


def normalize_phone_number(phone: str) -> str:
    """Нормализует номер телефона, убирая все символы кроме цифр"""
    return ''.join(filter(str.isdigit, phone))


def generate_otp_code() -> str:
    """Генерирует случайный 6-значный OTP код"""
    return str(random.randint(100000, 999999))


# Проверка существования профиля
@router.post("/check-profile")
def check_profile(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Проверяет существование профиля по номеру телефона
    """
    # Normalize phone number
    phone_number = normalize_phone_number(login_data.phone_number)
    print(f"DEBUG check-profile: normalized phone={phone_number}")

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if user:
        # Пользователь найден - отправляем OTP для авторизации
        otp_code = generate_otp_code()

        # Деактивируем старые коды для этого номера
        db.query(models.OtpCode).filter(
            models.OtpCode.phone_number == phone_number,
            models.OtpCode.is_used == False
        ).update({"is_used": True})

        # Создаем новый OTP код
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        new_otp = models.OtpCode(
            phone_number=phone_number,
            code=otp_code.strip(),  # Ensure no whitespace
            expires_at=expires_at
        )

        db.add(new_otp)
        db.commit()
        db.refresh(new_otp)  # Refresh to ensure data is committed

        # Отправка SMS через Mobizon
        mobizon = get_mobizon_service()
        sms_result = mobizon.send_otp(phone_number, otp_code)

        print(f"DEBUG: OTP код для {phone_number}: {otp_code}")  # Временно для тестирования

        if sms_result.get("success"):
            print(f"SMS successfully sent to {phone_number}")
        else:
            print(f"SMS failed to send to {phone_number}: {sms_result.get('message')}")
            # Note: OTP is still generated and can be used even if SMS fails

        return {
            "profile_exists": True,
            "message": "OTP код отправлен на ваш номер по SMS",
            "user_type": user.user_type
        }
    else:
        # Пользователь не найден - нужна регистрация
        return {
            "profile_exists": False,
            "message": "Профиль не найден. Необходимо зарегистрироваться"
        }


# Отправка OTP кода (оставляем для совместимости)
@router.post("/send-otp", response_model=schemas.LoginResponse)
def send_otp(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Отправляет OTP код на указанный номер телефона
    """
    phone_number = normalize_phone_number(login_data.phone_number)

    # Генерируем случайный OTP код
    otp_code = generate_otp_code()

    # Деактивируем старые коды для этого номера
    db.query(models.OtpCode).filter(
        models.OtpCode.phone_number == phone_number,
        models.OtpCode.is_used == False
    ).update({"is_used": True})

    # Создаем новый OTP код
    expires_at = datetime.utcnow() + timedelta(minutes=5)  # 5 минут на ввод
    new_otp = models.OtpCode(
        phone_number=phone_number,
        code=otp_code,
        expires_at=expires_at
    )

    db.add(new_otp)
    db.commit()

    # Отправка SMS через Mobizon
    mobizon = get_mobizon_service()
    sms_result = mobizon.send_otp(phone_number, otp_code)

    print(f"DEBUG: OTP код для {phone_number}: {otp_code}")  # Временно для тестирования

    if sms_result.get("success"):
        print(f"SMS successfully sent to {phone_number}")
    else:
        print(f"SMS failed to send to {phone_number}: {sms_result.get('message')}")

    return schemas.LoginResponse(
        message="OTP код отправлен на ваш номер по SMS",
        otp_sent=True
    )


# Простая авторизация по номеру телефона (без OTP)
@router.post("/login-phone")
def login_with_phone(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Авторизация пользователя только по номеру телефона (без OTP)
    """
    phone_number = normalize_phone_number(login_data.phone_number)

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Необходимо зарегистрироваться"
        )

    # Обновляем статус верификации
    user.is_verified = True
    db.commit()

    # Создаем токен
    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": {
            "id": user.id,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
            "service_status": user.service_status.value,
            "is_verified": user.is_verified
        }
    }


# Подтверждение OTP и авторизация
@router.post("/verify-otp")
def verify_otp(otp_data: schemas.OtpRequest, request: Request, db: Session = Depends(get_db)):
    """
    Проверяет OTP код и авторизует пользователя
    """
    # Get IP address and user agent for logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')

    # Normalize phone number and trim OTP code
    phone_number = normalize_phone_number(otp_data.phone_number)
    otp_code_input = otp_data.code.strip()

    print(f"DEBUG verify-otp: original_phone={otp_data.phone_number}, normalized_phone={phone_number}, code={otp_code_input}")

    # Ищем активный OTP код для данного номера
    otp_record = db.query(models.OtpCode).filter(
        models.OtpCode.phone_number == phone_number,
        models.OtpCode.is_used == False,
        models.OtpCode.expires_at > datetime.utcnow()
    ).first()

    # Debug: Check if any OTP exists for this phone (even if expired/used)
    all_otps = db.query(models.OtpCode).filter(
        models.OtpCode.phone_number == phone_number
    ).order_by(models.OtpCode.created_at.desc()).limit(3).all()

    print(f"DEBUG: Found {len(all_otps)} total OTP records for {phone_number}")
    for otp in all_otps:
        print(f"  - code={otp.code}, is_used={otp.is_used}, expires_at={otp.expires_at}, now={datetime.utcnow()}")

    # Проверяем существование и валидность OTP
    if not otp_record:
        # Log failed login - OTP not found or expired
        login_log = analytics_models.LoginHistory(
            user_id=None,
            user_type='user',
            phone_number=phone_number,
            status='failed',
            failure_reason='OTP code not found or expired',
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(login_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP код не найден или истек срок действия"
        )


    # Check if bypass code is used (if bypass is enabled)
    is_bypass_code = settings.otp_bypass_enabled and otp_code_input == settings.otp_bypass_code

    if not is_bypass_code:
        # Проверяем правильность кода
        if otp_record.code != otp_code_input:
            print(f"DEBUG: OTP mismatch - expected: {otp_record.code}, got: {otp_code_input}")

            # Log failed login - invalid OTP code
            login_log = analytics_models.LoginHistory(
                user_id=None,
                user_type='user',
                phone_number=phone_number,
                status='failed',
                failure_reason='Invalid OTP code',
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(login_log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный OTP код"
            )

    print(f"DEBUG: OTP code validated successfully")
    else:
        print(f"DEBUG: Bypass OTP code used for {otp_data.phone_number}")

    # Помечаем код как использованный
    otp_record.is_used = True
    db.commit()

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if not user:
        # Log failed login - user not found
        login_log = analytics_models.LoginHistory(
            user_id=None,
            user_type='user',
            phone_number=phone_number,
            status='failed',
            failure_reason='User not found',
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(login_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Необходимо зарегистрироваться"
        )

    # Обновляем статус верификации
    user.is_verified = True
    db.commit()

    # Log successful login
    login_log = analytics_models.LoginHistory(
        user_id=user.id,
        user_type='user',
        phone_number=phone_number,
        status='success',
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(login_log)
    db.commit()

    # Создаем токен
    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": {
            "id": user.id,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
            "service_status": user.service_status.value,
            "is_verified": user.is_verified
        }
    }

# Загрузка фото
@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """
    Загружает фото на сервер
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен быть изображением"
        )

    # Создаем директорию если не существует
    upload_dir = "uploads/documents"
    os.makedirs(upload_dir, exist_ok=True)

    # Генерируем уникальное имя файла
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {"file_path": f"/{file_path}"}


# Загрузка документа (шаблоны, .docx, .doc, .pdf и т.д.)
@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """
    Загружает документ на сервер (поддерживает .docx, .doc, .pdf, .xlsx, .xls и изображения)
    """
    # Разрешенные MIME-типы
    allowed_types = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/msword',  # .doc
        'application/pdf',  # .pdf
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ]

    # Разрешенные расширения
    allowed_extensions = ['.docx', '.doc', '.pdf', '.xlsx', '.xls', '.jpg', '.jpeg', '.png', '.gif', '.webp']

    # Получаем расширение файла
    file_extension = ''
    if file.filename and '.' in file.filename:
        file_extension = '.' + file.filename.split('.')[-1].lower()

    # Проверяем тип файла
    if file.content_type not in allowed_types and file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла. Разрешены: .docx, .doc, .pdf, .xlsx, .xls и изображения"
        )

    # Создаем директорию если не существует
    upload_dir = "uploads/templates"
    os.makedirs(upload_dir, exist_ok=True)

    # Генерируем уникальное имя файла
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {"file_path": f"/{file_path}"}


# Регистрация физического лица
@router.post("/register-individual")
async def register_individual(
        phone_number: str = Form(...),
        full_name: str = Form(...),
        address: str = Form(...),
        person_status_id: int = Form(...),
        otp_code: str = Form(None),  # Optional OTP code
        # id_document_photo: UploadFile = File(...),
        # selfie_with_id_photo: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Регистрация физического лица с проверкой OTP
    """
    # Normalize phone number
    phone_number = normalize_phone_number(phone_number)

    # Validate OTP if provided
    if otp_code:
        # Trim whitespace from OTP code
        otp_code_input = otp_code.strip()

        # Check for valid OTP code
        otp_record = db.query(models.OtpCode).filter(
            models.OtpCode.phone_number == phone_number,
            models.OtpCode.is_used == False,
            models.OtpCode.expires_at > datetime.utcnow()
        ).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP код не найден или истек срок действия"
            )

        # Check if bypass code is used (if bypass is enabled)
        is_bypass_code = settings.otp_bypass_enabled and otp_code_input == settings.otp_bypass_code

        # Check if OTP code is correct (or master code)
        if not is_bypass_code and otp_record.code != otp_code_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный OTP код"
            )

        # Mark OTP as used
        otp_record.is_used = True
        db.commit()

    # Ищем существующего пользователя
    existing_user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if existing_user:
        # Проверяем, есть ли уже Individual данные
        individual_data = db.query(models.Individual).filter(
            models.Individual.user_id == existing_user.id
        ).first()

        if individual_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким номером уже зарегистрирован"
            )

        # Если User есть, но Individual нет - используем существующего User
        new_user = existing_user
        new_user.user_type =  "individual"
        db.commit()
    else:
        # Создаем нового пользователя
        new_user = models.User(
            phone_number=phone_number,
            user_type= "individual"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    # Загружаем фото удостоверения
    # id_doc_path = await save_uploaded_file(id_document_photo, "id_document")
    # selfie_path = await save_uploaded_file(selfie_with_id_photo, "selfie")
    id_doc_path =""
    selfie_path =""
    # Создаем запись физического лица
    individual = models.Individual(
        user_id=new_user.id,
        full_name=full_name,
        id_document_photo=id_doc_path,
        selfie_with_id_photo=selfie_path,
        address=address,
        person_status_id=person_status_id
    )
    db.add(individual)

    # Обновляем статус верификации пользователя
    new_user.is_verified = True
    db.commit()

    # Создаем токен доступа
    access_token = oauth2.create_access_token(data={"user_id": str(new_user.id)})

    return {
        "message": "Регистрация прошла успешно",
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": {
            "id": new_user.id,
            "phone_number": new_user.phone_number,
            "user_type": new_user.user_type,
            "service_status": new_user.service_status.value,
            "is_verified": new_user.is_verified
        }
    }

# Регистрация организации (исправленная версия с номером телефона)
@router.post("/register-organization")
def register_organization(
        org_data: schemas.OrganizationRegistration,
        db: Session = Depends(get_db)
):
    """
    Регистрация организации с проверкой OTP
    """
    # Normalize phone number
    phone_number = normalize_phone_number(org_data.phone_number)

    # Validate OTP if provided
    if org_data.otp_code:
        # Trim whitespace from OTP code
        otp_code_input = org_data.otp_code.strip()

        # Check for valid OTP code
        otp_record = db.query(models.OtpCode).filter(
            models.OtpCode.phone_number == phone_number,
            models.OtpCode.is_used == False,
            models.OtpCode.expires_at > datetime.utcnow()
        ).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP код не найден или истек срок действия"
            )

        # Check if bypass code is used (if bypass is enabled)
        is_bypass_code = settings.otp_bypass_enabled and otp_code_input == settings.otp_bypass_code

        # Check if OTP code is correct (or master code)
        if not is_bypass_code and otp_record.code != otp_code_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный OTP код"
            )

        # Mark OTP as used
        otp_record.is_used = True
        db.commit()

    # Ищем существующего пользователя
    existing_user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if existing_user:
        # Проверяем, есть ли уже Organization данные
        organization_data = db.query(models.Organization).filter(
            models.Organization.user_id == existing_user.id
        ).first()

        if organization_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким номером уже зарегистрирован"
            )

        # Если User есть, но Organization нет - используем существующего User
        new_user = existing_user
        new_user.user_type = "organization"
        db.commit()
    else:
        # Создаем нового пользователя
        new_user = models.User(
            phone_number=phone_number,
            user_type="organization"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    # Создаем запись организации
    organization = models.Organization(
        user_id=new_user.id,
        name=org_data.name,
        bin_number=org_data.bin_number,
        organization_type_id=org_data.organization_type_id,
        email=org_data.email,
        address=org_data.address
    )
    db.add(organization)

    # Обновляем статус верификации пользователя
    new_user.is_verified = True
    db.commit()

    # Создаем токен доступа
    access_token = oauth2.create_access_token(data={"user_id": str(new_user.id)})

    return {
        "message": "Регистрация организации прошла успешно",
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": {
            "id": new_user.id,
            "phone_number": new_user.phone_number,
            "user_type": new_user.user_type,
            "service_status": new_user.service_status.value,
            "is_verified": new_user.is_verified
        }
    }


#
# # Получение справочников
# @router.get("/person-statuses", response_model=List[schemas.PersonStatusResponse])
# def get_person_statuses(db: Session = Depends(get_db)):
#     """
#     Получает список статусов личности
#     """
#     statuses = db.query(models.PersonStatus).filter(
#         models.PersonStatus.is_active == True
#     ).all()
#     return statuses
#

# Получение справочников (МОКИ)
@router.get("/person-statuses")
def get_person_statuses():
    """
    Получает список статусов личности (фейковые данные)
    """
    return [
        {
            "id": 1,
            "name_ru": "Студент",
            "name_kz": "Студент",
            "code": "student"
        },
        {
            "id": 2,
            "name_ru": "Рабочий",
            "name_kz": "Жұмысшы",
            "code": "worker"
        },
        {
            "id": 3,
            "name_ru": "Школьник",
            "name_kz": "Оқушы",
            "code": "schooler"
        },
        {
            "id": 4,
            "name_ru": "Безработный",
            "name_kz": "Жұмыссыз",
            "code": "unemployed"
        },
        {
            "id": 5,
            "name_ru": "Предприниматель",
            "name_kz": "Кәсіпкер",
            "code": "entrepreneur"
        },
        {
            "id": 6,
            "name_ru": "Пенсионер",
            "name_kz": "Зейнеткер",
            "code": "retired"
        },
        {
            "id": 7,
            "name_ru": "Домохозяйка",
            "name_kz": "Үй шаруасындағы",
            "code": "housewife"
        },
        {
            "id": 8,
            "name_ru": "Другое",
            "name_kz": "Басқа",
            "code": "other"
        }
    ]


# @router.get("/organization-types", response_model=List[schemas.OrganizationTypeResponse])
# def get_organization_types(db: Session = Depends(get_db)):
#     """
#     Получает список типов организаций
#     """
#     types = db.query(models.OrganizationType).filter(
#         models.OrganizationType.is_active == True
#     ).all()
#     return types


@router.get("/organization-types")
def get_organization_types():
    """
    Получает список типов организаций (фейковые данные)
    """
    return [
        {
            "id": 1,
            "name_ru": "Бизнес",
            "name_kz": "Бизнес",
            "code": "business"
        },
        {
            "id": 2,
            "name_ru": "Государственное учреждение",
            "name_kz": "Мемлекеттік мекеме",
            "code": "government"
        },
        {
            "id": 3,
            "name_ru": "Учебное заведение",
            "name_kz": "Оқу орны",
            "code": "educational"
        },
        {
            "id": 4,
            "name_ru": "НПО/НКО",
            "name_kz": "ҮЕҰ/КҚҰ",
            "code": "non_profit"
        }
    ]


# Вспомогательная функция для сохранения файлов


async def save_uploaded_file(file: UploadFile, file_type: str) -> str:
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен быть изображением"
        )

    upload_dir = "uploads/documents"
    os.makedirs(upload_dir, exist_ok=True)

    # Читаем файл
    content = await file.read()

    # Проверяем размер (макс 20MB)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл слишком большой. Максимум 20MB"
        )

    try:
        # Открываем и сжимаем изображение
        image = Image.open(io.BytesIO(content))

        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        # Уменьшаем до разумного размера
        max_size = (1920, 1920)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Сохраняем
        unique_filename = f"{uuid.uuid4()}_{file_type}.jpg"
        file_path = os.path.join(upload_dir, unique_filename)

        image.save(file_path, 'JPEG', quality=85, optimize=True)

        return f"/{file_path}"

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка обработки изображения: {str(e)}"
        )


@router.get("/users")
def get_all_users(
    skip: int = 0,
    limit: int = 1000,
    status_filter: str = None,
    current_admin: models.Admin = Depends(oauth2.get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get all users (admin only) for notification targeting.
    Returns basic user info: id, email, phone, name, status
    """
    query = db.query(models.User)

    # Filter by status if provided
    if status_filter and status_filter != "all":
        query = query.filter(models.User.service_status == status_filter)

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    # Build response with user details
    result = []
    for user in users:
        user_data = {
            "id": user.id,
            "phone_number": user.phone_number,
            "email": None,
            "full_name": None,
            "status": user.service_status.value if user.service_status else "UNKNOWN",
            "user_type": user.user_type,
        }

        # Get additional details based on user type
        if user.user_type == "individual":
            individual = db.query(models.Individual).filter(
                models.Individual.user_id == user.id
            ).first()
            if individual:
                user_data["full_name"] = individual.full_name
                # Individual model doesn't have email, use phone from User

        elif user.user_type == "organization":
            organization = db.query(models.Organization).filter(
                models.Organization.user_id == user.id
            ).first()
            if organization:
                user_data["full_name"] = organization.name
                user_data["email"] = organization.email

        result.append(user_data)

    return result