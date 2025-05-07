from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models, schemas
import os

# Настройки токена
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-should-be-kept-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Создание схемы OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v2/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT токен для пользователя
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str, credentials_exception):
    """
    Проверяет JWT токен
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")

        if id is None:
            raise credentials_exception

        token_data = schemas.TokenData(id=id)
        return token_data

    except JWTError:
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Получает текущего пользователя на основе токена
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.id == token_data.id).first()

    if user is None:
        raise credentials_exception

    return user


def get_expert_user(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Проверяет, что текущий пользователь является экспертом
    """
    expert = db.query(models.Expert).filter(models.Expert.user_id == current_user.id).first()

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав эксперта для выполнения этого действия"
        )

    return current_user, expert


def get_admin_user(current_user=Depends(get_current_user)):
    """
    Проверяет, что текущий пользователь является администратором
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав администратора для выполнения этого действия"
        )

    return current_user