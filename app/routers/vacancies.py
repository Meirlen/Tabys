from fastapi import APIRouter, Depends, status, Query, Response, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import (
    VacancyList,
    VacancyDetail,
    VacancyCreate,
    VacancyUpdate,
    VacancyApplicationCreate,
    VacancyApplicationUpdate,
)
from app import crud
from app.utils import send_email
from app.oauth2 import get_current_user
from app import models, resume_models
from datetime import datetime

router = APIRouter(prefix="/api/v2/vacancies", tags=["Vacancies"])


@router.get("/")
def list_vacancies(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        keyword: Optional[str] = Query(None),
        lang: Optional[str] = Query("ru", regex="^(kz|ru)$"),
        profession_id: Optional[int] = Query(None),
        city_id: Optional[int] = Query(None),
        region_id: Optional[int] = Query(None),
        employment_type: Optional[str] = Query(None),
        work_type: Optional[str] = Query(None),
        min_salary: Optional[int] = Query(None, ge=0),
        max_salary: Optional[int] = Query(None, ge=0),
        db: Session = Depends(get_db)
):
    """Список вакансий с фильтрацией"""
    vacancies = crud.get_vacancies_filtered(
        db=db,
        skip=skip,
        limit=limit,
        keyword=keyword,
        lang=lang,
        profession_id=profession_id,
        city_id=city_id,
        region_id=region_id,
        employment_type=employment_type,
        work_type=work_type,
        min_salary=min_salary,
        max_salary=max_salary,
        is_active=True
    )
    return vacancies


@router.get("/search")
def search_vacancies(
        profession_id: Optional[int] = None,
        city_id: Optional[int] = None,
        region_id: Optional[int] = None,
        employment_type: Optional[str] = None,
        work_type: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """Поиск вакансий"""
    vacancies = crud.filter_vacancies(
        db,
        profession_id=profession_id,
        city_id=city_id,
        region_id=region_id,
        employment_type=employment_type,
        work_type=work_type,
        min_salary=min_salary,
        max_salary=max_salary,
        search=search,
        skip=skip,
        limit=limit
    )
    return vacancies


@router.get("/{vacancy_id}")
def get_vacancy_details(vacancy_id: int, db: Session = Depends(get_db)):
    """Детали вакансии"""
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    return vacancy


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_vacancy(
        vacancy: VacancyCreate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """Создание вакансии"""
    # Проверка профессии
    profession = db.query(resume_models.Profession).filter(
        resume_models.Profession.id == vacancy.profession_id,
        resume_models.Profession.is_active == True
    ).first()
    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профессия не найдена"
        )

    # Проверка города
    city = db.query(resume_models.City).filter(
        resume_models.City.id == vacancy.city_id,
        resume_models.City.is_active == True
    ).first()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Город не найден"
        )

    # Проверка навыков
    if vacancy.required_skills:
        for skill_id in vacancy.required_skills:
            skill = db.query(resume_models.Skill).filter(
                resume_models.Skill.id == skill_id,
                resume_models.Skill.is_active == True
            ).first()
            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Навык с ID {skill_id} не найден"
                )

    return crud.create_vacancy(db=db, vacancy=vacancy)


@router.put("/{vacancy_id}")
def update_vacancy(
        vacancy_id: int,
        vacancy: VacancyUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Обновление вакансии"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    existing_vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not existing_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    if vacancy.profession_id:
        profession = db.query(resume_models.Profession).filter(
            resume_models.Profession.id == vacancy.profession_id,
            resume_models.Profession.is_active == True
        ).first()
        if not profession:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профессия не найдена"
            )

    if vacancy.city_id:
        city = db.query(resume_models.City).filter(
            resume_models.City.id == vacancy.city_id,
            resume_models.City.is_active == True
        ).first()
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Город не найден"
            )

    if vacancy.required_skills:
        for skill_id in vacancy.required_skills:
            skill = db.query(resume_models.Skill).filter(
                resume_models.Skill.id == skill_id,
                resume_models.Skill.is_active == True
            ).first()
            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Навык с ID {skill_id} не найден"
                )

    return crud.update_vacancy(db=db, vacancy_id=vacancy_id, vacancy_update=vacancy)


@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vacancy(
        vacancy_id: int,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """Удаление вакансии"""
    existing_vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not existing_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    crud.delete_vacancy(db=db, vacancy_id=vacancy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{vacancy_id}/activate")
def activate_vacancy(
        vacancy_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Активация вакансии"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    vacancy.is_active = True
    vacancy.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Вакансия активирована", "vacancy_id": vacancy_id}


@router.post("/{vacancy_id}/deactivate")
def deactivate_vacancy(
        vacancy_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Деактивация вакансии"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    vacancy.is_active = False
    vacancy.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Вакансия деактивирована", "vacancy_id": vacancy_id}


# ========== ОТКЛИКИ ==========

@router.post("/{vacancy_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_for_vacancy(
        vacancy_id: int,
        application: VacancyApplicationCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Подать отклик"""
    vacancy_data = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    if not vacancy_data.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вакансия неактивна"
        )

    existing_application = crud.check_existing_application(
        db, user_id=current_user.id, vacancy_id=vacancy_id
    )
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже подавали отклик"
        )

    resume = crud.get_resume(db, resume_id=application.resume_id, user_id=current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    if not resume.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Резюме должно быть опубликовано"
        )

    application.vacancy_id = vacancy_id
    new_application = crud.create_vacancy_application(
        db=db,
        user_id=current_user.id,
        application=application
    )

    # Email
    contact_email = vacancy_data.get("contact_email")
    if contact_email:
        profession = vacancy_data.get("profession", {})
        vacancy_title = profession.get("name_ru", "Вакансия")
        background_tasks.add_task(
            send_email,
            recipient_email=contact_email,
            subject=f"Новый отклик на '{vacancy_title}'",
            message=f"Новый отклик от {resume.full_name}"
        )

    return new_application


@router.get("/my-applications")
def get_my_applications(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Мои отклики"""
    applications = crud.get_user_applications(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status_filter
    )
    return applications


@router.get("/{vacancy_id}/applications")
def get_vacancy_applications(
        vacancy_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Отклики на вакансию"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    applications = crud.get_vacancy_applications(
        db,
        vacancy_id=vacancy_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit
    )
    return applications


@router.patch("/{vacancy_id}/applications/{application_id}")
def update_application_status(
        vacancy_id: int,
        application_id: int,
        status_update: VacancyApplicationUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Обновить статус отклика"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    application = crud.get_vacancy_application(
        db, application_id=application_id, vacancy_id=vacancy_id
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отклик не найден"
        )

    allowed_statuses = ["new", "reviewed", "accepted", "rejected"]
    if status_update.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый статус"
        )

    updated_application = crud.update_vacancy_application_status(
        db, application_id=application_id, status=status_update.status
    )

    return updated_application


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_application(
        application_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Удалить отклик"""
    success = crud.delete_vacancy_application(
        db, application_id=application_id, user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отклик не найден"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ========== СТАТИСТИКА ==========

@router.get("/stats/summary")
def get_vacancies_summary(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """Общая статистика"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    return crud.get_vacancies_stats(db)


@router.get("/stats/by-profession")
def get_vacancies_by_profession(db: Session = Depends(get_db)):
    """Статистика по профессиям"""
    return crud.get_vacancies_by_profession(db)


@router.get("/stats/by-city")
def get_vacancies_by_city(db: Session = Depends(get_db)):
    """Статистика по городам"""
    return crud.get_vacancies_by_city(db)