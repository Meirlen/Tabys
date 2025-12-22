from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, oauth2, analytics_models
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime

router = APIRouter(prefix="/api/v2/admin", tags=["Admin Authentication"])

# Настройка для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Импортируем схемы из schemas.py
from app import schemas


def hash_password(password: str):
    """Хэширование пароля"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/register", response_model=schemas.AdminResponse)
def register_admin(admin_data: schemas.AdminRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового администратора
    """
    # Проверяем, существует ли админ с таким логином
    existing_admin = db.query(models.Admin).filter(
        models.Admin.login == admin_data.login
    ).first()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор с таким логином уже существует"
        )

    # Хэшируем пароль
    hashed_password = hash_password(admin_data.password)

    # Создаем нового администратора
    new_admin = models.Admin(
        name=admin_data.name,
        role=admin_data.role,
        login=admin_data.login,
        password=hashed_password
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin


@router.post("/login")
def login_admin(login_data: schemas.AdminLogin, request: Request, db: Session = Depends(get_db)):
    """
    Авторизация администратора
    """
    # Ищем админа по логину
    admin = db.query(models.Admin).filter(
        models.Admin.login == login_data.login
    ).first()

    # Get IP address and user agent for logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')

    if not admin:
        # Log failed login attempt
        login_log = analytics_models.LoginHistory(
            admin_id=None,
            user_type='admin',
            login=login_data.login,
            status='failed',
            failure_reason='Admin not found',
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(login_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )

    # Проверяем пароль
    if not verify_password(login_data.password, admin.password):
        # Log failed login attempt - wrong password
        login_log = analytics_models.LoginHistory(
            admin_id=admin.id,
            user_type='admin',
            login=login_data.login,
            status='failed',
            failure_reason='Invalid password',
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(login_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )

    # Log successful login
    login_log = analytics_models.LoginHistory(
        admin_id=admin.id,
        user_type='admin',
        login=login_data.login,
        status='success',
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(login_log)
    db.commit()

    # Создаем токен (используем существующую функцию)
    access_token = oauth2.create_access_token(data={"admin_id": str(admin.id), "user_type": "admin"})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin_data": {
            "id": admin.id,
            "name": admin.name,
            "login": admin.login,
            "role": admin.role,  # ДОБАВЛЕНО: отправляем роль на frontend
            "created_at": admin.created_at
        }
    }


@router.get("/profile")
def get_admin_profile(db: Session = Depends(get_db), current_admin: models.Admin = Depends(oauth2.get_current_admin)):
    """
    Получение профиля текущего администратора
    """
    return {
        "id": current_admin.id,
        "name": current_admin.name,
        "login": current_admin.login,
        "role": current_admin.role,  # ДОБАВЛЕНО: отправляем роль
        "created_at": current_admin.created_at
    }


@router.put("/change-password")
def change_admin_password(
        password_data: schemas.AdminChangePassword,
        db: Session = Depends(get_db),
        current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Изменение пароля администратора
    """
    # Проверяем старый пароль
    if not verify_password(password_data.old_password, current_admin.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )

    # Устанавливаем новый пароль
    current_admin.password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Пароль успешно изменен"}


@router.get("/list")
def get_all_admins(
        db: Session = Depends(get_db),
        current_admin: models.Admin = Depends(oauth2.get_current_admin)
):
    """
    Получение списка всех администраторов (доступно только для супер-админов)
    """
    # Проверяем, что текущий админ - супер-админ
    if current_admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому разделу"
        )

    admins = db.query(models.Admin).all()
    return [
        {
            "id": admin.id,
            "name": admin.name,
            "login": admin.login,
            "role": admin.role,
            "created_at": admin.created_at
        }
        for admin in admins
    ]