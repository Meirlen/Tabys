from fastapi import APIRouter, Depends, status, Query, Response, BackgroundTasks, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import uuid

from app.database import get_db
from app.schemas import (
    EventList,
    EventDetail,
    EventCreate,
    EventUpdate,
    EventParticipantCreate,
    EventParticipant
)
from app import crud
from app.utils import send_email
from app.oauth2 import get_current_user

router = APIRouter(prefix="/api/v2/events", tags=["Events"])


@router.get("/", response_model=List[EventList])
def list_events(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Получение списка всех мероприятий
    """
    events = crud.get_events(db, skip=skip, limit=limit)
    return events


@router.get("/search", response_model=List[EventList])
def search_events(
        format: Optional[str] = None,
        search: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Поиск и фильтрация мероприятий по различным параметрам
    """
    events = crud.filter_events(
        db,
        format=format,
        search=search,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return events


@router.get("/{event_id}", response_model=EventDetail)
def get_event_details(event_id: int, db: Session = Depends(get_db)):
    """
    Получение детальной информации о мероприятии
    """
    event = crud.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мероприятие не найдено"
        )
    return event


@router.post("/", response_model=EventDetail, status_code=status.HTTP_201_CREATED)
def create_event(
        event: EventCreate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Создание нового мероприятия (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    return crud.create_event(db=db, event=event)


@router.put("/{event_id}", response_model=EventDetail)
def update_event(
        event_id: int,
        event_update: EventUpdate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Обновление существующего мероприятия (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    updated_event = crud.update_event(db, event_id=event_id, event_update=event_update)
    if not updated_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мероприятие не найдено"
        )

    return updated_event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
        event_id: int,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Удаление мероприятия (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    success = crud.delete_event(db, event_id=event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мероприятие не найдено"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{event_id}/participate", response_model=EventParticipant, status_code=status.HTTP_201_CREATED)
def register_for_event(
        event_id: int,
        participant: EventParticipantCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Регистрация пользователя на мероприятие
    """
    # Проверяем существование мероприятия
    event = crud.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мероприятие не найдено"
        )

    # Создаем запись участника
    registered_participant = crud.create_event_participant(
        db=db,
        event_id=event_id,
        participant=participant
    )

    # Отправляем уведомление о регистрации в фоновом режиме
    background_tasks.add_task(
        send_email,
        recipient_email=participant.email,
        subject=f"Подтверждение регистрации на мероприятие: {event.title}",
        message=f"""
        Здравствуйте, {participant.first_name} {participant.last_name}!

        Благодарим вас за регистрацию на мероприятие "{event.title}".

        Детали мероприятия:
        - Дата: {event.event_date.strftime('%d.%m.%Y %H:%M')}
        - Место: {event.location}
        - Формат: {event.format}

        Ваш регистрационный номер: {registered_participant.registration_id}

        С уважением,
        Команда поддержки
        """
    )

    return registered_participant


@router.get("/{event_id}/participants", response_model=List[EventParticipant])
def get_event_participants(
        event_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Получение списка участников мероприятия (только для администраторов)
    """
    # # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Проверка существования мероприятия
    event = crud.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мероприятие не найдено"
        )

    participants = crud.get_event_participants(db, event_id=event_id, skip=skip, limit=limit)
    return participants


@router.post("/{event_id}/upload-photo")
async def upload_event_photo(
        event_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Upload a photo for an event
    """
    # Check if event exists
    event = crud.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Validate file type
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Create uploads directory if it doesn't exist
    upload_dir = "uploads/events"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save the file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Update event with photo path
    photo_url = f"/{file_path}"
    updated_event = crud.update_event(
        db,
        event_id=event_id,
        event_update=EventUpdate(event_photo=photo_url)
    )

    return {
        "message": "Photo uploaded successfully",
        "photo_url": photo_url,
        "event_id": event_id
    }


@router.delete("/{event_id}/photo")
def delete_event_photo(
        event_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete the photo for an event
    """
    event = crud.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Delete the physical file if it exists
    if event.event_photo:
        file_path = event.event_photo.lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Error deleting file: {e}")

    # Update event to remove photo URL
    updated_event = crud.update_event(
        db,
        event_id=event_id,
        event_update=EventUpdate(event_photo=None)
    )

    return {"message": "Photo deleted successfully"}