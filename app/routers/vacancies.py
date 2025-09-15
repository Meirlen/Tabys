from fastapi import APIRouter, Depends, status, Query, Response, BackgroundTasks, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import (
    VacancyList,
    VacancyDetail,
    VacancyCreate,
    VacancyUpdate,
    VacancyFilter,
    VacancyApplicationCreate,
)
from app import crud
from app.utils import send_email, validate_file_extension
from app.oauth2 import get_current_user

from app import models, schemas,resume_models

from datetime import datetime

router = APIRouter(prefix="/api/v2/vacancies", tags=["Vacancies"])


@router.get("/")
def list_vacancies(
        skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
        limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
        keyword: Optional[str] = Query(None, description="Ключевое слово для поиска"),
        lang: Optional[str] = Query("ru", regex="^(kz|ru)$", description="Язык поиска (kz/ru)"),
        employment_type: Optional[str] = Query(None, description="Тип занятости"),
        work_type: Optional[str] = Query(None, description="Тип работы"),
        min_salary: Optional[int] = Query(None, ge=0, description="Минимальная зарплата"),
        max_salary: Optional[int] = Query(None, ge=0, description="Максимальная зарплата"),
        location: Optional[str] = Query(None, description="Местоположение"),
        db: Session = Depends(get_db)
):
    """
    Получение списка вакансий с фильтрацией

    Параметры фильтрации:
    - keyword: поиск по названию (приоритет по выбранному языку)
    - lang: язык поиска (kz/ru) - определяет приоритет поиска
    - employment_type: тип занятости
    - work_type: тип работы
    - min_salary/max_salary: диапазон зарплаты
    - location: местоположение
    """
    vacancies = crud.get_vacancies_filtered(
        db=db,
        skip=skip,
        limit=limit,
        keyword=keyword,
        lang=lang,
        employment_type=employment_type,
        work_type=work_type,
        min_salary=min_salary,
        max_salary=max_salary,
        location=location
    )

    print(vacancies)
    return vacancies


@router.get("/search", response_model=List[VacancyList])
def search_vacancies(
        employment_type: Optional[str] = None,
        work_type: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Поиск и фильтрация вакансий по различным параметрам
    """
    vacancies = crud.filter_vacancies(
        db,
        employment_type=employment_type,
        work_type=work_type,
        city=city,
        search=search,
        skip=skip,
        limit=limit
    )
    return vacancies


@router.get("/{vacancy_id}", response_model=VacancyDetail)
def get_vacancy_details(vacancy_id: int, db: Session = Depends(get_db)):
    """
    Получение детальной информации о вакансии
    """
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    return vacancy


@router.post("/", response_model=VacancyDetail, status_code=status.HTTP_201_CREATED)
def create_vacancy(
        vacancy: VacancyCreate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Создание новой вакансии (только для авторизованных администраторов)
    """
    # # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Валидация казахского и русского описаний
    if vacancy.description_kz and len(vacancy.description_kz) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Описание вакансии на казахском не должно превышать 1000 символов"
        )

    if vacancy.description_ru and len(vacancy.description_ru) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Описание вакансии на русском не должно превышать 1000 символов"
        )

    return crud.create_vacancy(db=db, vacancy=vacancy)

@router.put("/{vacancy_id}", response_model=VacancyDetail)
def update_vacancy(
        vacancy_id: int,
        vacancy: VacancyUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление существующей вакансии (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Проверяем существование вакансии
    existing_vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not existing_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    if vacancy.description and len(vacancy.description) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Описание вакансии не должно превышать 1000 символов"
        )

    return crud.update_vacancy(db=db, vacancy_id=vacancy_id, vacancy_update=vacancy)


@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vacancy(
        vacancy_id: int,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Удаление вакансии (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Проверяем существование вакансии
    existing_vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not existing_vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    crud.delete_vacancy(db=db, vacancy_id=vacancy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
# Исправленный код для функции apply_for_vacancy




# Исправленный код для функции apply_for_vacancy без параметра attachments

@router.post("/{vacancy_id}/apply",  status_code=status.HTTP_201_CREATED)
def apply_for_vacancy(
        vacancy_id: int,
        application: VacancyApplicationCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Подача отклика на вакансию с выбором резюме
    """
    # Проверка существования вакансии
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    # Проверка, что пользователь не подавал отклик на эту вакансию ранее
    existing_application = crud.check_existing_application(
        db, user_id=current_user.id, vacancy_id=vacancy_id
    )
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже подавали отклик на эту вакансию"
        )

    # Проверка принадлежности резюме пользователю
    resume = crud.get_resume(db, resume_id=application.resume_id, user_id=current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено или не принадлежит вам"
        )

    # Проверка, что резюме опубликовано
    if not resume.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно использовать только опубликованные резюме"
        )

    # Создание отклика
    application.vacancy_id = vacancy_id
    new_application = crud.create_vacancy_application(
        db=db,
        user_id=current_user.id,
        application=application
    )

    # Получение информации для уведомления
    vacancy_title = vacancy.title_ru or vacancy.title_kz or "Вакансия"

    # Отправка уведомления работодателю
    if vacancy.contact_email:
        background_tasks.add_task(
            send_email,
            recipient_email=vacancy.contact_email,
            subject=f"Новый отклик на вакансию '{vacancy_title}'",
            message=f"""
            Здравствуйте!

            Получен новый отклик на вакансию "{vacancy_title}".

            Данные кандидата:
            - Имя: {resume.full_name}
            - Профессия: {resume.profession_id}  # Здесь можно добавить название профессии

            {f"Сопроводительное письмо: {application.cover_letter}" if application.cover_letter else ""}

            Вы можете просмотреть подробную информацию о кандидате в административной панели.

            С уважением,
            Система управления вакансиями
            """
        )

    return new_application


# Add these routes to the existing router in vacancy API
@router.get("/my-applications")
def get_my_applications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Получение списка моих откликов на вакансии
    """
    applications = crud.get_user_applications(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return applications



@router.get("/{vacancy_id}/applications")
def get_vacancy_applications(
        vacancy_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Получение списка откликов на вакансию (только для администраторов)
    """
    # Проверка прав доступа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Проверка существования вакансии
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    applications = crud.get_vacancy_applications(db, vacancy_id=vacancy_id)
    return applications


@router.get("/{vacancy_id}/applications/{application_id}/resume")
def download_vacancy_application_resume(
        vacancy_id: int,
        application_id: int,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Скачивание резюме кандидата (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Получаем отклик на вакансию
    application = crud.get_vacancy_application(db, application_id=application_id, vacancy_id=vacancy_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отклик не найден"
        )

    # Возвращаем файл резюме
    return Response(
        content=application.resume_content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={application.resume_filename}"
        }
    )


@router.patch("/{vacancy_id}/applications/{application_id}")
def update_application_status(
        vacancy_id: int,
        application_id: int,
        status_update: schemas.VacancyApplicationUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    """
    Обновление статуса отклика (только для администраторов)
    """
    # Проверка прав доступа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Проверка существования отклика
    application = crud.get_vacancy_application(
        db, application_id=application_id, vacancy_id=vacancy_id
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отклик не найден"
        )

    # Валидация статуса
    allowed_statuses = ["new", "reviewed", "accepted", "rejected"]
    if status_update.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый статус. Разрешены: {', '.join(allowed_statuses)}"
        )

    # Обновление статуса
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
    """
    Удаление своего отклика на вакансию
    """
    success = crud.delete_vacancy_application(
        db, application_id=application_id, user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отклик не найден или не принадлежит вам"
        )



from sqlalchemy import func
from typing import Optional, List
