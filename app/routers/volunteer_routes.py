# volunteer_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from app.database import get_db
from app import models, oauth2
from app.v_models import *
from app.v_schemas import *
from datetime import datetime, timedelta
from typing import Optional, List
import os
import uuid

router = APIRouter(prefix="/api/v2/volunteer", tags=["Volunteer"])


# === ЛИЧНЫЙ КАБИНЕТ ===

@router.get("/dashboard")
def get_volunteer_dashboard(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Главная страница личного кабинета волонтера
    # """
    # if current_user.user_type != "VOLUNTEER":
    #     raise HTTPException(status_code=403, detail="Только для волонтеров")

    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль волонтера не найден")

    # Баланс и статистика
    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if not balance:
        balance = VolunteerBalance(volunteer_id=volunteer.id)
        db.add(balance)
        db.commit()
        db.refresh(balance)

    # Требования для повышения
    status_requirements = {
        "VOLUNTEER": {"next": "TEAM_LEADER", "v_coins_needed": 150},
        "TEAM_LEADER": {"next": "SUPERVISOR", "v_coins_needed": 200},
        "SUPERVISOR": {"next": "COORDINATOR", "v_coins_needed": 300},
        "COORDINATOR": {"next": None, "v_coins_needed": 0}
    }

    current_req = status_requirements.get(volunteer.volunteer_status, {})
    progress_percent = 0
    if current_req.get("v_coins_needed"):
        progress_percent = min(100, (balance.current_balance / current_req["v_coins_needed"]) * 100)

    # История последних мероприятий
    recent_events = db.query(EventApplication).filter(
        EventApplication.volunteer_id == volunteer.id
    ).order_by(desc(EventApplication.created_at)).limit(5).all()

    return {
        "volunteer": {
            "id": volunteer.id,
            "full_name": volunteer.full_name,
            "status": volunteer.volunteer_status,
            "direction_id": volunteer.direction_id
        },
        "balance": {
            "current": balance.current_balance,
            "total_earned": balance.total_earned,
            "total_spent": balance.total_spent,
            "warning_level": balance.warning_level,
            "events_participated": balance.events_participated,
            "events_missed": balance.events_missed
        },
        "progress": {
            "current_status": volunteer.volunteer_status,
            "next_status": current_req.get("next"),
            "v_coins_needed": current_req.get("v_coins_needed", 0),
            "progress_percent": round(progress_percent, 1)
        },
        "recent_events": [
            {
                "id": app.id,
                "event_id": app.event_id,
                "role": app.applied_role,
                "status": app.status,
                "attended": app.attended,
                "v_coins_earned": app.v_coins_earned
            }
            for app in recent_events
        ]
    }


@router.get("/my-history")
def get_volunteer_history(
        skip: int = 0,
        limit: int = 20,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    История мероприятий и транзакций V-coins
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    # История заявок
    applications = db.query(EventApplication).filter(
        EventApplication.volunteer_id == volunteer.id
    ).order_by(desc(EventApplication.created_at)).offset(skip).limit(limit).all()

    # История V-coins
    transactions = db.query(VCoinTransaction).filter(
        VCoinTransaction.volunteer_id == volunteer.id
    ).order_by(desc(VCoinTransaction.created_at)).limit(10).all()

    return {
        "applications": [
            {
                "id": app.id,
                "event_id": app.event_id,
                "role": app.applied_role,
                "status": app.status,
                "attended": app.attended,
                "missed": app.missed,
                "report_submitted": app.report_submitted,
                "v_coins_earned": app.v_coins_earned,
                "created_at": app.created_at
            }
            for app in applications
        ],
        "transactions": [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.transaction_type,
                "description": tx.description,
                "created_at": tx.created_at
            }
            for tx in transactions
        ]
    }


# === КАТАЛОГ МЕРОПРИЯТИЙ ===
@router.get("/events")
def get_events_catalog(
        skip: int = 0,
        limit: int = 20,
        direction_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        location: Optional[str] = None,
        status: Optional[str] = "upcoming",
        db: Session = Depends(get_db)
):
    """
    Каталог мероприятий с фильтрами
    """
    query = db.query(VolunteerEvent).filter(VolunteerEvent.is_active == True)

    if status:
        query = query.filter(VolunteerEvent.status == status)

    if direction_id:
        query = query.filter(VolunteerEvent.direction_id == direction_id)

    if date_from:
        query = query.filter(VolunteerEvent.event_date >= date_from)

    if date_to:
        query = query.filter(VolunteerEvent.event_date <= date_to)

    if location:
        query = query.filter(VolunteerEvent.location.ilike(f"%{location}%"))

    events = query.order_by(VolunteerEvent.event_date).offset(skip).limit(limit).all()

    # Формируем результат с подсчетом заявок и суммой бонусов за задачи
    events_with_stats = []
    for event in events:
        total_applications = db.query(func.count(EventApplication.id)).filter(
            EventApplication.event_id == event.id,
            EventApplication.status == "approved"
        ).scalar()

        # Считаем сумму всех бонусов за задачи
        tasks_total_bonus = db.query(func.coalesce(func.sum(EventTask.v_coins_bonus), 0)).filter(
            EventTask.event_id == event.id
        ).scalar()

        events_with_stats.append({
            "id": event.id,
            "title": event.title,
            "title_kz": event.title_kz,
            "description": event.description,
            "description_kz": event.description_kz,
            "event_date": event.event_date,
            "location": event.location,
            "direction_id": event.direction_id,
            "v_coins_reward": event.v_coins_reward,
            "photo_bonus": event.photo_bonus,
            "status": event.status,
            "required_volunteers": event.required_volunteers,
            "required_team_leaders": event.required_team_leaders,
            "required_supervisors": event.required_supervisors,
            "total_applications": total_applications,
            "tasks_total_bonus": tasks_total_bonus  # ← ДОБАВЛЕНО для фронта
        })

    return {
        "total": query.count(),
        "events": events_with_stats
    }

@router.post("/events/{event_id}/cancel")  # Изменено с @router.delete
def cancel_application(
        event_id: int,  # Изменено - теперь берем event_id
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Отмена заявки
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    application = db.query(EventApplication).filter(
        EventApplication.event_id == event_id,  # Изменено
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if application.status not in ["pending", "approved"]:
        raise HTTPException(status_code=400, detail="Невозможно отменить заявку")

    application.status = "cancelled"
    db.commit()

    return {"message": "Заявка отменена"}
@router.get("/events/{event_id}")
def get_event_detail(
        event_id: int,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Детальная страница мероприятия
    """
    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    # Проверяем заявку пользователя
    my_application = None
    if volunteer:
        my_application = db.query(EventApplication).filter(
            EventApplication.event_id == event_id,
            EventApplication.volunteer_id == volunteer.id
        ).first()

    # Чек-лист задач
    tasks = db.query(EventTask).filter(EventTask.event_id == event_id).all()

    # Считаем активные заявки
    total_applications = db.query(func.count(EventApplication.id)).filter(
        EventApplication.event_id == event_id,
        EventApplication.status.in_(["pending", "approved"])
    ).scalar()

    return {
        "event": {
            "id": event.id,
            "title": event.title,
            "title_kz": event.title_kz,
            "description": event.description,
            "description_kz": event.description_kz,
            "event_date": event.event_date,
            "location": event.location,
            "direction_id": event.direction_id,
            "v_coins_reward": event.v_coins_reward,
            "photo_bonus": event.photo_bonus,
            "status": event.status,
            "whatsapp_group_link": event.whatsapp_group_link,
            "required_volunteers": event.required_volunteers,
            "required_team_leaders": event.required_team_leaders,
            "required_supervisors": event.required_supervisors,
            "total_applications": total_applications
        },
        "my_application": {
            "id": my_application.id,
            "role": my_application.applied_role,
            "status": my_application.status,
            "report_submitted": my_application.report_submitted  # ← ДОБАВЬ ЭТО
        } if my_application else None,
        "tasks": [  # ← УБЕДИСЬ ЧТО ЭТО ЕСТЬ
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "for_role": task.for_role,
                "is_required": task.is_required,
                "v_coins_bonus": task.v_coins_bonus
            }
            for task in tasks
        ]
    }
@router.post("/events/{event_id}/apply")
def apply_for_event(
        event_id: int,
        application_data: EventApplicationCreate,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Подача заявки на мероприятие
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль волонтера не найден")

    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == event_id, VolunteerEvent.is_active == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # Проверка что еще не подавал заявку
    existing = db.query(EventApplication).filter(
        EventApplication.event_id == event_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Вы уже подали заявку на это мероприятие")

    # Проверка роли
    allowed_roles = ["VOLUNTEER", "TEAM_LEADER", "SUPERVISOR", "COORDINATOR"]
    if application_data.role not in allowed_roles:  # ИЗМЕНЕНО
        raise HTTPException(status_code=400, detail="Недопустимая роль")

    # Проверка статуса волонтера для роли
    status_hierarchy = {
        "VOLUNTEER": 1,
        "TEAM_LEADER": 2,
        "SUPERVISOR": 3,
        "COORDINATOR": 4
    }

    if status_hierarchy[application_data.role] > status_hierarchy[volunteer.volunteer_status]:  # ИЗМЕНЕНО
        raise HTTPException(
            status_code=403,
            detail=f"Для роли {application_data.role} нужен статус выше"
        )

    # Создаем заявку
    new_app = EventApplication(
        event_id=event_id,
        volunteer_id=volunteer.id,
        applied_role=application_data.role,  # ИЗМЕНЕНО
        status="pending"
    )

    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    return {
        "message": "Заявка успешно подана",
        "application_id": new_app.id,
        "status": new_app.status,
        "whatsapp_link": event.whatsapp_group_link
    }

@router.delete("/applications/{application_id}")
def cancel_application(
        application_id: int,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Отмена заявки
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    application = db.query(EventApplication).filter(
        EventApplication.id == application_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if application.status not in ["pending", "approved"]:
        raise HTTPException(status_code=400, detail="Невозможно отменить заявку")

    application.status = "cancelled"
    db.commit()

    return {"message": "Заявка отменена"}


# === ОТЧЕТЫ ===

@router.post("/applications/{application_id}/report")
async def submit_report(
        application_id: int,
        report_text: str = None,
        photo: UploadFile = File(None),
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Подача отчета о мероприятии
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    application = db.query(EventApplication).filter(
        EventApplication.id == application_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if not application.attended:
        raise HTTPException(status_code=400, detail="Сначала нужно отметить присутствие")

    if application.report_submitted:
        raise HTTPException(status_code=400, detail="Отчет уже подан")

    # Сохраняем фото
    photo_url = None
    if photo:
        upload_dir = "uploads/reports"
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = photo.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(upload_dir, unique_name)

        with open(file_path, "wb") as f:
            content = await photo.read()
            f.write(content)

        photo_url = f"/{file_path}"

    # Обновляем заявку
    application.report_text = report_text
    application.report_photo_url = photo_url
    application.report_submitted = True

    # Начисляем V-coins
    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == application.event_id).first()
    bonus = event.photo_bonus if photo_url else 0

    application.v_coins_earned += bonus

    # Транзакция V-coins
    if bonus > 0:
        transaction = VCoinTransaction(
            volunteer_id=volunteer.id,
            amount=bonus,
            transaction_type="bonus",
            description=f"Бонус за фото в отчете",
            event_id=event.id
        )
        db.add(transaction)

        # Обновляем баланс
        balance = db.query(VolunteerBalance).filter(
            VolunteerBalance.volunteer_id == volunteer.id
        ).first()
        if balance:
            balance.current_balance += bonus
            balance.total_earned += bonus

    db.commit()

    return {
        "message": "Отчет успешно подан",
        "bonus_earned": bonus,
        "total_earned": application.v_coins_earned
    }


# === ЗАДАЧИ (ЧЕК-ЛИСТ) ===
# === ОТЧЕТЫ ПО ЗАДАЧАМ ===

@router.get("/applications/{application_id}/tasks")
def get_my_tasks(
        application_id: int,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Чек-лист задач для моей заявки с возможностью подачи отчётов
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    application = db.query(EventApplication).filter(
        EventApplication.id == application_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Все задачи мероприятия для моей роли
    tasks = db.query(EventTask).filter(
        EventTask.event_id == application.event_id,
        (EventTask.for_role == application.applied_role) | (EventTask.for_role == "ALL")
    ).all()

    result = []
    for task in tasks:
        # Проверяем есть ли completion
        completion = db.query(TaskCompletion).filter(
            TaskCompletion.task_id == task.id,
            TaskCompletion.application_id == application_id
        ).first()

        # Если нет - создаём
        if not completion:
            completion = TaskCompletion(
                task_id=task.id,
                application_id=application_id
            )
            db.add(completion)
            db.flush()

        result.append({
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "is_required": task.is_required,
                "v_coins_bonus": task.v_coins_bonus
            },
            "completion": {
                "id": completion.id,
                "completed": completion.completed,
                "report_text": completion.report_text,
                "report_photo_url": completion.report_photo_url,
                "report_status": completion.report_status,
                "admin_comment": completion.admin_comment,
                "v_coins_earned": completion.v_coins_earned,
                "completed_at": completion.completed_at
            }
        })

    db.commit()
    return {"tasks": result}

from fastapi import Form  # ← Добавь в импорты
@router.post("/tasks/{task_id}/submit-report")
async def submit_task_report(
        task_id: int,
        application_id: int = Form(...),
        report_text: str = Form(None),
        photo: UploadFile = File(None),
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Подать отчёт по конкретной задаче
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    application = db.query(EventApplication).filter(
        EventApplication.id == application_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    task = db.query(EventTask).filter(EventTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Находим completion
    completion = db.query(TaskCompletion).filter(
        TaskCompletion.task_id == task_id,
        TaskCompletion.application_id == application_id
    ).first()

    if not completion:
        completion = TaskCompletion(
            task_id=task_id,
            application_id=application_id,
            report_status="not_submitted"
        )
        db.add(completion)
        db.flush()

    # ========== ИСПРАВЛЕНО: Проверка статуса ==========
    # Можно подавать отчёт только если:
    # - not_submitted (первый раз)
    # - rejected (подача заново после отклонения)
    if completion.report_status in ["pending", "approved"]:
        if completion.report_status == "pending":
            raise HTTPException(status_code=400, detail="Отчёт уже отправлен и находится на проверке")
        else:
            raise HTTPException(status_code=400, detail="Отчёт уже одобрен")

    # Сохраняем фото
    photo_url = None
    if photo:
        upload_dir = "uploads/task_reports"
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = photo.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(upload_dir, unique_name)

        with open(file_path, "wb") as f:
            content = await photo.read()
            f.write(content)

        photo_url = f"/{file_path}"

    # Обновляем completion
    completion.report_text = report_text
    completion.report_photo_url = photo_url
    completion.report_status = "pending"  # На проверке
    completion.completed = True
    completion.completed_at = datetime.utcnow()
    completion.admin_comment = None  # Очищаем старый комментарий админа

    db.commit()
    db.refresh(completion)

    return {
        "message": "Отчёт отправлен на проверку",
        "completion_id": completion.id,
        "status": "pending"
    }

@router.post("/tasks/{task_id}/complete")
def mark_task_complete(
        task_id: int,
        application_id: int,
        notes: Optional[str] = None,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Отметить задачу как выполненную
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    application = db.query(EventApplication).filter(
        EventApplication.id == application_id,
        EventApplication.volunteer_id == volunteer.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    task = db.query(EventTask).filter(EventTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверяем/создаем completion
    completion = db.query(TaskCompletion).filter(
        TaskCompletion.task_id == task_id,
        TaskCompletion.application_id == application_id
    ).first()

    if not completion:
        completion = TaskCompletion(
            task_id=task_id,
            application_id=application_id
        )
        db.add(completion)

    completion.completed = True
    completion.completed_at = datetime.utcnow()
    completion.notes = notes

    # Начисляем бонус
    if task.v_coins_bonus > 0:
        application.v_coins_earned += task.v_coins_bonus

        transaction = VCoinTransaction(
            volunteer_id=volunteer.id,
            amount=task.v_coins_bonus,
            transaction_type="bonus",
            description=f"Выполнение задачи: {task.title}",
            event_id=application.event_id
        )
        db.add(transaction)

        balance = db.query(VolunteerBalance).filter(
            VolunteerBalance.volunteer_id == volunteer.id
        ).first()
        if balance:
            balance.current_balance += task.v_coins_bonus
            balance.total_earned += task.v_coins_bonus

    db.commit()

    return {
        "message": "Задача отмечена как выполненная",
        "bonus_earned": task.v_coins_bonus
    }


# === ПЛЮШКИ/БОНУСЫ ===

@router.get("/benefits")
def get_benefits_catalog(
        category: Optional[str] = None,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Каталог плюшек
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    query = db.query(Benefit).filter(Benefit.is_active == True)

    if category:
        query = query.filter(Benefit.category == category)

    benefits = query.all()

    status_hierarchy = {
        "VOLUNTEER": 1,
        "TEAM_LEADER": 2,
        "SUPERVISOR": 3,
        "COORDINATOR": 4
    }

    result = []
    for benefit in benefits:
        can_afford = balance.current_balance >= benefit.v_coins_cost if balance else False
        can_access = status_hierarchy[volunteer.volunteer_status] >= status_hierarchy[benefit.min_status]

        result.append({
            "id": benefit.id,
            "title": benefit.title,
            "title_kz": benefit.title_kz,
            "description": benefit.description,
            "v_coins_cost": benefit.v_coins_cost,
            "min_status": benefit.min_status,
            "category": benefit.category,
            "icon_url": benefit.icon_url,
            "can_afford": can_afford,
            "can_access": can_access,
            "available": can_afford and can_access
        })

    return {
        "my_balance": balance.current_balance if balance else 0,
        "my_status": volunteer.volunteer_status,
        "benefits": result
    }


@router.post("/benefits/{benefit_id}/purchase")
def purchase_benefit(
        benefit_id: int,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Покупка плюшки
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    benefit = db.query(Benefit).filter(
        Benefit.id == benefit_id,
        Benefit.is_active == True
    ).first()

    if not benefit:
        raise HTTPException(status_code=404, detail="Плюшка не найдена")

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if not balance or balance.current_balance < benefit.v_coins_cost:
        raise HTTPException(status_code=400, detail="Недостаточно V-coins")

    # Проверка статуса
    status_hierarchy = {
        "VOLUNTEER": 1,
        "TEAM_LEADER": 2,
        "SUPERVISOR": 3,
        "COORDINATOR": 4
    }

    if status_hierarchy[volunteer.volunteer_status] < status_hierarchy[benefit.min_status]:
        raise HTTPException(status_code=403, detail="Недостаточный статус")

    # Проверка лимита
    if benefit.stock_limit and benefit.stock_available <= 0:
        raise HTTPException(status_code=400, detail="Плюшка закончилась")

    # Покупка
    purchase = BenefitPurchase(
        volunteer_id=volunteer.id,
        benefit_id=benefit_id,
        v_coins_spent=benefit.v_coins_cost,
        status="pending"
    )
    db.add(purchase)

    # Списываем V-coins
    balance.current_balance -= benefit.v_coins_cost
    balance.total_spent += benefit.v_coins_cost

    # Транзакция
    transaction = VCoinTransaction(
        volunteer_id=volunteer.id,
        amount=-benefit.v_coins_cost,
        transaction_type="spent",
        description=f"Покупка: {benefit.title}",
        benefit_id=benefit_id
    )
    db.add(transaction)

    # Уменьшаем сток
    if benefit.stock_limit:
        benefit.stock_available -= 1

    db.commit()
    db.refresh(purchase)

    return {
        "message": "Плюшка успешно куплена",
        "purchase_id": purchase.id,
        "remaining_balance": balance.current_balance
    }


@router.get("/my-purchases")
def get_my_purchases(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Мои покупки плюшек
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    purchases = db.query(BenefitPurchase).filter(
        BenefitPurchase.volunteer_id == volunteer.id
    ).order_by(desc(BenefitPurchase.created_at)).all()

    result = []
    for purchase in purchases:
        benefit = db.query(Benefit).filter(Benefit.id == purchase.benefit_id).first()
        result.append({
            "id": purchase.id,
            "benefit": {
                "title": benefit.title if benefit else "Удалено",
                "cost": purchase.v_coins_spent
            },
            "status": purchase.status,
            "created_at": purchase.created_at,
            "completed_at": purchase.completed_at
        })

    return {"purchases": result}


# === ПОВЫШЕНИЕ СТАТУСА ===

@router.get("/promotion-requirements")
def get_promotion_requirements(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Требования для повышения
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    requirements = {
        "VOLUNTEER": {
            "next_status": "TEAM_LEADER",
            "v_coins_required": 150,
            "benefits": ["Доступ к роли тим-лидера", "Управление командой", "Больше бонусов"]
        },
        "TEAM_LEADER": {
            "next_status": "SUPERVISOR",
            "v_coins_required": 200,
            "benefits": ["Доступ к роли супервайзера", "Контроль проектов", "VIP плюшки"]
        },
        "SUPERVISOR": {
            "next_status": "COORDINATOR",
            "v_coins_required": 300,
            "benefits": ["Высший статус", "Координация программ", "Все привилегии"]
        },
        "COORDINATOR": {
            "next_status": None,
            "v_coins_required": 0,
            "benefits": ["Максимальный уровень достигнут"]
        }
    }

    current_req = requirements.get(volunteer.volunteer_status, {})
    can_request = False

    if current_req.get("v_coins_required"):
        can_request = balance.current_balance >= current_req["v_coins_required"]

    return {
        "current_status": volunteer.volunteer_status,
        "current_balance": balance.current_balance if balance else 0,
        "requirements": current_req,
        "can_request": can_request,
        "all_levels": requirements
    }


@router.post("/request-promotion")
def request_promotion(
        request_data: dict,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Запрос на повышение
    """
    requested_status = request_data.get("requested_status")

    if not requested_status:
        raise HTTPException(status_code=400, detail="requested_status is required")

    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Профиль волонтера не найден")

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if not balance:
        raise HTTPException(status_code=404, detail="Баланс волонтера не найден")

    # Проверка логичности повышения
    hierarchy = {
        "VOLUNTEER": {"next": "TEAM_LEADER", "coins": 150},
        "TEAM_LEADER": {"next": "SUPERVISOR", "coins": 200},
        "SUPERVISOR": {"next": "COORDINATOR", "coins": 300}
    }

    current_level = hierarchy.get(volunteer.volunteer_status)

    if not current_level or current_level["next"] != requested_status:
        raise HTTPException(status_code=400, detail="Недопустимое повышение")

    if balance.current_balance < current_level["coins"]:
        raise HTTPException(status_code=400, detail="Недостаточно V-coins")

    # Проверка существующих запросов
    existing = db.query(PromotionRequest).filter(
        PromotionRequest.volunteer_id == volunteer.id,
        PromotionRequest.status == "pending"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="У вас уже есть активный запрос")

    # Создаем запрос
    request = PromotionRequest(
        volunteer_id=volunteer.id,
        current_status=volunteer.volunteer_status,
        requested_status=requested_status,
        v_coins_at_request=balance.current_balance
    )

    db.add(request)
    db.commit()

    return {
        "message": "Запрос на повышение отправлен",
        "request_id": request.id,
        "status": "pending"
    }


@router.get("/my-promotion-requests")
def get_my_promotion_requests(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Мои запросы на повышение
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    requests = db.query(PromotionRequest).filter(
        PromotionRequest.volunteer_id == volunteer.id
    ).order_by(desc(PromotionRequest.created_at)).all()

    return {
        "requests": [
            {
                "id": req.id,
                "current_status": req.current_status,
                "requested_status": req.requested_status,
                "status": req.status,
                "v_coins_at_request": req.v_coins_at_request,
                "admin_comment": req.admin_comment,
                "created_at": req.created_at,
                "reviewed_at": req.reviewed_at
            }
            for req in requests
        ]
    }


# === РЕЙТИНГ ===

@router.get("/leaderboard")
def get_leaderboard(
        period: str = "month",  # week, month, all
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """
    Рейтинг волонтеров
    """
    # Базовый запрос
    query = db.query(
        Volunteer.id,
        Volunteer.full_name,
        Volunteer.volunteer_status,
        VolunteerBalance.current_balance,
        VolunteerBalance.total_earned,
        VolunteerBalance.events_participated
    ).join(
        VolunteerBalance,
        Volunteer.id == VolunteerBalance.volunteer_id
    )

    # Фильтр по периоду (можно улучшить)
    if period == "week":
        # Топ за неделю по earned
        query = query.order_by(desc(VolunteerBalance.total_earned))
    elif period == "month":
        query = query.order_by(desc(VolunteerBalance.total_earned))
    else:
        query = query.order_by(desc(VolunteerBalance.total_earned))

    leaders = query.limit(limit).all()

    result = []
    for i, leader in enumerate(leaders, 1):
        result.append({
            "position": i,
            "volunteer_id": leader.id,
            "full_name": leader.full_name,
            "status": leader.volunteer_status,
            "current_balance": leader.current_balance,
            "total_earned": leader.total_earned,
            "events_count": leader.events_participated
        })

    return {
        "period": period,
        "leaderboard": result
    }


# === ДОСТИЖЕНИЯ/БЕЙДЖИ ===

@router.get("/achievements")
def get_achievements(
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    """
    Все достижения и мои полученные
    """
    volunteer = db.query(Volunteer).filter(Volunteer.user_id == current_user.id).first()

    all_achievements = db.query(Achievement).filter(Achievement.is_active == True).all()

    my_achievements = db.query(VolunteerAchievement).filter(
        VolunteerAchievement.volunteer_id == volunteer.id
    ).all()

    my_ids = {a.achievement_id for a in my_achievements}

    result = []
    for ach in all_achievements:
        result.append({
            "id": ach.id,
            "title": ach.title,
            "description": ach.description,
            "icon_url": ach.icon_url,
            "badge_color": ach.badge_color,
            "earned": ach.id in my_ids,
            "earned_at": next((a.earned_at for a in my_achievements if a.achievement_id == ach.id), None)
        })

    return {
        "total_achievements": len(all_achievements),
        "earned_count": len(my_ids),
        "achievements": result
    }





