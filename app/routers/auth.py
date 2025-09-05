from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, oauth2
from datetime import datetime, timedelta
import os
import uuid
from typing import List

router = APIRouter(prefix="/api/v2/auth", tags=["Authentication"])


# Проверка существования профиля
@router.post("/check-profile")
def check_profile(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Проверяет существование профиля по номеру телефона
    """
    phone_number = login_data.phone_number

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if user:
        # Пользователь найден - отправляем OTP для авторизации
        otp_code = "950826"

        # Деактивируем старые коды для этого номера
        db.query(models.OtpCode).filter(
            models.OtpCode.phone_number == phone_number,
            models.OtpCode.is_used == False
        ).update({"is_used": True})

        # Создаем новый OTP код
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        new_otp = models.OtpCode(
            phone_number=phone_number,
            code=otp_code,
            expires_at=expires_at
        )

        db.add(new_otp)
        db.commit()

        # TODO: Отправка в WhatsApp
        # send_whatsapp_message(phone_number, f"Ваш код: {otp_code}")

        return {
            "profile_exists": True,
            "message": "OTP код отправлен на ваш номер в WhatsApp",
            "user_type": user.user_type.value
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
    phone_number = login_data.phone_number

    # Генерируем OTP код (пока что статический 950826)
    otp_code = "950826"

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

    # TODO: Здесь будет отправка в WhatsApp
    # send_whatsapp_message(phone_number, f"Ваш код: {otp_code}")

    return schemas.LoginResponse(
        message="OTP код отправлен на ваш номер в WhatsApp",
        otp_sent=True
    )


# Подтверждение OTP и авторизация
@router.post("/verify-otp")
def verify_otp(otp_data: schemas.OtpRequest, db: Session = Depends(get_db)):
    """
    Проверяет OTP код и авторизует пользователя
    """
    otp_code = "950826"

    # Проверяем OTP код
    if otp_data.code != otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный OTP код"
        )

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == otp_data.phone_number
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
            "user_type": user.user_type.value,
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


# Регистрация физического лица
@router.post("/register-individual")
async def register_individual(
        phone_number: str = Form(...),
        full_name: str = Form(...),
        address: str = Form(...),
        person_status_id: int = Form(...),
        id_document_photo: UploadFile = File(...),
        selfie_with_id_photo: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Регистрация физического лица
    """
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
        new_user.user_type = models.UserTypeEnum.INDIVIDUAL
        db.commit()
    else:
        # Создаем нового пользователя
        new_user = models.User(
            phone_number=phone_number,
            user_type=models.UserTypeEnum.INDIVIDUAL
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    # Загружаем фото удостоверения
    id_doc_path = await save_uploaded_file(id_document_photo, "id_document")
    selfie_path = await save_uploaded_file(selfie_with_id_photo, "selfie")

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
            "user_type": new_user.user_type.value,
            "service_status": new_user.service_status.value,
            "is_verified": new_user.is_verified
        }
    }

# Регистрация организации
@router.post("/register-organization", response_model=schemas.OrganizationResponse)
def register_organization(
        org_data: schemas.OrganizationRegistration,
        db: Session = Depends(get_db)
):
    """
    Регистрация организации
    """
    # Проверяем, что пользователь еще не зарегистрирован
    existing_user = db.query(models.User).filter(
        models.User.phone_number == org_data.phone_number
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким номером уже зарегистрирован"
        )

    # Создаем пользователя
    new_user = models.User(
        phone_number=org_data.phone_number,
        user_type=models.UserTypeEnum.ORGANIZATION
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
    db.commit()

    return schemas.OrganizationResponse.from_orm(new_user)

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

    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}_{file_type}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return f"/{file_path}"