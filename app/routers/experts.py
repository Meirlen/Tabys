from fastapi import (
    APIRouter, Depends, status, Query, Response,
    BackgroundTasks, HTTPException, File, UploadFile, Form
)
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil # Для копирования файла
import os     # Для работы с путями
import uuid   # Для генерации уникальных имен файлов

# Импорты ваших модулей
from app.database import get_db
from app.schemas import (
    ExpertList,
    ExpertDetail,
    ExpertCreate, # Эта схема будет использоваться для данных из формы
    CollaborationRequestCreate,
    CollaborationRequest,
    # ExpertFilter # Уже был в вашем фрагменте
)
from app import crud
from app.utils import send_email # Предполагается, что этот модуль существует
from app.oauth2 import get_current_user # Если используется аутентификация



router = APIRouter(prefix="/api/v2/experts", tags=["Experts"])
AVATAR_UPLOAD_DIR = "./static/avatars/experts" # Путь относительно корня проекта
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True) # Создать каталог, если он не существует


@router.get("/", response_model=List[ExpertList])
def list_experts(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Получение списка всех экспертов
    """
    experts = crud.get_experts(db, skip=skip, limit=limit)
    return experts


@router.get("/search", response_model=List[ExpertList])
def search_experts(
        specialization: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Поиск и фильтрация экспертов по различным параметрам
    """
    experts = crud.filter_experts(
        db,
        specialization=specialization,
        city=city,
        search=search,
        skip=skip,
        limit=limit
    )
    return experts


@router.get("/{expert_id}", response_model=ExpertDetail)
def get_expert_details(expert_id: int, db: Session = Depends(get_db)):
    """
    Получение детальной информации об эксперте
    """
    expert = crud.get_expert(db, expert_id=expert_id)
    return expert

import json
@router.post("/", response_model=ExpertDetail, status_code=status.HTTP_201_CREATED)
def create_expert(
        # Явно указываем, что поля приходят из формы
        full_name: str = Form(...),
        specialization: str = Form(...),
        phone: Optional[str] = Form(None),
        website: Optional[str] = Form(None),
        city: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        # education и experience приходят как JSON-строки из формы
        education_str: str = Form(..., alias="education"),  # Клиент должен отправить поле 'education' как JSON-строку
        experience_str: str = Form(..., alias="experience"),
        # Клиент должен отправить поле 'experience' как JSON-строку
        avatar: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user) # Если используется
):
    """
    Создание нового эксперта.
    При отправке данных используйте Content-Type: multipart/form-data.
    Поля модели ExpertCreate (full_name, specialization и т.д.)
    должны быть отправлены как отдельные поля формы.
    Для списков (education, experience) отправляйте их как JSON-строки.
    Например, поле 'education' должно содержать строку:
    '[{"university": "Example Uni", "start_date": "2022-01-01T00:00:00", ...}]'
    """
    avatar_url_path = None
    if avatar:
        if not avatar.content_type or not avatar.content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Загруженный файл должен быть изображением.")

        file_extension = os.path.splitext(avatar.filename)[1] if avatar.filename else ".png"
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        if file_extension.lower() not in allowed_extensions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Недопустимый тип файла. Разрешены: {', '.join(allowed_extensions)}")

        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_location = os.path.join(AVATAR_UPLOAD_DIR, unique_filename)
        try:
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(avatar.file, file_object)
            avatar_url_path = f"/static/avatars/experts/{unique_filename}"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Не удалось сохранить аватар: {str(e)}")
        finally:
            avatar.file.close()

    # Преобразуем JSON-строки education и experience в списки словарей
    try:
        education_list = json.loads(education_str)
        experience_list = json.loads(experience_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Некорректный JSON формат для education или experience.")

    # Создаем экземпляр ExpertCreate вручную из полученных данных
    expert_data_for_schema = {
        "full_name": full_name,
        "specialization": specialization,
        "phone": phone,
        "website": website,
        "city": city,
        "address": address,
        "education": education_list,  # Pydantic сам проверит типы внутри списка
        "experience": experience_list,  # Pydantic сам проверит типы внутри списка
        # avatar_url будет добавлен в CRUD функции, здесь его нет
    }

    try:
        expert_payload = ExpertCreate(**expert_data_for_schema)
    except Exception as pydantic_exc:  # Ловим ошибки валидации Pydantic
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Ошибка валидации данных эксперта: {pydantic_exc}")

    created_expert = crud.create_expert(db=db, expert=expert_payload, avatar_url=avatar_url_path)
    return created_expert

@router.post("/{expert_id}/collaborate", response_model=CollaborationRequest, status_code=status.HTTP_201_CREATED)
def request_collaboration(
        expert_id: int,
        request: CollaborationRequestCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Отправка запроса на сотрудничество с экспертом
    """
    # Получаем эксперта для проверки существования
    expert = crud.get_expert(db, expert_id=expert_id)

    # Создаем запрос на сотрудничество
    collab_request = crud.create_collaboration_request(
        db=db,
        expert_id=expert_id,
        request=request
    )


    # Отправляем уведомление эксперту в фоновом режиме
    # background_tasks.add_task(
    #     send_email,
    #     recipient_email=expert.email,
    #     subject=f"Новый запрос на сотрудничество от {request.user_name}",
    #     message=f"""
    #     Здравствуйте!
    #
    #     Вы получили новый запрос на сотрудничество от {request.user_name}.
    #
    #     Контактная информация:
    #     - Email: {request.user_email}
    #     - Телефон: {request.user_phone or "Не указан"}
    #
    #     Сообщение:
    #     {request.message or "Сообщение не указано"}
    #
    #     Для ответа на запрос перейдите в личный кабинет.
    #
    #     С уважением,
    #     Команда поддержки
    #     """
    # )

    return collab_request


@router.put("/{request_id}/status", response_model=CollaborationRequest)
def update_request_status(
        request_id: str,
        background_tasks: BackgroundTasks,
        status: str = Query(..., description="Статус запроса: pending, approved, rejected"),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление статуса запроса на сотрудничество (только для экспертов)
    """
    # Обновляем статус запроса
    updated_request = crud.update_collaboration_request_status(
        db=db,
        request_id=request_id,
        status=status
    )

    # Отправляем уведомление пользователю в фоновом режиме
    if status == "approved":
        background_tasks.add_task(
            send_email,
            recipient_email=updated_request.user_email,
            subject=f"Ваш запрос на сотрудничество был одобрен",
            message=f"""
            Здравствуйте, {updated_request.user_name}!

            Ваш запрос на сотрудничество с экспертом был одобрен.
            Эксперт свяжется с вами в ближайшее время.

            С уважением,
            Команда поддержки
            """
        )

    return updated_request