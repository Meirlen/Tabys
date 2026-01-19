from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import Depends, Header
from app.database import get_db
from app import models, schemas
import os

# Настройки токена
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-should-be-kept-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000000

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


def optional_get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Получает текущего пользователя на основе токена, но не требует обязательной аутентификации.
    Возвращает None если токен отсутствует или недействителен.
    """
    try:
        if not authorization:
            return None
        
        # Extract token from "Bearer <token>" format
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")

        if id is None:
            return None

        user = db.query(models.User).filter(models.User.id == id).first()
        return user

    except (JWTError, Exception):
        return None


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


# Добавьте эти функции в ваш файл oauth2.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()


def get_current_admin(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
):
    """
    Получение текущего администратора из токена
    """
    try:
        # Декодируем токен (используйте ваши настройки JWT)
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,  # Ваш секретный ключ
            algorithms=[ALGORITHM]  # Ваш алгоритм
        )

        admin_id = payload.get("admin_id")
        user_type = payload.get("user_type")

        if admin_id is None or user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен"
            )

        # Ищем администратора в базе данных
        admin = db.query(models.Admin).filter(models.Admin.id == int(admin_id)).first()

        if admin is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Администратор не найден"
            )

        return admin

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )


def create_admin_access_token(data: dict, expires_delta: timedelta = None):
    """
    Создание токена доступа для администратора
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)  # Токен на 24 часа

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Middleware для проверки прав администратора
def admin_required(
        current_admin: models.Admin = Depends(get_current_admin)
):
    """
    Проверка, что пользователь является администратором
    """
    return current_admin