# volunteer_admin_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database import get_db
from app import models, oauth2
from app.v_models import *
from app.v_schemas import *
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/v2/admin/volunteer", tags=["Volunteer Admin"])


def verify_admin(current_admin: models.Admin = Depends(oauth2.get_current_admin)):
    """Проверка прав админа"""
    return current_admin


# === УПРАВЛЕНИЕ МЕРОПРИЯТИЯМИ ===

@router.post("/events")
def create_event(
        event: EventCreate,
        db: Session = Depends(get_db),
):
    """Создание мероприятия"""
    new_event = VolunteerEvent(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return {"message": "Мероприятие создано", "event_id": new_event.id}


@router.put("/events/{event_id}")
def update_event(
        event_id: int,
        event_data: EventCreate,
        db: Session = Depends(get_db),
):
    """Обновление мероприятия"""
    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    for key, value in event_data.dict(exclude_unset=True).items():
        setattr(event, key, value)

    event.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Мероприятие обновлено"}


@router.delete("/events/{event_id}")
def delete_event(
        event_id: int,
        db: Session = Depends(get_db),
):
    """Удаление мероприятия"""
    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Не найдено")

    event.is_active = False
    db.commit()
    return {"message": "Мероприятие деактивировано"}


# === УПРАВЛЕНИЕ ЗАЯВКАМИ ===

@router.get("/events/{event_id}/applications")
def get_event_applications(
        event_id: int,
        status_filter: Optional[str] = None,
        db: Session = Depends(get_db),
):
    """Все заявки на мероприятие"""
    query = db.query(EventApplication).filter(EventApplication.event_id == event_id)

    if status_filter:
        query = query.filter(EventApplication.status == status_filter)

    applications = query.all()

    result = []
    for app in applications:
        volunteer = db.query(Volunteer).filter(Volunteer.id == app.volunteer_id).first()
        result.append({
            "application_id": app.id,
            "volunteer": {
                "id": volunteer.id,
                "name": volunteer.full_name,
                "status": volunteer.volunteer_status
            },
            "applied_role": app.applied_role,
            "status": app.status,
            "attended": app.attended,
            "report_submitted": app.report_submitted,
            "created_at": app.created_at
        })

    return {"applications": result}


@router.post("/applications/{application_id}/approve")
def approve_application(
        application_id: int,
        db: Session = Depends(get_db),
):
    """Одобрить заявку"""
    app = db.query(EventApplication).filter(EventApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Не найдено")

    app.status = "approved"
    db.commit()
    return {"message": "Заявка одобрена"}


@router.post("/applications/{application_id}/reject")
def reject_application(
        application_id: int,
        reason: str = None,  # Добавь параметр для причины
        db: Session = Depends(get_db),
):
    """Отклонить заявку"""
    app = db.query(EventApplication).filter(EventApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Не найдено")

    app.status = "rejected"
    if reason:
        app.rejection_reason = reason  # Если есть поле в модели
    db.commit()
    return {"message": "Заявка отклонена"}



@router.patch("/applications/{application_id}/attendance")
def mark_attendance(
        application_id: int,
        attended: bool,
        db: Session = Depends(get_db),
):
    """Отметить присутствие/отсутствие"""
    app = db.query(EventApplication).filter(EventApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Не найдено")

    app.attended = attended
    app.missed = not attended

    volunteer = db.query(Volunteer).filter(Volunteer.id == app.volunteer_id).first()
    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if not balance:
        balance = VolunteerBalance(volunteer_id=volunteer.id)
        db.add(balance)

    if attended:
        # Начисляем V-coins
        event = db.query(VolunteerEvent).filter(VolunteerEvent.id == app.event_id).first()
        app.v_coins_earned = event.v_coins_reward

        balance.events_participated += 1
        balance.current_balance += event.v_coins_reward
        balance.total_earned += event.v_coins_reward

        # Транзакция
        transaction = VCoinTransaction(
            volunteer_id=volunteer.id,
            amount=event.v_coins_reward,
            transaction_type="earned",
            description=f"Участие в мероприятии: {event.title}",
            event_id=event.id
        )
        db.add(transaction)

        # Сбрасываем warning_level если посетил
        if balance.warning_level != "green":
            balance.events_missed = 0
            balance.warning_level = "green"
    else:
        # Пропуск - увеличиваем счетчик
        balance.events_missed += 1

        # Обновляем warning_level
        if balance.events_missed == 1:
            balance.warning_level = "yellow"
        elif balance.events_missed == 2:
            balance.warning_level = "orange"
        elif balance.events_missed >= 3:
            balance.warning_level = "red"

    db.commit()

    return {
        "message": "Присутствие отмечено",
        "attended": attended,
        "warning_level": balance.warning_level
    }


# === УПРАВЛЕНИЕ ЗАДАЧАМИ ===
@router.post("/events/{event_id}/tasks")
def create_event_task(
        event_id: int,
        task: TaskCreate,  # ← ИСПРАВЛЕНО: принимаем объект
        db: Session = Depends(get_db),
):
    """Создать задачу для мероприятия"""

    # Проверяем что мероприятие существует
    event = db.query(VolunteerEvent).filter(VolunteerEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    new_task = EventTask(
        event_id=event_id,
        title=task.title,
        description=task.description,
        for_role=task.for_role,
        is_required=task.is_required,
        v_coins_bonus=task.v_coins_bonus
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "message": "Задача создана",
        "task_id": new_task.id,
        "task": {
            "id": new_task.id,
            "title": new_task.title,
            "description": new_task.description,
            "for_role": new_task.for_role,
            "is_required": new_task.is_required,
            "v_coins_bonus": new_task.v_coins_bonus
        }
    }

# === УПРАВЛЕНИЕ ПЛЮШКАМИ ===
from pydantic import BaseModel
from typing import Optional


# Добавь схему в начало файла или в v_schemas.py
class BenefitCreate(BaseModel):
    title: str
    title_kz: Optional[str] = None
    description: str
    description_kz: Optional[str] = None
    v_coins_cost: int
    min_status: str = "VOLUNTEER"
    category: Optional[str] = None
    stock_limit: Optional[int] = None
    icon_url: Optional[str] = None


@router.post("/benefits")
def create_benefit(
        benefit: BenefitCreate,  # ← ИСПРАВЛЕНО: из body
        db: Session = Depends(get_db),
):
    """Создать плюшку"""
    new_benefit = Benefit(
        title=benefit.title,
        title_kz=benefit.title_kz,
        description=benefit.description,
        description_kz=benefit.description_kz,
        v_coins_cost=benefit.v_coins_cost,
        min_status=benefit.min_status,
        category=benefit.category,
        stock_limit=benefit.stock_limit,
        stock_available=benefit.stock_limit if benefit.stock_limit else None,
        icon_url=benefit.icon_url
    )
    db.add(new_benefit)
    db.commit()
    db.refresh(new_benefit)

    return {
        "message": "Плюшка создана",
        "benefit_id": new_benefit.id,
        "benefit": {
            "id": new_benefit.id,
            "title": new_benefit.title,
            "v_coins_cost": new_benefit.v_coins_cost,
            "category": new_benefit.category,
            "min_status": new_benefit.min_status
        }
    }


@router.get("/benefits")
def get_all_benefits(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
):
    """Получить все плюшки (для админа)"""
    benefits = db.query(Benefit).order_by(desc(Benefit.created_at)).offset(skip).limit(limit).all()

    return {
        "benefits": [
            {
                "id": benefit.id,
                "title": benefit.title,
                "title_kz": benefit.title_kz,
                "description": benefit.description,
                "description_kz": benefit.description_kz,
                "v_coins_cost": benefit.v_coins_cost,
                "min_status": benefit.min_status,
                "category": benefit.category,
                "stock_limit": benefit.stock_limit,
                "stock_available": benefit.stock_available,
                "icon_url": benefit.icon_url,
                "is_active": benefit.is_active,
                "created_at": benefit.created_at
            }
            for benefit in benefits
        ],
        "total": len(benefits)
    }


@router.put("/benefits/{benefit_id}")
def update_benefit(
        benefit_id: int,
        benefit_data: BenefitCreate,  # ← Используем ту же схему
        db: Session = Depends(get_db),
):
    """Обновить плюшку"""
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id).first()
    if not benefit:
        raise HTTPException(status_code=404, detail="Плюшка не найдена")

    # Обновляем поля
    benefit.title = benefit_data.title
    benefit.title_kz = benefit_data.title_kz
    benefit.description = benefit_data.description
    benefit.description_kz = benefit_data.description_kz
    benefit.v_coins_cost = benefit_data.v_coins_cost
    benefit.min_status = benefit_data.min_status
    benefit.category = benefit_data.category
    benefit.stock_limit = benefit_data.stock_limit
    benefit.icon_url = benefit_data.icon_url

    # Обновляем stock_available только если stock_limit изменился
    if benefit_data.stock_limit:
        benefit.stock_available = benefit_data.stock_limit

    benefit.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(benefit)

    return {
        "message": "Плюшка обновлена",
        "benefit": {
            "id": benefit.id,
            "title": benefit.title,
            "v_coins_cost": benefit.v_coins_cost,
            "category": benefit.category,
            "min_status": benefit.min_status
        }
    }


@router.delete("/benefits/{benefit_id}")
def delete_benefit(
        benefit_id: int,
        db: Session = Depends(get_db),
):
    """Удалить (деактивировать) плюшку"""
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id).first()
    if not benefit:
        raise HTTPException(status_code=404, detail="Плюшка не найдена")

    # Деактивируем вместо удаления
    benefit.is_active = False
    benefit.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Плюшка удалена",
        "benefit_id": benefit_id
    }
@router.get("/purchases")
def get_all_purchases(
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        db: Session = Depends(get_db),
):
    """Все покупки плюшек"""
    query = db.query(BenefitPurchase)

    if status_filter:
        query = query.filter(BenefitPurchase.status == status_filter)

    purchases = query.order_by(desc(BenefitPurchase.created_at)).offset(skip).limit(limit).all()

    result = []
    for purchase in purchases:
        volunteer = db.query(Volunteer).filter(Volunteer.id == purchase.volunteer_id).first()
        user = db.query(models.User).filter(models.User.id == volunteer.user_id).first() if volunteer else None
        benefit = db.query(Benefit).filter(Benefit.id == purchase.benefit_id).first()

        result.append({
            "id": purchase.id,
            "volunteer_name": volunteer.full_name if volunteer else "Неизвестно",  # ← ИСПРАВЛЕНО
            "volunteer_phone": user.phone_number if user else None,  # ← ИСПРАВЛЕНО
            "benefit_title": benefit.title if benefit else "Удалено",  # ← ИСПРАВЛЕНО
            "cost": purchase.v_coins_spent,  # ← ИСПРАВЛЕНО (было v_coins_spent)
            "status": purchase.status,
            "created_at": purchase.created_at,
            "completed_at": purchase.completed_at,
            "admin_notes": getattr(purchase, 'admin_notes', None),
            "cancellation_reason": getattr(purchase, 'cancellation_reason', None)  # ← ДОБАВЛЕНО
        })

    return {"purchases": result}


@router.patch("/purchases/{purchase_id}/complete")
def complete_purchase(
        purchase_id: int,
        admin_notes: str = None,
        db: Session = Depends(get_db),
):
    """Завершить покупку"""
    purchase = db.query(BenefitPurchase).filter(BenefitPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Не найдено")

    purchase.status = "completed"
    purchase.admin_notes = admin_notes
    purchase.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Покупка завершена"}


# === УПРАВЛЕНИЕ ПОВЫШЕНИЯМИ ===

@router.get("/promotion-requests")
def get_promotion_requests(
        status_filter: Optional[str] = None,
        db: Session = Depends(get_db),
        current_admin: models.Admin = Depends(verify_admin)
):
    """Все запросы на повышение"""
    query = db.query(PromotionRequest)

    if status_filter:
        query = query.filter(PromotionRequest.status == status_filter)

    requests = query.order_by(desc(PromotionRequest.created_at)).all()

    result = []
    for req in requests:
        volunteer = db.query(Volunteer).filter(Volunteer.id == req.volunteer_id).first()
        if not volunteer:
            continue

        balance = db.query(VolunteerBalance).filter(
            VolunteerBalance.volunteer_id == volunteer.id
        ).first()

        result.append({
            "request_id": req.id,
            "volunteer": {
                "id": volunteer.id,
                "name": volunteer.full_name,
                "current_status": volunteer.volunteer_status
            },
            "requested_status": req.requested_status,
            "v_coins_at_request": req.v_coins_at_request,
            "current_v_coins": balance.current_balance if balance else 0,
            "status": req.status,
            "created_at": req.created_at,
            "reviewed_at": req.reviewed_at,
            "admin_comment": req.admin_comment
        })

    return {"requests": result}


@router.post("/promotion-requests/{request_id}/approve")
def approve_promotion(
        request_id: int,
        request_data: dict,
        db: Session = Depends(get_db),
        current_admin: models.Admin = Depends(verify_admin)
):
    """Одобрить повышение"""
    req = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Не найдено")

    volunteer = db.query(Volunteer).filter(Volunteer.id == req.volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    # Повышаем статус
    volunteer.volunteer_status = req.requested_status
    volunteer.updated_at = datetime.utcnow()

    req.status = "approved"
    req.admin_comment = request_data.get("admin_comment", "")
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = current_admin.id

    db.commit()

    return {
        "message": f"Волонтер повышен до {req.requested_status}",
        "new_status": volunteer.volunteer_status
    }


@router.post("/promotion-requests/{request_id}/reject")
def reject_promotion(
        request_id: int,
        request_data: dict,
        db: Session = Depends(get_db),
        current_admin: models.Admin = Depends(verify_admin)
):
    """Отклонить повышение"""
    req = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Не найдено")

    admin_comment = request_data.get("admin_comment", "")
    if not admin_comment:
        raise HTTPException(status_code=400, detail="Комментарий обязателен при отклонении")

    req.status = "rejected"
    req.admin_comment = admin_comment
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = current_admin.id

    db.commit()

    return {"message": "Запрос отклонен"}


# === СТАТИСТИКА ===

@router.get("/stats/overview")
def get_volunteer_stats(
        db: Session = Depends(get_db),
):
    """Общая статистика волонтеров"""
    total_volunteers = db.query(func.count(Volunteer.id)).scalar()

    total_events = db.query(func.count(VolunteerEvent.id)).filter(VolunteerEvent.is_active == True).scalar()

    total_applications = db.query(func.count(EventApplication.id)).scalar()

    total_v_coins = db.query(func.sum(VolunteerBalance.total_earned)).scalar() or 0

    # По статусам
    by_status = db.query(
        Volunteer.volunteer_status,
        func.count(Volunteer.id)
    ).group_by(Volunteer.volunteer_status).all()

    return {
        "total_volunteers": total_volunteers,
        "total_events": total_events,
        "total_applications": total_applications,
        "total_v_coins_earned": total_v_coins,
        "volunteers_by_status": {status: count for status, count in by_status}
    }







# В volunteer_admin_routes.py замените эндпоинт /volunteers на этот:

@router.get("/volunteers")
def get_all_volunteers(
        status_filter: Optional[str] = None,
        direction_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
):
    """Получить список всех волонтёров"""
    query = db.query(Volunteer)

    # Фильтры
    if status_filter:
        query = query.filter(Volunteer.volunteer_status == status_filter)

    if direction_id:
        query = query.filter(Volunteer.direction_id == direction_id)

    volunteers = query.order_by(desc(Volunteer.created_at)).offset(skip).limit(limit).all()

    result = []
    for volunteer in volunteers:
        # Получаем баланс
        balance = db.query(VolunteerBalance).filter(
            VolunteerBalance.volunteer_id == volunteer.id
        ).first()

        # Получаем пользователя
        user = db.query(models.User).filter(models.User.id == volunteer.user_id).first()

        # Статистика достижений
        achievements_count = db.query(func.count(VolunteerAchievement.id)).filter(
            VolunteerAchievement.volunteer_id == volunteer.id
        ).scalar()

        result.append({
            "id": volunteer.id,
            "user_id": volunteer.user_id,
            "full_name": volunteer.full_name,
            "phone_number": user.phone_number if user else None,
            "volunteer_status": volunteer.volunteer_status,
            "v_coins_balance": balance.current_balance if balance else 0,
            "direction_id": volunteer.direction_id,
            "created_at": volunteer.created_at,
            "events_participated": balance.events_participated if balance else 0,
            "total_earned": balance.total_earned if balance else 0,
            "achievements_count": achievements_count or 0
        })

    return {
        "volunteers": result,
        "total": len(result)
    }


@router.get("/applications")
def get_all_applications(
        status: Optional[str] = None,
        event_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
):
    """Получить все заявки с фильтрами"""
    query = db.query(EventApplication)

    if status:
        query = query.filter(EventApplication.status == status)

    if event_id:
        query = query.filter(EventApplication.event_id == event_id)

    applications = query.order_by(desc(EventApplication.created_at)).offset(skip).limit(limit).all()

    result = []
    for app in applications:
        volunteer = db.query(Volunteer).filter(Volunteer.id == app.volunteer_id).first()
        user = db.query(models.User).filter(models.User.id == volunteer.user_id).first()
        event = db.query(VolunteerEvent).filter(VolunteerEvent.id == app.event_id).first()

        result.append({
            "id": app.id,
            "volunteer_name": volunteer.full_name,
            "volunteer_phone": user.phone_number if user else None,
            "event_title": event.title if event else "Удалено",
            "role": app.applied_role,
            "status": app.status,
            "attended": app.attended,
            "missed": app.missed,
            "created_at": app.created_at,
            "rejection_reason": getattr(app, 'rejection_reason', None)
        })

    return {"applications": result, "total": len(result)}


@router.put("/volunteers/{volunteer_id}")
def update_volunteer(
        volunteer_id: int,
        full_name: Optional[str] = None,
        volunteer_status: Optional[str] = None,
        v_coins_balance: Optional[int] = None,
        db: Session = Depends(get_db),
):
    """Обновить данные волонтёра"""
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтёр не найден")

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer_id
    ).first()

    if full_name:
        volunteer.full_name = full_name

    if volunteer_status:
        if volunteer_status not in ["VOLUNTEER", "TEAM_LEADER", "SUPERVISOR", "COORDINATOR"]:
            raise HTTPException(status_code=400, detail="Неверный статус")
        volunteer.volunteer_status = volunteer_status

    if v_coins_balance is not None and balance:
        balance.current_balance = v_coins_balance

    volunteer.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Волонтёр успешно обновлён",
        "volunteer": {
            "id": volunteer.id,
            "full_name": volunteer.full_name,
            "volunteer_status": volunteer.volunteer_status,
            "v_coins_balance": balance.current_balance if balance else 0
        }
    }


@router.post("/volunteers/{volunteer_id}/coins")
def manage_volunteer_coins(
        volunteer_id: int,
        amount: int,
        reason: str,
        type: str,  # 'add' или 'deduct'
        db: Session = Depends(get_db),
):
    """Начислить или списать V-coins волонтёру"""
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтёр не найден")

    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer_id
    ).first()

    if not balance:
        balance = VolunteerBalance(volunteer_id=volunteer_id)
        db.add(balance)
        db.flush()

    if type == "add":
        balance.current_balance += amount
        balance.total_earned += amount
        transaction_amount = amount
    elif type == "deduct":
        if balance.current_balance < amount:
            raise HTTPException(status_code=400, detail="Недостаточно V-coins")
        balance.current_balance -= amount
        transaction_amount = -amount
    else:
        raise HTTPException(status_code=400, detail="Неверный тип операции")

    # Создаём транзакцию
    transaction = VCoinTransaction(
        volunteer_id=volunteer_id,
        amount=transaction_amount,
        transaction_type="admin_adjustment",
        description=f"Админ: {reason}"
    )
    db.add(transaction)
    db.commit()

    return {
        "message": f"V-coins успешно {'начислены' if type == 'add' else 'списаны'}",
        "new_balance": balance.current_balance
    }


# === УПРАВЛЕНИЕ ОТЧЕТАМИ ПО ЗАДАЧАМ ===

@router.get("/task-reports")
def get_all_task_reports(
        status_filter: Optional[str] = None,  # pending, approved, rejected
        event_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
):
    """Все отчёты по задачам"""
    query = db.query(TaskCompletion).filter(
        TaskCompletion.report_status != "not_submitted"
    )

    if status_filter:
        query = query.filter(TaskCompletion.report_status == status_filter)

    completions = query.order_by(desc(TaskCompletion.created_at)).offset(skip).limit(limit).all()

    result = []
    for completion in completions:
        # Получаем связанные данные
        task = db.query(EventTask).filter(EventTask.id == completion.task_id).first()
        application = db.query(EventApplication).filter(EventApplication.id == completion.application_id).first()

        if not task or not application:
            continue

        volunteer = db.query(Volunteer).filter(Volunteer.id == application.volunteer_id).first()
        user = db.query(models.User).filter(models.User.id == volunteer.user_id).first()
        event = db.query(VolunteerEvent).filter(VolunteerEvent.id == application.event_id).first()

        # Фильтр по event_id
        if event_id and event.id != event_id:
            continue

        result.append({
            "id": completion.id,
            "volunteer_name": volunteer.full_name,
            "volunteer_phone": user.phone_number if user else None,
            "event_title": event.title if event else "Удалено",
            "task_title": task.title,
            "task_v_coins": task.v_coins_bonus,
            "report_text": completion.report_text,
            "report_photo_url": completion.report_photo_url,
            "report_status": completion.report_status,
            "admin_comment": completion.admin_comment,
            "v_coins_earned": completion.v_coins_earned,
            "created_at": completion.created_at
        })

    return {"reports": result, "total": len(result)}


class ApproveReportRequest(BaseModel):
    admin_comment: Optional[str] = None


@router.post("/task-reports/{completion_id}/approve")
def approve_task_report(
        completion_id: int,
        request: ApproveReportRequest,  # ← ИСПРАВЛЕНО: из body
        db: Session = Depends(get_db),
):
    """Одобрить отчёт по задаче"""
    completion = db.query(TaskCompletion).filter(TaskCompletion.id == completion_id).first()
    if not completion:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    if completion.report_status and completion.report_status != "pending":
        raise HTTPException(status_code=400, detail="Отчёт уже обработан")

    # Получаем задачу для V-coins
    task = db.query(EventTask).filter(EventTask.id == completion.task_id).first()
    application = db.query(EventApplication).filter(EventApplication.id == completion.application_id).first()
    volunteer = db.query(Volunteer).filter(Volunteer.id == application.volunteer_id).first()

    # Одобряем отчёт
    completion.report_status = "approved"
    completion.admin_comment = request.admin_comment  # ← ИСПРАВЛЕНО
    completion.v_coins_earned = task.v_coins_bonus

    # Начисляем V-coins волонтёру
    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if balance:
        balance.current_balance += task.v_coins_bonus
        balance.total_earned += task.v_coins_bonus

    # Создаём транзакцию
    transaction = VCoinTransaction(
        volunteer_id=volunteer.id,
        amount=task.v_coins_bonus,
        transaction_type="earned",
        description=f"Выполнение задачи: {task.title}",
        event_id=application.event_id
    )
    db.add(transaction)

    db.commit()

    return {
        "message": "Отчёт одобрен",
        "v_coins_earned": task.v_coins_bonus
    }


# Добавь схему в начало файла (или в v_schemas.py)
class RejectReportRequest(BaseModel):
    admin_comment: str


@router.post("/task-reports/{completion_id}/reject")
def reject_task_report(
        completion_id: int,
        request: RejectReportRequest,  # ← ИСПРАВЛЕНО: из body
        db: Session = Depends(get_db),
):
    """Отклонить отчёт по задаче"""
    completion = db.query(TaskCompletion).filter(TaskCompletion.id == completion_id).first()
    if not completion:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    if completion.report_status and completion.report_status != "pending":
        raise HTTPException(status_code=400, detail="Отчёт уже обработан")

    # Отклоняем отчёт
    completion.report_status = "rejected"
    completion.admin_comment = request.admin_comment  # ← ИСПРАВЛЕНО
    completion.v_coins_earned = 0
    completion.completed = False  # Снимаем отметку о выполнении

    db.commit()

    return {
        "message": "Отчёт отклонён",
        "admin_comment": request.admin_comment
    }


@router.post("/purchases/{purchase_id}/approve")
def approve_purchase(
        purchase_id: int,
        db: Session = Depends(get_db),
):
    """Одобрить покупку"""
    purchase = db.query(BenefitPurchase).filter(BenefitPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Покупка не найдена")

    if purchase.status != "pending":
        raise HTTPException(status_code=400, detail="Покупка уже обработана")

    purchase.status = "approved"
    db.commit()

    return {"message": "Покупка одобрена"}


@router.post("/purchases/{purchase_id}/complete")
def complete_purchase(
        purchase_id: int,
        admin_notes: Optional[str] = None,
        db: Session = Depends(get_db),
):
    """Завершить покупку (плюшка выдана)"""
    purchase = db.query(BenefitPurchase).filter(BenefitPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Покупка не найдена")

    if purchase.status != "approved":
        raise HTTPException(status_code=400, detail="Покупка должна быть сначала одобрена")

    purchase.status = "completed"
    purchase.completed_at = datetime.utcnow()
    if admin_notes and hasattr(purchase, 'admin_notes'):
        purchase.admin_notes = admin_notes

    db.commit()

    return {"message": "Покупка завершена"}


class CancelPurchaseRequest(BaseModel):
    reason: str


@router.post("/purchases/{purchase_id}/cancel")
def cancel_purchase(
        purchase_id: int,
        request: CancelPurchaseRequest,
        db: Session = Depends(get_db),
):
    """Отменить покупку и вернуть V-coins"""
    purchase = db.query(BenefitPurchase).filter(BenefitPurchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Покупка не найдена")

    if purchase.status == "completed":
        raise HTTPException(status_code=400, detail="Нельзя отменить завершённую покупку")

    # Возвращаем V-coins волонтёру
    volunteer = db.query(Volunteer).filter(Volunteer.id == purchase.volunteer_id).first()
    balance = db.query(VolunteerBalance).filter(
        VolunteerBalance.volunteer_id == volunteer.id
    ).first()

    if balance:
        balance.current_balance += purchase.v_coins_spent
        balance.total_spent -= purchase.v_coins_spent

    # Создаём транзакцию возврата
    transaction = VCoinTransaction(
        volunteer_id=volunteer.id,
        amount=purchase.v_coins_spent,
        transaction_type="refund",
        description=f"Возврат за отменённую покупку: {request.reason}",
        benefit_id=purchase.benefit_id
    )
    db.add(transaction)

    # Обновляем покупку
    purchase.status = "cancelled"
    if hasattr(purchase, 'cancellation_reason'):
        purchase.cancellation_reason = request.reason

    # Возвращаем сток плюшки
    benefit = db.query(Benefit).filter(Benefit.id == purchase.benefit_id).first()
    if benefit and benefit.stock_limit:
        benefit.stock_available += 1

    db.commit()

    return {
        "message": "Покупка отменена, V-coins возвращены",
        "refunded_amount": purchase.v_coins_spent
    }


# === УПРАВЛЕНИЕ ТРЕБОВАНИЯМИ СТАТУСОВ ===

@router.get("/status-requirements")
def get_status_requirements(
        db: Session = Depends(get_db),
):
    """
    Получить все требования для статусов
    """
    requirements = db.query(StatusRequirement).order_by(StatusRequirement.level).all()

    if not requirements:
        # Если таблица пустая - создаём дефолтные значения
        default_statuses = [
            {
                "status": "VOLUNTEER",
                "title_ru": "Волонтер",
                "title_kz": "Волонтер",
                "level": 1,
                "v_coins_required": 0,  # Стартовый статус
                "benefits_ru": "Базовый статус",
                "benefits_kz": "Негізгі мәртебе"
            },
            {
                "status": "TEAM_LEADER",
                "title_ru": "Тимлидер",
                "title_kz": "Топ жетекшісі",
                "level": 2,
                "v_coins_required": 150,
                "benefits_ru": "Доступ к роли тимлидера, Управление командой, Больше бонусов",
                "benefits_kz": "Топ жетекшісі рөліне қол жеткізу, Команданы басқару, Көбірек бонустар"
            },
            {
                "status": "SUPERVISOR",
                "title_ru": "Супервайзер",
                "title_kz": "Супервайзер",
                "level": 3,
                "v_coins_required": 200,
                "benefits_ru": "Доступ к роли супервайзера, Контроль проектов, VIP плюшки",
                "benefits_kz": "Супервайзер рөліне қол жеткізу, Жобаларды бақылау, VIP артықшылықтар"
            },
            {
                "status": "COORDINATOR",
                "title_ru": "Координатор",
                "title_kz": "Үйлестіруші",
                "level": 4,
                "v_coins_required": 300,
                "benefits_ru": "Высший статус, Координация программ, Все привилегии",
                "benefits_kz": "Жоғары мәртебе, Бағдарламаларды үйлестіру, Барлық артықшылықтар"
            }
        ]

        for status_data in default_statuses:
            new_req = StatusRequirement(**status_data)
            db.add(new_req)

        db.commit()
        requirements = db.query(StatusRequirement).order_by(StatusRequirement.level).all()

    return {
        "status_requirements": [
            {
                "id": req.id,
                "status": req.status,
                "title_ru": req.title_ru,
                "title_kz": req.title_kz,
                "level": req.level,
                "v_coins_required": req.v_coins_required,
                "benefits_ru": req.benefits_ru,
                "benefits_kz": req.benefits_kz
            }
            for req in requirements
        ]
    }


@router.put("/status-requirements/{status}")
def update_status_requirement(
        status: str,  # VOLUNTEER, TEAM_LEADER, SUPERVISOR, COORDINATOR
        data: StatusRequirementUpdate,
        db: Session = Depends(get_db),
):
    """
    Обновить требования для статуса

    Пример:
    PUT /api/v2/admin/volunteer/status-requirements/TEAM_LEADER
    {
        "v_coins_required": 200,
        "benefits_ru": "Новые преимущества",
        "benefits_kz": "Жаңа артықшылықтар"
    }
    """
    requirement = db.query(StatusRequirement).filter(
        StatusRequirement.status == status
    ).first()

    if not requirement:
        raise HTTPException(status_code=404, detail="Статус не найден")

    # Обновляем только переданные поля
    if data.v_coins_required is not None:
        requirement.v_coins_required = data.v_coins_required

    if data.benefits_ru is not None:
        requirement.benefits_ru = data.benefits_ru

    if data.benefits_kz is not None:
        requirement.benefits_kz = data.benefits_kz

    requirement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(requirement)

    return {
        "message": f"Требования для статуса {status} обновлены",
        "requirement": {
            "status": requirement.status,
            "title_ru": requirement.title_ru,
            "level": requirement.level,
            "v_coins_required": requirement.v_coins_required,
            "benefits_ru": requirement.benefits_ru,
            "benefits_kz": requirement.benefits_kz
        }
    }


@router.post("/status-requirements/reset-defaults")
def reset_status_requirements(
        db: Session = Depends(get_db),
):
    """
    Сбросить требования к дефолтным значениям
    """
    # Удаляем все существующие
    db.query(StatusRequirement).delete()

    # Создаём дефолтные
    default_statuses = [
        {
            "status": "VOLUNTEER",
            "title_ru": "Волонтер",
            "title_kz": "Волонтер",
            "level": 1,
            "v_coins_required": 0,
            "benefits_ru": "Базовый статус",
            "benefits_kz": "Негізгі мәртебе"
        },
        {
            "status": "TEAM_LEADER",
            "title_ru": "Тимлидер",
            "title_kz": "Топ жетекшісі",
            "level": 2,
            "v_coins_required": 150,
            "benefits_ru": "Доступ к роли тимлидера, Управление командой, Больше бонусов",
            "benefits_kz": "Топ жетекшісі рөліне қол жеткізу, Команданы басқару, Көбірек бонустар"
        },
        {
            "status": "SUPERVISOR",
            "title_ru": "Супервайзер",
            "title_kz": "Супервайзер",
            "level": 3,
            "v_coins_required": 200,
            "benefits_ru": "Доступ к роли супервайзера, Контроль проектов, VIP плюшки",
            "benefits_kz": "Супервайзер рөліне қол жеткізу, Жобаларды бақылау, VIP артықшылықтар"
        },
        {
            "status": "COORDINATOR",
            "title_ru": "Координатор",
            "title_kz": "Үйлестіруші",
            "level": 4,
            "v_coins_required": 300,
            "benefits_ru": "Высший статус, Координация программ, Все привилегии",
            "benefits_kz": "Жоғары мәртебе, Бағдарламаларды үйлестіру, Барлық артықшылықтар"
        }
    ]

    for status_data in default_statuses:
        new_req = StatusRequirement(**status_data)
        db.add(new_req)

    db.commit()

    return {"message": "Требования сброшены к дефолтным значениям"}