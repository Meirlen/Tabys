from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app import oauth2
from app.project_models import (
    Project, ProjectGallery, VotingParticipant, Vote,
    ProjectApplication, VotingResults
)
from app.project_schemas import (
    ProjectCreateMulti, ProjectUpdateMulti, VotingParticipantCreateMulti,
    format_project_response, format_participant_response, validate_language
)
from typing import List, Optional
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v2/projects", tags=["Projects Multi-language"])

# Константа для базового URL
BASE_URL = "aisoft09.shop"


def get_full_url(path: Optional[str]) -> Optional[str]:
    """Формирует полный URL из относительного пути"""
    if not path:
        return None
    if path.startswith('http'):
        return path
    return f"{BASE_URL}{path}"


# === ПРОЕКТЫ ===
@router.post("/", response_model=dict)
def create_project(
        title_kz: str = Form(..., description="Заголовок на казахском"),
        title_ru: str = Form(..., description="Заголовок на русском"),
        description_kz: str = Form(..., description="Описание на казахском"),
        description_ru: str = Form(..., description="Описание на русском"),
        author: str = Form(...),
        project_type: str = Form(..., description="voting или application"),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        video_url: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Создание нового проекта с мультиязычными полями"""

    # Валидация типа проекта
    if project_type not in ["voting", "application"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_type должен быть 'voting' или 'application'"
        )

    # Валидация дат
    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дата завершения должна быть позже даты начала"
        )

    new_project = Project(
        title_kz=title_kz,
        title_ru=title_ru,
        description_kz=description_kz,
        description_ru=description_ru,
        author=author,
        project_type=project_type,
        start_date=start_date,
        end_date=end_date,
        video_url=video_url,
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "message": "Проект успешно создан",
        "project_id": new_project.id,
        "title_kz": new_project.title_kz,
        "title_ru": new_project.title_ru,
        "project_type": new_project.project_type
    }


@router.get("/")
def get_projects(
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        project_type: Optional[str] = Query(None, description="Тип проекта"),
        status: Optional[str] = Query(None, description="Статус проекта"),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """Получение списка проектов с локализацией"""

    # Валидация языка
    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = db.query(Project)

    if project_type:
        query = query.filter(Project.project_type == project_type)
    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

    return [
        {
            **format_project_response(project, lang),
            "photo_url": get_full_url(project.photo_url),
            "video_url": get_full_url(project.video_url)
        }
        for project in projects
    ]


@router.get("/{project_id}")
def get_project_detail(
        project_id: int,
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение детальной информации о проекте с локализацией"""

    # Валидация языка
    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        **format_project_response(project, lang),
        "photo_url": get_full_url(project.photo_url),
        "video_url": get_full_url(project.video_url),
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
                **format_participant_response(p, lang),
                "photo_url": get_full_url(p.photo_url),
                "video_url": get_full_url(p.video_url)
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


@router.put("/{project_id}")
def update_project(
        project_id: int,
        title_kz: Optional[str] = Form(None),
        title_ru: Optional[str] = Form(None),
        description_kz: Optional[str] = Form(None),
        description_ru: Optional[str] = Form(None),
        author: Optional[str] = Form(None),
        start_date: Optional[datetime] = Form(None),
        end_date: Optional[datetime] = Form(None),
        video_url: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Обновление проекта с поддержкой мультиязычности"""

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    # Обновляем только переданные поля
    if title_kz is not None:
        project.title_kz = title_kz
    if title_ru is not None:
        project.title_ru = title_ru
    if description_kz is not None:
        project.description_kz = description_kz
    if description_ru is not None:
        project.description_ru = description_ru
    if author is not None:
        project.author = author
    if start_date is not None:
        project.start_date = start_date
    if end_date is not None:
        project.end_date = end_date
    if video_url is not None:
        project.video_url = video_url
    if status is not None:
        if status not in ["draft", "active", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Неверный статус")
        project.status = status

    # Валидация дат
    if project.end_date <= project.start_date:
        raise HTTPException(
            status_code=400,
            detail="Дата завершения должна быть позже даты начала"
        )

    db.commit()
    return {"message": "Проект успешно обновлен"}


@router.delete("/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление проекта"""
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
    """Загрузка основного фото проекта"""

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
    """Загрузка изображения в галерею проекта"""

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
        name_kz: str = Form(..., description="Имя на казахском"),
        name_ru: str = Form(..., description="Имя на русском"),
        description_kz: Optional[str] = Form(None, description="Описание на казахском"),
        description_ru: Optional[str] = Form(None, description="Описание на русском"),
        video_url: Optional[str] = Form(None),
        instagram_url: Optional[str] = Form(None),
        facebook_url: Optional[str] = Form(None),
        linkedin_url: Optional[str] = Form(None),
        twitter_url: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Добавление участника в голосовалку с мультиязычными полями"""

    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден или это не голосовалка"
        )

    participant = VotingParticipant(
        project_id=project_id,
        name_kz=name_kz,
        name_ru=name_ru,
        description_kz=description_kz,
        description_ru=description_ru,
        video_url=video_url,
        instagram_url=instagram_url,
        facebook_url=facebook_url,
        linkedin_url=linkedin_url,
        twitter_url=twitter_url
    )

    db.add(participant)
    db.commit()
    db.refresh(participant)

    return {
        "message": "Участник добавлен",
        "participant_id": participant.id,
        "name_kz": participant.name_kz,
        "name_ru": participant.name_ru
    }


@router.post("/{project_id}/participants/{participant_id}/upload-photo")
async def upload_participant_photo(
        project_id: int,
        participant_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Загрузка фото участника голосования"""

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
        current_user=Depends(oauth2.get_current_user)
):
    """Голосование за участника"""

    participant_id = vote_data.get("participant_id")
    user_id = current_user.id

    if not participant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан ID участника"
        )

    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"
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
        "participant_name_ru": participant.name_ru,
        "participant_name_kz": participant.name_kz,
        "current_votes": participant.votes_count
    }


@router.get("/{project_id}/results")
def get_voting_results(
        project_id: int,
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение результатов голосования с локализацией"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Проверяем, что проект существует и это голосовалка
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.project_type == "voting"
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
            "participant_name": format_participant_response(participant, lang)["name"],
            "photo_url": get_full_url(participant.photo_url),
            "votes_count": participant.votes_count,
            "percentage": f"{percentage:.1f}%"
        })

    return {
        "project_id": project_id,
        "project_title": format_project_response(project, lang)["title"],
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
    """Подача заявки на проект"""

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
        "project_title_ru": project.title_ru,
        "project_title_kz": project.title_kz,
        "status": "pending"
    }


@router.get("/{project_id}/applications")
def get_project_applications(
        project_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Получение заявок по проекту (только для создателей/админов)"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        "project_title": format_project_response(project, lang)["title"],
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
    """Обновление статуса заявки (только для админов)"""

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
def get_project_stats(
        project_id: int,
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение статистики по проекту"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    stats = {
        "project_id": project_id,
        "project_title": format_project_response(project, lang)["title"],
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
                "name": format_participant_response(top_participant, lang)["name"],
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
def get_active_voting_projects(
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение активных проектов-голосовалок с локализацией"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.utcnow()
    projects = db.query(Project).filter(
        Project.project_type == "voting",
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

        project_data = format_project_response(project, lang)
        project_data.update({
            "photo_url": get_full_url(project.photo_url),
            "participants_count": participants_count,
            "votes_count": votes_count
        })
        result.append(project_data)

    return {
        "count": len(result),
        "projects": result
    }


@router.get("/active/applications")
def get_active_application_projects(
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение активных проектов с приемом заявок с локализацией"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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

        project_data = format_project_response(project, lang)
        project_data.update({
            "photo_url": get_full_url(project.photo_url),
            "applications_count": applications_count
        })
        result.append(project_data)

    return {
        "count": len(result),
        "projects": result
    }


@router.get("/my-votes")
def get_my_votes(
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Получение голосов текущего пользователя с локализацией"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = current_user.get("user_id")

    votes = db.query(Vote).filter(Vote.user_id == user_id).order_by(desc(Vote.created_at)).all()

    result = []
    for vote in votes:
        project = db.query(Project).filter(Project.id == vote.project_id).first()
        participant = db.query(VotingParticipant).filter(VotingParticipant.id == vote.participant_id).first()

        result.append({
            "vote_id": vote.id,
            "project_id": vote.project_id,
            "project_title": format_project_response(project, lang)["title"] if project else "Неизвестный проект",
            "participant_id": vote.participant_id,
            "participant_name": format_participant_response(participant, lang)[
                "name"] if participant else "Неизвестный участник",
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
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        db: Session = Depends(get_db)
):
    """Получение заявок пользователя по номеру телефона с локализацией"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    applications = db.query(ProjectApplication).filter(
        ProjectApplication.phone_number == phone_number
    ).order_by(desc(ProjectApplication.created_at)).all()

    result = []
    for app in applications:
        project = db.query(Project).filter(Project.id == app.project_id).first()

        result.append({
            "application_id": app.id,
            "project_id": app.project_id,
            "project_title": format_project_response(project, lang)["title"] if project else "Неизвестный проект",
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
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление изображения из галереи"""

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
    """Удаление участника голосования"""

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
        name_kz: Optional[str] = Form(None),
        name_ru: Optional[str] = Form(None),
        description_kz: Optional[str] = Form(None),
        description_ru: Optional[str] = Form(None),
        video_url: Optional[str] = Form(None),
        instagram_url: Optional[str] = Form(None),
        facebook_url: Optional[str] = Form(None),
        linkedin_url: Optional[str] = Form(None),
        twitter_url: Optional[str] = Form(None),
        db: Session = Depends(get_db),
):
    """Обновление данных участника с поддержкой мультиязычности"""

    participant = db.query(VotingParticipant).filter(
        VotingParticipant.id == participant_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    # Обновляем поля
    if name_kz is not None:
        participant.name_kz = name_kz
    if name_ru is not None:
        participant.name_ru = name_ru
    if description_kz is not None:
        participant.description_kz = description_kz
    if description_ru is not None:
        participant.description_ru = description_ru
    if video_url is not None:
        participant.video_url = video_url
    if instagram_url is not None:
        participant.instagram_url = instagram_url
    if facebook_url is not None:
        participant.facebook_url = facebook_url
    if linkedin_url is not None:
        participant.linkedin_url = linkedin_url
    if twitter_url is not None:
        participant.twitter_url = twitter_url

    db.commit()

    return {"message": "Данные участника обновлены"}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def save_uploaded_file(file: UploadFile, folder: str) -> str:
    """Сохранение загруженного файла"""
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
        q: str = Query(..., min_length=1, description="Поисковый запрос"),
        lang: str = Query("ru", description="Язык ответа (kz/ru)"),
        project_type: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """Поиск проектов по названию и описанию с поддержкой мультиязычности"""

    try:
        lang = validate_language(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Поиск по мультиязычным полям
    if lang == "kz":
        query = db.query(Project).filter(
            Project.title_kz.ilike(f"%{q}%") | Project.description_kz.ilike(f"%{q}%")
        )
    else:
        query = db.query(Project).filter(
            Project.title_ru.ilike(f"%{q}%") | Project.description_ru.ilike(f"%{q}%")
        )

    if project_type:
        query = query.filter(Project.project_type == project_type)
    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()

    return {
        "query": q,
        "language": lang,
        "count": len(projects),
        "projects": [
            {
                **format_project_response(project, lang),
                "photo_url": get_full_url(project.photo_url),
                # Обрезаем описание для краткости
                "description": format_project_response(project, lang)["description"][:200] + "..."
                if len(format_project_response(project, lang)["description"]) > 200
                else format_project_response(project, lang)["description"]
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
    """Завершение проекта с сохранением мультиязычных результатов"""

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    project.status = "completed"
    db.commit()

    # Если это голосовалка, сохраняем результаты с мультиязычными именами
    if project.project_type == "voting":
        participants = db.query(VotingParticipant).filter(
            VotingParticipant.project_id == project_id
        ).order_by(desc(VotingParticipant.votes_count)).all()

        total_votes = sum(p.votes_count for p in participants)

        # Очищаем старые результаты
        db.query(VotingResults).filter(VotingResults.project_id == project_id).delete()

        # Сохраняем новые результаты с мультиязычными именами
        for i, participant in enumerate(participants, 1):
            percentage = (participant.votes_count / total_votes * 100) if total_votes > 0 else 0

            result = VotingResults(
                project_id=project_id,
                participant_id=participant.id,
                participant_name_kz=participant.name_kz,
                participant_name_ru=participant.name_ru,
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