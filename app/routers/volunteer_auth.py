from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, oauth2
from app.v_models import *
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/v2/volunteer", tags=["Volunteer Auth"])


def generate_otp_code() -> str:
    """Генерирует случайный 6-значный OTP код"""
    return str(random.randint(100000, 999999))


# Справочники
@router.get("/corps")
def get_volunteer_corps():
    """
    Получает список корпусов для волонтёров
    """
    return [
        {"id": 1, "name_ru": "Волонтёры Победы", "name_kz": "Жеңіс волонтерлері"},
        {"id": 2, "name_ru": "Волонтёры-медики", "name_kz": "Медициналық волонтерлер"},
        {"id": 3, "name_ru": "Волонтёры культуры", "name_kz": "Мәдениет волонтерлері"},
        {"id": 4, "name_ru": "Серебряные волонтёры", "name_kz": "Күміс волонтерлер"},
        {"id": 5, "name_ru": "Экологические волонтёры", "name_kz": "Экологиялық волонтерлер"},
        {"id": 6, "name_ru": "Спортивные волонтёры", "name_kz": "Спорттық волонтерлер"},
        {"id": 7, "name_ru": "Киберволонтёры", "name_kz": "Киберволонтерлер"},
        {"id": 8, "name_ru": "Другое", "name_kz": "Басқа"}
    ]


@router.get("/directions")
def get_volunteer_directions():
    """
    Получает список направлений для волонтёров
    """
    return [
        {"id": 1, "name_ru": "Социальное волонтёрство", "name_kz": "Әлеуметтік волонтерлік"},
        {"id": 2, "name_ru": "Событийное волонтёрство", "name_kz": "Іс-шаралық волонтерлік"},
        {"id": 3, "name_ru": "Культурное волонтёрство", "name_kz": "Мәдени волонтерлік"},
        {"id": 4, "name_ru": "Медицинское волонтёрство", "name_kz": "Медициналық волонтерлік"},
        {"id": 5, "name_ru": "Экологическое волонтёрство", "name_kz": "Экологиялық волонтерлік"},
        {"id": 6, "name_ru": "Патриотическое волонтёрство", "name_kz": "Патриоттық волонтерлік"},
        {"id": 7, "name_ru": "Спортивное волонтёрство", "name_kz": "Спорттық волонтерлік"},
        {"id": 8, "name_ru": "Донорство", "name_kz": "Донорлық"},
        {"id": 9, "name_ru": "Поисковое волонтёрство", "name_kz": "Іздеу волонтерлігі"},
        {"id": 10, "name_ru": "Цифровое волонтёрство", "name_kz": "Цифрлық волонтерлік"}
    ]


# Проверка профиля волонтёра
@router.post("/check-profile")
def check_volunteer_profile(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Проверяет существование профиля волонтёра по номеру телефона
    """
    phone_number = login_data.phone_number

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if user:
        # Проверяем, есть ли профиль волонтера
        volunteer = db.query(Volunteer).filter(
            Volunteer.user_id == user.id
        ).first()

        if volunteer:
            # Волонтёр найден - отправляем OTP для авторизации
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
                code=otp_code,
                expires_at=expires_at
            )

            db.add(new_otp)
            db.commit()

            print(f"DEBUG: OTP код для волонтёра {phone_number}: {otp_code}")

            return {
                "profile_exists": True,
                "message": "OTP код отправлен на ваш номер в WhatsApp",
                "user_type": "VOLUNTEER",
                "has_other_roles": user.user_type != "VOLUNTEER"
            }
        else:
            # Пользователь есть, но профиля волонтера нет
            return {
                "profile_exists": False,
                "user_exists": True,
                "message": "У вас есть аккаунт, но нет профиля волонтера. Создайте профиль волонтера"
            }
    else:
        # Пользователь не найден - нужна полная регистрация
        return {
            "profile_exists": False,
            "user_exists": False,
            "message": "Профиль не найден. Необходимо зарегистрироваться"
        }


# Регистрация нового волонтёра (только для новых пользователей)
@router.post("/register")
def register_volunteer(
        phone_number: str = Form(...),
        full_name: str = Form(...),
        corps_id: int = Form(...),
        direction_id: int = Form(...),
        db: Session = Depends(get_db)
):
    """
    Регистрация НОВОГО волонтёра (создание User + Volunteer)
    Используется только для пользователей, у которых нет аккаунта
    """
    # Проверяем существующего пользователя
    existing_user = db.query(models.User).filter(
        models.User.phone_number == phone_number
    ).first()

    if existing_user:
        # Если пользователь уже существует - отправляем на другой эндпоинт
        volunteer_data = db.query(Volunteer).filter(
            Volunteer.user_id == existing_user.id
        ).first()

        if volunteer_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Волонтёр с таким номером уже зарегистрирован"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким номером уже существует. Используйте эндпоинт /create-volunteer-profile для добавления роли волонтера"
            )

    # Создаем нового пользователя
    new_user = models.User(
        phone_number=phone_number,
        user_type="VOLUNTEER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Создаем запись волонтёра
    volunteer = Volunteer(
        user_id=new_user.id,
        full_name=full_name,
        corps_id=corps_id,
        direction_id=direction_id,
        volunteer_status="VOLUNTEER"
    )
    db.add(volunteer)

    # Обновляем статус верификации пользователя
    new_user.is_verified = True
    db.commit()
    db.refresh(volunteer)

    # Создаем токен доступа
    access_token = oauth2.create_access_token(data={"user_id": str(new_user.id)})

    return {
        "message": "Регистрация волонтёра прошла успешно",
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": {
            "id": new_user.id,
            "phone_number": new_user.phone_number,
            "user_type": "VOLUNTEER",
            "volunteer_status": volunteer.volunteer_status,
            "is_verified": new_user.is_verified
        }
    }


# НОВЫЙ ЭНДПОИНТ: Создание профиля волонтера для существующего пользователя
@router.post("/create-volunteer-profile")
def create_volunteer_profile(
        full_name: str = Form(...),
        corps_id: int = Form(...),
        direction_id: int = Form(...),
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Создает профиль волонтера для существующего пользователя.
    Используется когда пользователь уже зарегистрирован под другой ролью
    и хочет стать волонтером параллельно.
    """
    # Проверяем, есть ли уже профиль волонтера
    existing_volunteer = db.query(Volunteer).filter(
        Volunteer.user_id == current_user.id
    ).first()

    if existing_volunteer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть профиль волонтера"
        )

    # Создаем профиль волонтера
    volunteer = Volunteer(
        user_id=current_user.id,
        full_name=full_name,
        corps_id=corps_id,
        direction_id=direction_id,
        volunteer_status="VOLUNTEER"
    )
    db.add(volunteer)
    db.commit()
    db.refresh(volunteer)

    return {
        "message": "Профиль волонтера создан успешно",
        "volunteer_data": {
            "id": volunteer.id,
            "user_id": current_user.id,
            "full_name": volunteer.full_name,
            "corps_id": volunteer.corps_id,
            "direction_id": volunteer.direction_id,
            "volunteer_status": volunteer.volunteer_status,
            "created_at": volunteer.created_at
        },
        "note": f"Ваша основная роль ({current_user.user_type}) сохранена. Теперь вы также волонтер!"
    }


# Проверка наличия профиля волонтера у текущего пользователя
@router.get("/has-profile")
def check_has_volunteer_profile(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Проверяет, есть ли у текущего авторизованного пользователя профиль волонтера
    """
    volunteer = db.query(Volunteer).filter(
        Volunteer.user_id == current_user.id
    ).first()

    return {
        "has_volunteer_profile": volunteer is not None,
        "primary_role": current_user.user_type,
        "phone_number": current_user.phone_number
    }


# Подтверждение OTP для волонтёра
@router.post("/verify-otp")
def verify_volunteer_otp(otp_data: schemas.OtpRequest, db: Session = Depends(get_db)):
    """
    Проверяет OTP код и авторизует волонтёра
    """
    # Ищем активный OTP код для данного номера
    otp_record = db.query(models.OtpCode).filter(
        models.OtpCode.phone_number == otp_data.phone_number,
        models.OtpCode.is_used == False,
        models.OtpCode.expires_at > datetime.utcnow()
    ).first()

    # Проверяем существование и валидность OTP
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP код не найден или истек срок действия"
        )

    # Мастер-код для разработки
    if otp_data.code != "950826":
        # Проверяем правильность кода
        if otp_record.code != otp_data.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный OTP код"
            )

    # Помечаем код как использованный
    otp_record.is_used = True
    db.commit()

    # Ищем пользователя
    user = db.query(models.User).filter(
        models.User.phone_number == otp_data.phone_number
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Получаем данные волонтёра
    volunteer = db.query(Volunteer).filter(
        Volunteer.user_id == user.id
    ).first()

    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль волонтёра не найден. Необходимо создать профиль"
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
            "primary_role": user.user_type,
            "volunteer_status": volunteer.volunteer_status,
            "is_verified": user.is_verified,
            "has_multiple_roles": user.user_type != "VOLUNTEER"
        }
    }


# Получение профиля волонтёра
@router.get("/profile")
def get_volunteer_profile(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Получает профиль волонтёра текущего пользователя
    """
    # Получаем данные волонтёра (не проверяем user_type, так как теперь могут быть множественные роли)
    volunteer = db.query(Volunteer).filter(
        Volunteer.user_id == current_user.id
    ).first()

    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль волонтёра не найден"
        )

    return {
        "id": volunteer.id,
        "user_id": current_user.id,
        "phone_number": current_user.phone_number,
        "full_name": volunteer.full_name,
        "corps_id": volunteer.corps_id,
        "direction_id": volunteer.direction_id,
        "volunteer_status": volunteer.volunteer_status,
        "primary_role": current_user.user_type,
        "has_multiple_roles": current_user.user_type != "VOLUNTEER",
        "created_at": volunteer.created_at,
        "updated_at": volunteer.updated_at
    }


# Обновление профиля волонтёра
@router.put("/profile")
def update_volunteer_profile(
        full_name: str = Form(None),
        corps_id: int = Form(None),
        direction_id: int = Form(None),
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Обновляет профиль волонтёра
    """
    # Получаем данные волонтёра
    volunteer = db.query(Volunteer).filter(
        Volunteer.user_id == current_user.id
    ).first()

    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль волонтёра не найден"
        )

    # Обновляем данные
    if full_name is not None:
        volunteer.full_name = full_name
    if corps_id is not None:
        volunteer.corps_id = corps_id
    if direction_id is not None:
        volunteer.direction_id = direction_id

    volunteer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(volunteer)

    return {
        "message": "Профиль обновлён успешно",
        "profile": {
            "id": volunteer.id,
            "full_name": volunteer.full_name,
            "corps_id": volunteer.corps_id,
            "direction_id": volunteer.direction_id,
            "volunteer_status": volunteer.volunteer_status
        }
    }


# Получение информации о статусе
@router.get("/status-info")
def get_volunteer_status_info():
    """
    Получает информацию о всех статусах волонтёров
    """
    return {
        "statuses": [
            {
                "code": "VOLUNTEER",
                "name_ru": "Волонтёр",
                "name_kz": "Волонтер",
                "description_ru": "Базовый статус волонтёра",
                "description_kz": "Негізгі волонтер мәртебесі",
                "level": 1
            },
            {
                "code": "TEAM_LEADER",
                "name_ru": "Тим-лидер",
                "name_kz": "Топ жетекшісі",
                "description_ru": "Лидер волонтёрской команды",
                "description_kz": "Волонтерлер тобының жетекшісі",
                "level": 2
            },
            {
                "code": "SUPERVISOR",
                "name_ru": "Супервайзер",
                "name_kz": "Супервайзер",
                "description_ru": "Супервайзер волонтёрских проектов",
                "description_kz": "Волонтерлік жобалардың супервайзері",
                "level": 3
            },
            {
                "code": "COORDINATOR",
                "name_ru": "Координатор",
                "name_kz": "Координатор",
                "description_ru": "Координатор волонтёрских программ",
                "description_kz": "Волонтерлік бағдарламалардың үйлестірушісі",
                "level": 4
            }
        ]
    }