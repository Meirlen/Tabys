from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app import oauth2
from app.project_models import (
    Project, ProjectGallery, VotingParticipant, Vote,
    ProjectApplication, VotingResults,  ProjectStatusEnum,
    ProjectFormTemplate, ProjectFormSubmission
)
from app.project_schemas import (
    ProjectCreate, ProjectUpdate, VotingParticipantCreate, ProjectApplicationCreate, ProjectResponse,
    FormTemplateCreate, FormTemplateUpdate, FormTemplateResponse,
    FormSubmissionCreate, FormSubmissionUpdate, FormSubmissionResponse,
    FormSubmissionListResponse, FormAnalyticsResponse, FormField
)
from app.schemas import ModerationStats, ModerationStatus
from typing import List, Optional
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v2/projects", tags=["Projects"])

# Константа для базового URL
BASE_URL = "https://api.saryarqa-jastary.kz"

def get_full_url(path: Optional[str]) -> Optional[str]:
    """
    Формирует полный URL из относительного пути
    """
    if not path:
        return None
    if path.startswith('http'):
        return path
    return f"{BASE_URL}{path}"


# === ПРОЕКТЫ ===
@router.post("/", response_model=dict)
def create_project(
        project_data: ProjectCreate,
        db: Session = Depends(get_db)
        # Временно убираем current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Создание нового проекта
    """
    new_project = Project(
        title=project_data.title,
        title_ru=project_data.title_ru,
        description=project_data.description,
        description_ru=project_data.description_ru,
        author=project_data.author,
        project_type=project_data.project_type,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        photo_url=project_data.photo_url,
        video_url=project_data.video_url,
        admin_id=None  # Will be set by admin endpoints
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "message": "Проект успешно создан",
        "project_id": new_project.id,
        "title": new_project.title,
        "project_type": new_project.project_type
    }


@router.get("/")
def get_projects(
        project_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка проектов с фильтрами
    """
    query = db.query(Project)

    if project_type:
        query = query.filter(Project.project_type == project_type)

    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

    return [
        {
            "id": project.id,
            "title": project.title,
            "title_ru": project.title_ru,
            "description": project.description,
            "description_ru": project.description_ru,
            "author": project.author,
            "project_type": project.project_type,
            "status": project.status,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "photo_url": get_full_url(project.photo_url),
            "video_url": get_full_url(project.video_url),
            "created_at": project.created_at
        }
        for project in projects
    ]

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, func, desc
from datetime import datetime, timezone, timedelta


def calculate_time_remaining(end_date: datetime) -> dict:
    """
    Вычисляет оставшееся время до завершения проекта
    Простое решение: прибавляем 6 часов к UTC времени для получения казахстанского времени
    """
    # Получаем UTC время и добавляем 6 часов (Казахстан)
    now_utc = datetime.utcnow()
    now_local = now_utc + timedelta(hours=6)

    # Считаем что end_date уже в локальном времени
    if end_date.tzinfo is not None:
        # Если есть timezone info, убираем её для простоты
        end_date = end_date.replace(tzinfo=None)

    time_diff = end_date - now_local

    if time_diff.total_seconds() <= 0:
        return {
            "hours_remaining": 0,
            "minutes_remaining": 0,
            "is_expired": True
        }

    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return {
        "hours_remaining": hours,
        "minutes_remaining": minutes,
        "is_expired": False
    }


def update_project_status(project: Project) -> str:
    """
    Обновляет статус проекта на основе текущего времени
    """
    # Получаем локальное время (UTC + 6 часов)
    now_utc = datetime.utcnow()
    now_local = now_utc + timedelta(hours=6)

    # Работаем с датами как с локальными (без timezone)
    end_date = project.end_date.replace(tzinfo=None) if project.end_date.tzinfo else project.end_date
    start_date = project.start_date.replace(tzinfo=None) if project.start_date.tzinfo else project.start_date

    # Если конечная дата прошла
    if now_local >= end_date:
        return "completed"
    # Если проект еще не начался и статус draft
    elif now_local < start_date and project.status == "draft":
        return "draft"
    # Если проект в процессе
    elif start_date <= now_local < end_date and project.status in ["draft", "active"]:
        return "active"

    return project.status


@router.get("/new")
def get_projects(
        project_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка проектов с фильтрами
    """
    query = db.query(Project)

    if project_type:
        query = query.filter(Project.project_type == project_type)

    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

    result = []

    for project in projects:
        # Определяем актуальный статус
        actual_status = update_project_status(project)

        # Если статус изменился, обновляем в базе данных
        if actual_status != project.status:
            project.status = actual_status
            db.add(project)

        # Вычисляем оставшееся время
        time_remaining = calculate_time_remaining(project.end_date)

        project_data = {
            "id": project.id,
            "title": project.title,
            "title_ru": project.title_ru,
            "description": project.description,
            "description_ru": project.description_ru,
            "author": project.author,
            "project_type": project.project_type,
            "status": actual_status,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "photo_url": get_full_url(project.photo_url),
            "video_url": get_full_url(project.video_url),
            "created_at": project.created_at,
            "hours_remaining": time_remaining["hours_remaining"],
            "minutes_remaining": time_remaining["minutes_remaining"],
            "is_expired": time_remaining["is_expired"]
        }

        result.append(project_data)

    db.commit()

    return result


@router.get("/{project_id}", response_model=dict)
def get_project_detail(project_id: int, db: Session = Depends(get_db)):
    """
    Получение детальной информации о проекте
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    # Получаем галерею
    gallery = db.query(ProjectGallery).filter(
        ProjectGallery.project_id == project_id
    ).all()

    result = {
        "id": project.id,
        "title": project.title,
        "title_ru": project.title_ru,
        "description": project.description,
        "description_ru": project.description_ru,
        "author": project.author,
        "project_type": project.project_type,
        "status": project.status,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "photo_url": get_full_url(project.photo_url),
        "video_url": get_full_url(project.video_url),
        "created_at": project.created_at,
        "gallery": [
            {
                "id": img.id,
                "image_url": get_full_url(img.image_url),
                "description": img.description,
                "created_at": img.created_at
            }
            for img in gallery
        ]
    }

    # Если это голосовалка, добавляем участников
    if project.project_type == "voting":
        participants = db.query(VotingParticipant).filter(
            VotingParticipant.project_id == project_id
        ).order_by(desc(VotingParticipant.votes_count)).all()

        result["participants"] = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "description_ru": p.description_ru,
                "photo_url": get_full_url(p.photo_url),
                "video_url": get_full_url(p.video_url),
                "votes_count": p.votes_count,
                "instagram_url": p.instagram_url,
                "facebook_url": p.facebook_url,
                "linkedin_url": p.linkedin_url,
                "twitter_url": p.twitter_url,
                "created_at": p.created_at
            }
            for p in participants
        ]

        # Общее количество голосов
        total_votes = db.query(func.count(Vote.id)).filter(
            Vote.project_id == project_id
        ).scalar()
        result["total_votes"] = total_votes

    # Если это прием заявок, добавляем количество заявок
    elif project.project_type == "application":
        applications_count = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project_id
        ).scalar()
        result["applications_count"] = applications_count

    return result


@router.put("/{project_id}", response_model=dict)
def update_project(
        project_id: int,
        project_data: ProjectUpdate,
        db: Session = Depends(get_db),
):
    """
    Обновление проекта
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    # Обновляем поля
    update_data = project_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(project, key):
            setattr(project, key, value)

    db.commit()

    return {"message": "Проект успешно обновлен"}


@router.delete("/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
):
    """
    Удаление проекта
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    db.delete(project)
    db.commit()

    return {"message": "Проект успешно удален"}


# === ЗАГРУЗКА ФАЙЛОВ ===

@router.post("/{project_id}/upload-photo")
async def upload_project_photo(
        project_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Загрузка основного фото проекта
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен быть изображением"
        )

    # Проверяем существование проекта
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    # Сохраняем файл
    file_path = await save_uploaded_file(file, "projects")

    # Обновляем проект
    project.photo_url = file_path
    db.commit()

    return {"file_path": get_full_url(file_path), "message": "Фото успешно загружено"}


@router.post("/{project_id}/upload-gallery")
async def upload_gallery_image(
        project_id: int,
        file: UploadFile = File(...),
        description: str = Form(None),
        db: Session = Depends(get_db)
):
    """
    Загрузка изображения в галерею проекта
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен быть изображением"
        )

    # Проверяем существование проекта
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    # Сохраняем файл
    file_path = await save_uploaded_file(file, "gallery")

    # Создаем запись в галерее
    gallery_item = ProjectGallery(
        project_id=project_id,
        image_url=file_path,
        description=description
    )

    db.add(gallery_item)
    db.commit()
    db.refresh(gallery_item)

    return {
        "id": gallery_item.id,
        "file_path": get_full_url(file_path),
        "message": "Изображение добавлено в галерею"
    }


# === УЧАСТНИКИ ГОЛОСОВАНИЯ ===

@router.post("/{project_id}/participants")
def create_voting_participant(
        project_id: int,
        participant_data: VotingParticipantCreate,
        db: Session = Depends(get_db)
):
    """
    Добавление участника в голосовалку
    """
    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"  # Вместо ProjectTypeEnum.VOTING
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или это не голосовалка"
        )

    participant = VotingParticipant(
        project_id=project_id,
        name=participant_data.name,
        description=participant_data.description,
        description_ru=participant_data.description_ru,
        video_url=participant_data.video_url,
        instagram_url=participant_data.instagram_url,
        facebook_url=participant_data.facebook_url,
        linkedin_url=participant_data.linkedin_url,
        twitter_url=participant_data.twitter_url
    )

    db.add(participant)
    db.commit()
    db.refresh(participant)

    return {
        "message": "Участник добавлен",
        "participant_id": participant.id,
        "name": participant.name
    }


@router.post("/{project_id}/participants/{participant_id}/upload-photo")
async def upload_participant_photo(
        project_id: int,
        participant_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Загрузка фото участника голосования
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл должен быть изображением"
        )

    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id,
        VotingParticipant.project_id == project_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Сохраняем файл
    file_path = await save_uploaded_file(file, "participants")

    # Обновляем участника
    participant.photo_url = file_path
    db.commit()

    return {"file_path": get_full_url(file_path), "message": "Фото участника загружено"}


# === ГОЛОСОВАНИЕ ===

@router.post("/{project_id}/vote")
def vote_for_participant(
        project_id: int,
        vote_data: dict,  # {"participant_id": int}
        db: Session = Depends(get_db),
        current_user = Depends(oauth2.get_current_user)
):
    """
    Голосование за участника
    """
    participant_id = vote_data.get("participant_id")
    user_id = current_user.id

    if not participant_id:
        print("Не указан ID участника")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан ID участника"
        )

    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"  # Вместо ProjectTypeEnum.VOTING
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или это не голосовалка"
        )

    # Проверяем, что проект активен
    now = datetime.utcnow()
    if project.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Голосование неактивно"
        )

    if now < project.start_date or now > project.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Голосование не в активном периоде"
        )

    # Проверяем, что участник существует
    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id,
        VotingParticipant.project_id == project_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Проверяем, что пользователь еще не голосовал в этом проекте
    existing_vote = db.query(Vote).filter(
        Vote.project_id == project_id,
        Vote.user_id == user_id
    ).first()

    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже голосовали в этом проекте"
        )

    # Создаем голос
    vote = Vote(
        project_id=project_id,
        participant_id=participant_id,
        user_id=user_id,
        user_phone=current_user.phone_number
    )

    db.add(vote)

    # Увеличиваем счетчик голосов у участника
    participant.votes_count += 1

    db.commit()

    return {
        "message": "Голос принят",
        "participant_name": participant.name,
        "current_votes": participant.votes_count
    }


@router.get("/{project_id}/results")
def get_voting_results(project_id: int, db: Session = Depends(get_db)):
    """
    Получение результатов голосования
    """
    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"  # Вместо ProjectTypeEnum.VOTING
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или это не голосовалка"
        )

    # Получаем участников с количеством голосов
    participants = db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).order_by(desc(VotingParticipant.votes_count)).all()

    total_votes = sum(p.votes_count for p in participants)

    results = []
    for i, participant in enumerate(participants, 1):
        percentage = (participant.votes_count / total_votes * 100) if total_votes > 0 else 0
        results.append({
            "position": i,
            "participant_id": participant.id,
            "participant_name": participant.name,
            "photo_url": get_full_url(participant.photo_url),
            "votes_count": participant.votes_count,
            "percentage": f"{percentage:.1f}%"
        })

    return {
        "project_id": project_id,
        "project_title": project.title,
        "total_votes": total_votes,
        "total_participants": len(participants),
        "results": results
    }


# === ЗАЯВКИ НА ПРОЕКТЫ ===

@router.post("/{project_id}/applications")
async def submit_application(
        project_id: int,
        phone_number: str = Form(...),
        description: str = Form(...),
        applicant_name: str = Form(None),
        email: str = Form(None),
        document: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """
    Подача заявки на проект
    """
    # Проверяем, что проект существует и это прием заявок
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "application"
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или это не проект с приемом заявок"
        )

    # Проверяем, что проект активен
    now = datetime.utcnow()
    if project.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Прием заявок неактивен"
        )

    if now < project.start_date or now > project.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Прием заявок не в активном периоде"
        )

    # Сохраняем документ, если он загружен
    document_url = None
    if document:
        # Проверяем тип файла (разрешаем различные форматы документов)
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/jpg'
        ]
        if document.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы PDF, Word, JPEG, PNG"
            )

        document_url = await save_uploaded_file(document, "applications")

    # Создаем заявку
    application = ProjectApplication(
        project_id=project_id,
        phone_number=phone_number,
        description=description,
        applicant_name=applicant_name,
        email=email,
        document_url=document_url
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "message": "Заявка успешно подана",
        "application_id": application.id,
        "project_title": project.title,
        "status": "pending"
    }


@router.get("/{project_id}/applications")
def get_project_applications(
        project_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Получение заявок по проекту (только для создателей/админов)
    """
    # Проверяем, что проект существует
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    query = db.query(ProjectApplication).filter(
        ProjectApplication.project_id == project_id
    )

    if status_filter:
        query = query.filter(ProjectApplication.status == status_filter)

    applications = query.order_by(desc(ProjectApplication.created_at)).offset(skip).limit(limit).all()

    return {
        "project_title": project.title,
        "total_count": query.count(),
        "applications": [
            {
                "id": app.id,
                "phone_number": app.phone_number,
                "applicant_name": app.applicant_name,
                "email": app.email,
                "description": app.description,
                "document_url": get_full_url(app.document_url),
                "status": app.status,
                "admin_comment": app.admin_comment,
                "created_at": app.created_at,
                "reviewed_at": app.reviewed_at
            }
            for app in applications
        ]
    }


@router.put("/applications/{application_id}/status")
def update_application_status(
        application_id: int,
        status_data: dict,  # {"status": "approved/rejected", "comment": "текст"}
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Обновление статуса заявки (только для админов)
    """
    application = db.query(ProjectApplication).filter(
        ProjectApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    new_status = status_data.get("status")
    comment = status_data.get("comment", "")

    if new_status not in ["approved", "rejected", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный статус. Доступны: approved, rejected, pending"
        )

    application.status = new_status
    application.admin_comment = comment
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = current_user.get("user_id")

    db.commit()

    return {
        "message": f"Статус заявки изменен на {new_status}",
        "application_id": application.id,
        "new_status": new_status
    }


# === СТАТИСТИКА ===

@router.get("/{project_id}/stats")
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    """
    Получение статистики по проекту
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    stats = {
        "project_id": project_id,
        "project_title": project.title,
        "project_type": project.project_type,
        "status": project.status,
        "start_date": project.start_date,
        "end_date": project.end_date
    }

    if project.project_type == "voting":
        # Статистика для голосовалки
        total_participants = db.query(func.count(VotingParticipant.id)).filter(
            VotingParticipant.project_id == project_id
        ).scalar()

        total_votes = db.query(func.count(Vote.id)).filter(
            Vote.project_id == project_id
        ).scalar()

        # Лидирующий участник
        top_participant = db.query(VotingParticipant).filter(
            VotingParticipant.project_id == project_id
        ).order_by(desc(VotingParticipant.votes_count)).first()

        stats.update({
            "total_participants": total_participants,
            "total_votes": total_votes,
            "average_votes_per_participant": round(total_votes / total_participants,
                                                   2) if total_participants > 0 else 0,
            "leading_participant": {
                "name": top_participant.name,
                "votes": top_participant.votes_count
            } if top_participant else None
        })

    elif project.project_type == "application":
        # Статистика для приема заявок
        total_applications = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project_id
        ).scalar()

        pending_applications = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project_id,
            ProjectApplication.status == "pending"
        ).scalar()

        approved_applications = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project_id,
            ProjectApplication.status == "approved"
        ).scalar()

        rejected_applications = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project_id,
            ProjectApplication.status == "rejected"
        ).scalar()

        stats.update({
            "total_applications": total_applications,
            "pending_applications": pending_applications,
            "approved_applications": approved_applications,
            "rejected_applications": rejected_applications,
            "approval_rate": round((approved_applications / (approved_applications + rejected_applications) * 100),
                                   2) if (approved_applications + rejected_applications) > 0 else 0
        })

    return stats


# === ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ===

@router.get("/active/voting")
def get_active_voting_projects(db: Session = Depends(get_db)):
    """
    Получение активных проектов-голосовалок
    """
    now = datetime.utcnow()
    projects = db.query(Project).filter(
        Project.project_type == "voting", # Вместо ProjectTypeEnum.VOTING
        Project.status == "active",
        Project.start_date <= now,
        Project.end_date >= now
    ).order_by(desc(Project.created_at)).all()

    result = []
    for project in projects:
        # Получаем количество участников и голосов
        participants_count = db.query(func.count(VotingParticipant.id)).filter(
            VotingParticipant.project_id == project.id
        ).scalar()

        votes_count = db.query(func.count(Vote.id)).filter(
            Vote.project_id == project.id
        ).scalar()

        result.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "author": project.author,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "photo_url": get_full_url(project.photo_url),
            "participants_count": participants_count,
            "votes_count": votes_count
        })

    return {
        "count": len(result),
        "projects": result
    }


@router.get("/active/applications")
def get_active_application_projects(db: Session = Depends(get_db)):
    """
    Получение активных проектов с приемом заявок
    """
    now = datetime.utcnow()
    projects = db.query(Project).filter(
        Project.project_type == "application",
        Project.status == "active",
        Project.start_date <= now,
        Project.end_date >= now
    ).order_by(desc(Project.created_at)).all()

    result = []
    for project in projects:
        # Получаем количество заявок
        applications_count = db.query(func.count(ProjectApplication.id)).filter(
            ProjectApplication.project_id == project.id
        ).scalar()

        result.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "author": project.author,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "photo_url": get_full_url(project.photo_url),
            "applications_count": applications_count
        })

    return {
        "count": len(result),
        "projects": result
    }


@router.get("/my-votes")
def get_my_votes(
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Получение голосов текущего пользователя
    """
    user_id = current_user.get("user_id")

    votes = db.query(Vote).filter(Vote.user_id == user_id).order_by(desc(Vote.created_at)).all()

    result = []
    for vote in votes:
        project = db.query(Project).filter(Project.id == vote.project_id).first()
        participant = db.query(VotingParticipant).filter(VotingParticipant.id == vote.participant_id).first()

        result.append({
            "vote_id": vote.id,
            "project_id": vote.project_id,
            "project_title": project.title if project else "Неизвестный проект",
            "participant_id": vote.participant_id,
            "participant_name": participant.name if participant else "Неизвестный участник",
            "participant_photo": get_full_url(participant.photo_url) if participant and participant.photo_url else None,
            "voted_at": vote.created_at
        })

    return {
        "total_votes": len(result),
        "votes": result
    }


@router.get("/my-applications")
def get_my_applications(
        phone_number: str,
        db: Session = Depends(get_db)
):
    """
    Получение заявок пользователя по номеру телефона
    """
    applications = db.query(ProjectApplication).filter(
        ProjectApplication.phone_number == phone_number
    ).order_by(desc(ProjectApplication.created_at)).all()

    result = []
    for app in applications:
        project = db.query(Project).filter(Project.id == app.project_id).first()

        result.append({
            "application_id": app.id,
            "project_id": app.project_id,
            "project_title": project.title if project else "Неизвестный проект",
            "description": app.description,
            "applicant_name": app.applicant_name,
            "status": app.status,
            "admin_comment": app.admin_comment,
            "document_url": get_full_url(app.document_url),
            "created_at": app.created_at,
            "reviewed_at": app.reviewed_at
        })

    return {
        "total_applications": len(result),
        "applications": result
    }


# === УПРАВЛЕНИЕ ГАЛЕРЕЕЙ И УЧАСТНИКАМИ ===

@router.delete("/gallery/{image_id}")
def delete_gallery_image(
        image_id: int,
        db: Session = Depends(get_db),
):
    """
    Удаление изображения из галереи
    """
    image = db.query(ProjectGallery).filter(ProjectGallery.id == image_id).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Изображение не найдено"
        )

    # Удаляем файл с диска
    if image.image_url and os.path.exists(image.image_url.lstrip('/')):
        try:
            os.remove(image.image_url.lstrip('/'))
        except:
            pass  # Игнорируем ошибки удаления файла

    db.delete(image)
    db.commit()

    return {"message": "Изображение удалено"}


@router.delete("/participants/{participant_id}")
def delete_participant(
        participant_id: int,
        db: Session = Depends(get_db),
):
    """
    Удаление участника голосования
    """
    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Удаляем все голоса за этого участника
    db.query(Vote).filter(Vote.participant_id == participant_id).delete()

    # Удаляем участника
    db.delete(participant)
    db.commit()

    return {"message": "Участник удален"}


@router.put("/participants/{participant_id}")
def update_participant(
        participant_id: int,
        participant_data: dict,
        db: Session = Depends(get_db),
):
    """
    Обновление данных участника
    """
    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Обновляем поля
    allowed_fields = ['name', 'description', 'video_url', 'instagram_url', 'facebook_url', 'linkedin_url',
                      'twitter_url']

    for field in allowed_fields:
        if field in participant_data:
            setattr(participant, field, participant_data[field])

    db.commit()

    return {"message": "Данные участника обновлены"}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def save_uploaded_file(file: UploadFile, folder: str) -> str:
    """
    Сохранение загруженного файла
    """
    upload_dir = f"uploads/{folder}"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'unknown'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return f"/{file_path}"


# === ПОИСК И ФИЛЬТРАЦИЯ ===

@router.get("/search")
def search_projects(
        q: str,
        project_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    Поиск проектов по названию и описанию
    """
    query = db.query(Project).filter(
        Project.title.ilike(f"%{q}%") | Project.description.ilike(f"%{q}%")
    )

    if project_type:
        query = query.filter(Project.project_type == project_type)

    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

    return {
        "query": q,
        "count": len(projects),
        "projects": [
            {
                "id": project.id,
                "title": project.title,
                "description": project.description[:200] + "..." if len(
                    project.description) > 200 else project.description,
                "author": project.author,
                "project_type": project.project_type,
                "status": project.status,
                "photo_url": get_full_url(project.photo_url),
                "created_at": project.created_at
            }
            for project in projects
        ]
    }


# === ЗАВЕРШЕНИЕ ПРОЕКТОВ ===

@router.post("/{project_id}/complete")
def complete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Завершение проекта
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    project.status = "completed"
    db.commit()

    # Если это голосовалка, сохраняем результаты
    if project.project_type == "voting":
        participants = db.query(VotingParticipant).filter(
            VotingParticipant.project_id == project_id
        ).order_by(desc(VotingParticipant.votes_count)).all()

        total_votes = sum(p.votes_count for p in participants)

        # Очищаем старые результаты
        db.query(VotingResults).filter(VotingResults.project_id == project_id).delete()

        # Сохраняем новые результаты
        for i, participant in enumerate(participants, 1):
            percentage = (participant.votes_count / total_votes * 100) if total_votes > 0 else 0

            result = VotingResults(
                project_id=project_id,
                participant_id=participant.id,
                participant_name=participant.name,
                votes_count=participant.votes_count,
                percentage=f"{percentage:.1f}%",
                position=i
            )
            db.add(result)

        db.commit()

    return {
        "message": "Проект завершен",
        "project_id": project_id,
        "final_status": "completed"
    }


# Добавьте эти роуты в ваш файл project_routes.py

# === УПРАВЛЕНИЕ ГОЛОСАМИ ===

@router.post("/{project_id}/participants/{participant_id}/boost-votes")
def boost_participant_votes(
        project_id: int,
        participant_id: int,
        boost_data: dict,  # {"votes_to_add": int}
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)  # Раскомментировать для проверки прав
):
    """
    Увеличение количества голосов у участника (для тестирования)
    """
    votes_to_add = boost_data.get("votes_to_add", 0)

    if votes_to_add <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Количество голосов должно быть больше 0"
        )

    # Проверяем существование участника
    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id,
        VotingParticipant.project_id == project_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Увеличиваем счетчик
    old_votes = participant.votes_count
    participant.votes_count += votes_to_add

    db.commit()

    return {
        "message": f"Количество голосов увеличено на {votes_to_add}",
        "participant_id": participant_id,
        "participant_name": participant.name,
        "old_votes": old_votes,
        "new_votes": participant.votes_count,
        "added_votes": votes_to_add
    }


@router.put("/{project_id}/participants/{participant_id}/set-votes")
def set_participant_votes(
        project_id: int,
        participant_id: int,
        votes_data: dict,  # {"votes_count": int}
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Установка конкретного количества голосов у участника
    """
    new_votes_count = votes_data.get("votes_count", 0)

    if new_votes_count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Количество голосов не может быть отрицательным"
        )

    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id,
        VotingParticipant.project_id == project_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    old_votes = participant.votes_count
    participant.votes_count = new_votes_count

    db.commit()

    return {
        "message": f"Количество голосов установлено: {new_votes_count}",
        "participant_id": participant_id,
        "participant_name": participant.name,
        "old_votes": old_votes,
        "new_votes": new_votes_count
    }


@router.post("/{project_id}/boost-all-votes")
def boost_all_participants_votes(
        project_id: int,
        boost_data: dict,  # {"votes_to_add": int}
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Увеличение голосов у всех участников проекта
    """
    votes_to_add = boost_data.get("votes_to_add", 0)

    if votes_to_add <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Количество голосов должно быть больше 0"
        )

    # Проверяем существование проекта
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект-голосовалка не найден"
        )

    # Получаем всех участников
    participants = db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).all()

    if not participants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участники не найдены"
        )

    updated_participants = []

    # Увеличиваем голоса у всех участников
    for participant in participants:
        old_votes = participant.votes_count
        participant.votes_count += votes_to_add

        updated_participants.append({
            "id": participant.id,
            "name": participant.name,
            "old_votes": old_votes,
            "new_votes": participant.votes_count
        })

    db.commit()

    return {
        "message": f"Голоса увеличены на {votes_to_add} у всех участников",
        "project_id": project_id,
        "participants_updated": len(updated_participants),
        "votes_added_per_participant": votes_to_add,
        "participants": updated_participants
    }


@router.post("/{project_id}/distribute-random-votes")
def distribute_random_votes(
        project_id: int,
        votes_data: dict,  # {"total_votes": int}
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Случайное распределение голосов между участниками
    """
    import random

    total_votes = votes_data.get("total_votes", 0)

    if total_votes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Общее количество голосов должно быть больше 0"
        )

    # Получаем участников
    participants = db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).all()

    if not participants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участники не найдены"
        )

    # Случайно распределяем голоса
    participants_count = len(participants)
    votes_distribution = []

    # Генерируем случайные веса для каждого участника
    weights = [random.randint(1, 10) for _ in range(participants_count)]
    total_weight = sum(weights)

    # Распределяем голоса пропорционально весам
    remaining_votes = total_votes
    for i, participant in enumerate(participants):
        if i == participants_count - 1:  # Последнему участнику отдаем остаток
            votes_for_participant = remaining_votes
        else:
            votes_for_participant = int((weights[i] / total_weight) * total_votes)
            remaining_votes -= votes_for_participant

        old_votes = participant.votes_count
        participant.votes_count += votes_for_participant

        votes_distribution.append({
            "id": participant.id,
            "name": participant.name,
            "old_votes": old_votes,
            "added_votes": votes_for_participant,
            "new_votes": participant.votes_count
        })

    db.commit()

    return {
        "message": f"Распределено {total_votes} голосов между {participants_count} участниками",
        "project_id": project_id,
        "total_votes_distributed": total_votes,
        "participants": votes_distribution
    }


@router.post("/{project_id}/reset-votes")
def reset_all_votes(
        project_id: int,
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Сброс всех голосов в проекте
    """
    # Проверяем проект
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект-голосовалка не найден"
        )

    # Сбрасываем голоса у участников
    participants = db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).all()

    reset_participants = []
    for participant in participants:
        old_votes = participant.votes_count
        participant.votes_count = 0
        reset_participants.append({
            "id": participant.id,
            "name": participant.name,
            "old_votes": old_votes
        })

    # Удаляем записи о голосах из таблицы Vote
    votes_deleted = db.query(Vote).filter(Vote.project_id == project_id).delete()

    db.commit()

    return {
        "message": "Все голоса сброшены",
        "project_id": project_id,
        "participants_reset": len(reset_participants),
        "vote_records_deleted": votes_deleted,
        "participants": reset_participants
    }


@router.post("/{project_id}/participants/{participant_id}/create-fake-votes")
def create_fake_votes(
        project_id: int,
        participant_id: int,
        votes_data: dict,  # {"votes_count": int}
        db: Session = Depends(get_db),
        # current_user: dict = Depends(oauth2.get_current_user)
):
    """
    Создание фейковых записей голосов (с записями в таблице Vote)
    """
    votes_count = votes_data.get("votes_count", 0)

    if votes_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Количество голосов должно быть больше 0"
        )

    # Проверяем участника
    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id,
        VotingParticipant.project_id == project_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Создаем фейковые голоса
    fake_votes = []
    for i in range(votes_count):
        fake_vote = Vote(
            project_id=project_id,
            participant_id=participant_id,
            user_id=9999 + i,  # Фейковые ID пользователей
            user_phone=f"+7700000{1000 + i}",  # Фейковые номера
            created_at=datetime.utcnow()
        )
        db.add(fake_vote)
        fake_votes.append(fake_vote)

    # Увеличиваем счетчик у участника
    old_votes = participant.votes_count
    participant.votes_count += votes_count

    db.commit()

    return {
        "message": f"Создано {votes_count} фейковых голосов",
        "participant_id": participant_id,
        "participant_name": participant.name,
        "old_votes": old_votes,
        "new_votes": participant.votes_count,
        "fake_votes_created": len(fake_votes)
    }


# ========== ADMIN ENDPOINTS WITH RBAC ==========

from app.oauth2 import get_current_admin
from app.rbac import Module, Permission, require_module_access, require_permission, apply_owner_filter
from app import models
from fastapi import Query


@router.get("/admin/list")
def admin_list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True))
):
    """Admin: List projects with RBAC filtering (NPO sees only their own)"""
    # Start with base query
    query = db.query(Project)

    # Apply owner-based filtering for NPO/MSB roles
    query = apply_owner_filter(query, Project, current_admin)

    # Apply other filters
    if status:
        query = query.filter(Project.status == status)

    if project_type:
        query = query.filter(Project.project_type == project_type)

    if search:
        query = query.filter(
            (Project.title.ilike(f"%{search}%")) |
            (Project.title_ru.ilike(f"%{search}%")) |
            (Project.description.ilike(f"%{search}%")) |
            (Project.description_ru.ilike(f"%{search}%"))
        )

    # Execute query with pagination
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    return projects


@router.post("/admin/create", status_code=status.HTTP_201_CREATED)
def admin_create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.CREATE))
):
    """Admin: Create project with auto-approval for administrators/super_admins"""
    # Determine moderation status based on admin role
    is_admin_created = current_admin.role in ['administrator', 'super_admin']
    moderation_status = 'approved' if is_admin_created else 'pending'

    # Determine project status
    # Non-admins (NPO, MSB) can only create drafts - projects become active after moderation approval
    # Admins can create active projects immediately
    if is_admin_created:
        project_status = project_data.status or "draft"
    else:
        # Force draft status for non-admins until approved
        project_status = "draft"

    # Create project
    new_project = Project(
        title=project_data.title,
        title_ru=project_data.title_ru,
        description=project_data.description,
        description_ru=project_data.description_ru,
        author=project_data.author,
        project_type=project_data.project_type,
        status=project_status,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        photo_url=project_data.photo_url,
        video_url=project_data.video_url,
        admin_id=current_admin.id,
        moderation_status=moderation_status,
        is_admin_created=is_admin_created,
        moderated_at=datetime.utcnow() if is_admin_created else None,
        moderated_by=current_admin.id if is_admin_created else None
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project


@router.put("/admin/{project_id}")
def admin_update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE))
):
    """Admin: Update project with ownership check and re-moderation logic"""
    # Get existing project
    query = db.query(Project).filter(Project.id == project_id)

    # Apply owner filter for NPO/MSB
    query = apply_owner_filter(query, Project, current_admin)

    existing_project = query.first()
    if not existing_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или у вас нет прав на его редактирование"
        )

    # Define major fields that trigger re-moderation
    major_fields = ['title', 'title_ru', 'description', 'description_ru', 'author', 'project_type']
    major_update = any(
        getattr(project_data, field) is not None
        for field in major_fields
    )

    # Check if admin bypasses moderation
    is_admin = current_admin.role in ['administrator', 'super_admin']

    # Apply re-moderation logic
    if major_update and not is_admin and existing_project.moderation_status == 'approved':
        # Major update by non-admin on approved content requires re-moderation
        existing_project.moderation_status = 'pending'
        existing_project.moderated_at = None
        existing_project.moderated_by = None
    elif major_update and is_admin:
        # Admin updates stay approved
        existing_project.moderated_at = datetime.utcnow()
        existing_project.moderated_by = current_admin.id

    # Update fields
    if project_data.title is not None:
        existing_project.title = project_data.title
    if project_data.title_ru is not None:
        existing_project.title_ru = project_data.title_ru
    if project_data.description is not None:
        existing_project.description = project_data.description
    if project_data.description_ru is not None:
        existing_project.description_ru = project_data.description_ru
    if project_data.author is not None:
        existing_project.author = project_data.author
    # Note: project_type is not editable after creation - removed from update logic
    if project_data.status is not None:
        existing_project.status = project_data.status
    if project_data.start_date is not None:
        existing_project.start_date = project_data.start_date
    if project_data.end_date is not None:
        existing_project.end_date = project_data.end_date
    if project_data.photo_url is not None:
        existing_project.photo_url = project_data.photo_url
    if project_data.video_url is not None:
        existing_project.video_url = project_data.video_url

    db.commit()
    db.refresh(existing_project)

    return existing_project


@router.delete("/admin/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.DELETE))
):
    """Admin: Delete project with ownership check and cascading deletes"""
    # Get existing project
    query = db.query(Project).filter(Project.id == project_id)

    # Apply owner filter for NPO/MSB
    query = apply_owner_filter(query, Project, current_admin)

    existing_project = query.first()
    if not existing_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или у вас нет прав на его удаление"
        )

    # Delete related records first to avoid foreign key constraint violations

    # 1. Delete form submissions
    db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.project_id == project_id
    ).delete(synchronize_session=False)

    # 2. Delete form templates
    db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).delete(synchronize_session=False)

    # 3. Delete voting participants and their votes
    participant_ids = [p.id for p in db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).all()]

    if participant_ids:
        db.query(Vote).filter(Vote.participant_id.in_(participant_ids)).delete(synchronize_session=False)

    db.query(VotingParticipant).filter(
        VotingParticipant.project_id == project_id
    ).delete(synchronize_session=False)

    # 4. Delete project applications
    db.query(ProjectApplication).filter(
        ProjectApplication.project_id == project_id
    ).delete(synchronize_session=False)

    # 5. Delete voting results
    db.query(VotingResults).filter(
        VotingResults.project_id == project_id
    ).delete(synchronize_session=False)

    # 6. Delete gallery images
    db.query(ProjectGallery).filter(
        ProjectGallery.project_id == project_id
    ).delete(synchronize_session=False)

    # 7. Finally, delete the project itself
    db.delete(existing_project)
    db.commit()

    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@router.get("/admin/{project_id}")
def admin_get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True))
):
    """Admin: Get project details with ownership check"""
    query = db.query(Project).filter(Project.id == project_id)

    # Apply owner filter for NPO/MSB
    query = apply_owner_filter(query, Project, current_admin)

    project = query.first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или у вас нет прав на его просмотр"
        )

    return project


# ============================================
# Moderation Endpoints
# ============================================

@router.get("/admin/moderation/stats", response_model=ModerationStats)
def get_projects_moderation_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True))
):
    """
    Get project moderation statistics.
    Shows total, pending, approved, and rejected project counts.
    """
    total = db.query(Project).count()
    pending = db.query(Project).filter(Project.moderation_status == 'pending').count()
    approved = db.query(Project).filter(Project.moderation_status == 'approved').count()
    rejected = db.query(Project).filter(Project.moderation_status == 'rejected').count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }


@router.get("/admin/moderation/pending", response_model=List[ProjectResponse])
def get_pending_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True))
):
    """
    Get all pending projects awaiting moderation.
    Returns projects with moderation_status='pending'.
    """
    projects = db.query(Project).filter(
        Project.moderation_status == 'pending'
    ).offset(skip).limit(limit).all()

    return projects


@router.get("/admin/moderation/all-statuses", response_model=List[ProjectResponse])
def get_all_projects_with_status(
    moderation_status: Optional[ModerationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True))
):
    """
    Get all projects with optional status filter.
    Admin endpoint - shows all projects regardless of moderation status.
    """
    query = db.query(Project)

    if moderation_status:
        query = query.filter(Project.moderation_status == moderation_status.value)

    projects = query.offset(skip).limit(limit).all()
    return projects


@router.post("/admin/moderation/{project_id}/approve", response_model=ProjectResponse)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE))
):
    """
    Approve a project.
    Changes moderation_status to 'approved', sets status to 'active', and records moderator info.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.moderation_status = 'approved'
    project.moderated_at = datetime.utcnow()
    project.moderated_by = current_admin.id

    # Automatically activate the project when approved
    if project.status == 'draft':
        project.status = 'active'

    db.commit()
    db.refresh(project)
    return project


@router.post("/admin/moderation/{project_id}/reject", response_model=ProjectResponse)
def reject_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE))
):
    """
    Reject a project.
    Changes moderation_status to 'rejected' and records moderator info.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.moderation_status = 'rejected'
    project.moderated_at = datetime.utcnow()
    project.moderated_by = current_admin.id

    db.commit()
    db.refresh(project)
    return project


# ===== FORM BUILDER ENDPOINTS =====

# --- Admin Form Template CRUD ---

@router.post("/{project_id}/form-template", response_model=FormTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_form_template(
    project_id: int,
    form_data: FormTemplateCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.CREATE))
):
    """
    Admin: Create a custom form template for an application project.
    Only the project owner or super_admin can create forms.
    """
    # Verify project exists and is of type 'application'
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if project.project_type != "application":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form templates can only be created for application projects"
        )
    
    # Check ownership (NPO/MSB can only edit their own projects)
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to manage this project")
    
    # Check if template already exists
    existing_template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).first()
    
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form template already exists for this project. Use PUT to update."
        )
    
    # Convert fields to dict format for JSONB storage
    fields_data = [field.dict() for field in form_data.fields]
    
    # Create template
    template = ProjectFormTemplate(
        project_id=project_id,
        title_kz=form_data.title_kz,
        title_ru=form_data.title_ru,
        description_kz=form_data.description_kz,
        description_ru=form_data.description_ru,
        fields=fields_data,
        is_active=True
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.get("/{project_id}/form-template", response_model=FormTemplateResponse)
def get_form_template(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Public: Get form template for a project. Anyone can view to fill out the form.
    """
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id,
        ProjectFormTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form template not found for this project"
        )
    
    return template


@router.put("/{project_id}/form-template", response_model=FormTemplateResponse)
def update_form_template(
    project_id: int,
    form_data: FormTemplateUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE))
):
    """
    Admin: Update form template. Only project owner or super_admin can update.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to manage this project")
    
    # Get template
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form template not found"
        )
    
    # Update fields
    if form_data.title_kz is not None:
        template.title_kz = form_data.title_kz
    if form_data.title_ru is not None:
        template.title_ru = form_data.title_ru
    if form_data.description_kz is not None:
        template.description_kz = form_data.description_kz
    if form_data.description_ru is not None:
        template.description_ru = form_data.description_ru
    if form_data.fields is not None:
        template.fields = [field.dict() for field in form_data.fields]
    if form_data.is_active is not None:
        template.is_active = form_data.is_active
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/{project_id}/form-template", status_code=status.HTTP_204_NO_CONTENT)
def delete_form_template(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.DELETE))
):
    """
    Admin: Delete form template. Only project owner or super_admin can delete.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to manage this project")
    
    # Get template
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form template not found"
        )
    
    db.delete(template)
    db.commit()
    
    return None


# --- Public Form Submission ---

@router.post("/{project_id}/form/submit", response_model=FormSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_form(
    project_id: int,
    submission_data: FormSubmissionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.optional_get_current_user)  # Optional auth
):
    """
    Public: Submit a form response. Authentication is optional.
    """
    # Verify project exists and is active
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "application"
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not an application project"
        )
    
    # Check if project is active
    now = datetime.utcnow()
    if project.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not currently accepting applications"
        )
    
    if now < project.start_date or now > project.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in active period"
        )
    
    # Get form template
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id,
        ProjectFormTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form template not found"
        )
    
    # Validate responses match template fields (basic validation)
    template_field_ids = {field['id'] for field in template.fields}
    response_field_ids = set(submission_data.responses.keys())
    
    # Check required fields
    required_field_ids = {field['id'] for field in template.fields if field.get('required', False)}
    missing_required = required_field_ids - response_field_ids
    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {missing_required}"
        )
    
    # Create submission
    user_id = current_user.id if current_user else None
    
    submission = ProjectFormSubmission(
        project_id=project_id,
        form_template_id=template.id,
        user_id=user_id,
        phone_number=submission_data.phone_number,
        email=submission_data.email,
        applicant_name=submission_data.applicant_name,
        responses=submission_data.responses,
        status="pending"
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    return submission


# --- Admin Submission Management ---

@router.get("/{project_id}/submissions", response_model=FormSubmissionListResponse)
def get_submissions(
    project_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.READ))
):
    """
    Admin: Get list of form submissions with filtering and pagination.
    Only project owner or super_admin can view submissions.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view submissions for this project")
    
    # Build query
    query = db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.project_id == project_id
    )
    
    # Apply filters
    if status:
        query = query.filter(ProjectFormSubmission.status == status)
    
    if start_date:
        query = query.filter(ProjectFormSubmission.submitted_at >= start_date)
    
    if end_date:
        query = query.filter(ProjectFormSubmission.submitted_at <= end_date)
    
    if search:
        # Search in name, phone, email
        search_pattern = f"%{search}%"
        query = query.filter(
            (ProjectFormSubmission.applicant_name.ilike(search_pattern)) |
            (ProjectFormSubmission.phone_number.ilike(search_pattern)) |
            (ProjectFormSubmission.email.ilike(search_pattern))
        )
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    submissions = query.order_by(desc(ProjectFormSubmission.submitted_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "submissions": submissions
    }


@router.get("/{project_id}/submissions/{submission_id}", response_model=FormSubmissionResponse)
def get_submission_detail(
    project_id: int,
    submission_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.READ))
):
    """
    Admin: Get detailed view of a single submission.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view this submission")
    
    # Get submission
    submission = db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.id == submission_id,
        ProjectFormSubmission.project_id == project_id
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    return submission


@router.put("/{project_id}/submissions/{submission_id}/status", response_model=FormSubmissionResponse)
def update_submission_status(
    project_id: int,
    submission_id: int,
    status_data: FormSubmissionUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE))
):
    """
    Admin: Approve or reject a submission.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update this submission")
    
    # Get submission
    submission = db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.id == submission_id,
        ProjectFormSubmission.project_id == project_id
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Update status
    if status_data.status:
        submission.status = status_data.status
        submission.reviewed_by = current_admin.id
        submission.reviewed_at = datetime.utcnow()
    
    if status_data.admin_comment is not None:
        submission.admin_comment = status_data.admin_comment
    
    db.commit()
    db.refresh(submission)
    
    return submission


# --- Analytics & Export ---

@router.get("/{project_id}/analytics", response_model=FormAnalyticsResponse)
def get_form_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.READ))
):
    """
    Admin: Get analytics and statistics for form submissions.
    """
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view analytics for this project")
    
    # Get all submissions for this project
    submissions = db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.project_id == project_id
    ).all()
    
    total_submissions = len(submissions)
    pending_count = len([s for s in submissions if s.status == "pending"])
    approved_count = len([s for s in submissions if s.status == "approved"])
    rejected_count = len([s for s in submissions if s.status == "rejected"])
    
    # Submissions over time (group by date)
    from collections import defaultdict
    submissions_by_date = defaultdict(int)
    for sub in submissions:
        date_str = sub.submitted_at.strftime("%Y-%m-%d")
        submissions_by_date[date_str] += 1
    
    submissions_over_time = [
        {"date": date, "count": count}
        for date, count in sorted(submissions_by_date.items())
    ]
    
    # Field statistics (aggregate responses for dropdown/radio/checkbox fields)
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).first()
    
    field_statistics = {}
    if template:
        for field in template.fields:
            field_id = field['id']
            field_type = field['type']
            
            # Only calculate stats for categorical fields
            if field_type in ['dropdown', 'radio', 'checkbox', 'rating']:
                responses_for_field = []
                for sub in submissions:
                    if field_id in sub.responses:
                        value = sub.responses[field_id]
                        if isinstance(value, list):
                            responses_for_field.extend(value)
                        else:
                            responses_for_field.append(value)
                
                # Count occurrences
                from collections import Counter
                value_counts = Counter(responses_for_field)
                field_statistics[field_id] = {
                    "field_label_kz": field.get('label_kz', ''),
                    "field_label_ru": field.get('label_ru', ''),
                    "type": field_type,
                    "value_counts": dict(value_counts)
                }
    
    # Calculate average submissions per day
    if submissions:
        first_submission = min(s.submitted_at for s in submissions)
        days_active = (datetime.utcnow() - first_submission).days + 1
        avg_per_day = total_submissions / days_active if days_active > 0 else 0
    else:
        avg_per_day = 0.0
    
    return {
        "total_submissions": total_submissions,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "submissions_over_time": submissions_over_time,
        "field_statistics": field_statistics,
        "avg_submissions_per_day": round(avg_per_day, 2)
    }


@router.post("/{project_id}/submissions/export")
def export_submissions(
    project_id: int,
    format: str = "csv",  # csv or excel
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.PROJECTS, Permission.READ))
):
    """
    Admin: Export submissions to CSV or Excel format.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check ownership
    if current_admin.role not in ['administrator', 'super_admin']:
        if project.admin_id != current_admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to export submissions")
    
    # Get submissions
    query = db.query(ProjectFormSubmission).filter(
        ProjectFormSubmission.project_id == project_id
    )
    
    if status:
        query = query.filter(ProjectFormSubmission.status == status)
    
    submissions = query.order_by(desc(ProjectFormSubmission.submitted_at)).all()
    
    # Get form template for field labels
    template = db.query(ProjectFormTemplate).filter(
        ProjectFormTemplate.project_id == project_id
    ).first()
    
    if not template or not submissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data to export"
        )
    
    # Prepare CSV
    output = io.StringIO()
    
    # Build header row
    header = ["ID", "Submission Date", "Name", "Phone", "Email", "Status", "Admin Comment"]
    
    # Add field labels
    for field in template.fields:
        label = field.get('label_ru', field.get('label_kz', field['id']))
        header.append(label)
    
    writer = csv.writer(output)
    writer.writerow(header)
    
    # Write data rows
    for sub in submissions:
        row = [
            sub.id,
            sub.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            sub.applicant_name or "",
            sub.phone_number,
            sub.email or "",
            sub.status,
            sub.admin_comment or ""
        ]
        
        # Add responses
        for field in template.fields:
            field_id = field['id']
            value = sub.responses.get(field_id, "")
            # Convert lists to comma-separated string
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            row.append(value)
        
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}_submissions.csv"}
    )


# --- File Upload for Form Fields ---

@router.post("/{project_id}/form/upload-file")
async def upload_form_field_file(
    project_id: int,
    field_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Public: Upload a file for a form field. Returns file URL to include in submission.
    """
    # Validate file size (10MB max)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is 10MB."
        )
    
    # Validate file type (whitelist)
    allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create directory structure
    upload_dir = f"uploads/forms/project_{project_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Return URL
    file_url = f"/{file_path}"
    
    return {
        "file_url": get_full_url(file_url),
        "field_id": field_id,
        "filename": file.filename,
        "size": file_size
    }