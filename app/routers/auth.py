from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, oauth2, utils
from datetime import timedelta
from app.utils import send_email, generate_welcome_template
from typing import List
import os

router = APIRouter(prefix="/api/v2/auth", tags=["Authentication"])

# Время жизни токена
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
        user: schemas.UserCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Регистрация нового пользователя
    """
    # Проверяем, существует ли пользователь с таким email
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован"
        )

    # Хэшируем пароль
    hashed_password = utils.hash_password(user.password)
    user.password = hashed_password

    # Создаем нового пользователя
    new_user = models.User(
        email=user.email,
        password=user.password,
        full_name=user.full_name,
        is_admin=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Отправляем приветственное письмо
    html_content = generate_welcome_template(user.full_name)
    background_tasks.add_task(
        send_email,
        recipient_email=user.email,
        subject="Добро пожаловать на платформу экспертов!",
        message=f"Здравствуйте, {user.full_name}! Благодарим за регистрацию на нашей платформе.",
        html_message=html_content
    )

    return new_user




@router.post("/login")
def login_user(user_credentials: schemas.LoginUserSchema, db: Session = Depends(get_db),
               ):
    """
    Авторизация по номеру телефона.
    Если пользователя нет, создаем его автоматически с подпиской на 3 дня.
    Возвращает access_token.
    """

    # Проверяем, есть ли пользователь с таким номером
    user = db.query(models.User).filter(
        models.User.phone_number == user_credentials.phone_number
    ).first()

    # Если пользователя нет, создаем его с подпиской на 3 дня
    if not user:
        user = models.User(
            phone_number=user_credentials.phone_number,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Генерируем токен
    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})

    # Возвращаем ответ
    return {
        "code": 200,
        "message": "Success login",
        "data": {
            "user": {
                "id": user.id,
                "phone_number": user.phone_number,
            },
            "token": access_token,
            "token_type": "bearer"
        }
    }


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(oauth2.get_current_user)):
    """
    Получение информации о текущем пользователе
    """
    return current_user