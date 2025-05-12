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
    VacancyApplication
)
from app import crud
from app.utils import send_email, validate_file_extension
from app.oauth2 import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/v2/vacancies", tags=["Vacancies"])


@router.get("/", response_model=List[VacancyList])
def list_vacancies(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    Получение списка всех вакансий
    """
    vacancies = crud.get_vacancies(db, skip=skip, limit=limit)
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
        current_user=Depends(get_current_user)
):
    """
    Удаление вакансии (только для авторизованных администраторов)
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

    crud.delete_vacancy(db=db, vacancy_id=vacancy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
# Исправленный код для функции apply_for_vacancy




# Исправленный код для функции apply_for_vacancy без параметра attachments

@router.post("/{vacancy_id}/apply", response_model=VacancyApplication, status_code=status.HTTP_201_CREATED)
async def apply_for_vacancy(
        vacancy_id: int,
        background_tasks: BackgroundTasks,
        last_name: str = Form(...),
        first_name: str = Form(...),
        email: str = Form(...),
        phone: Optional[str] = Form(None),
        cover_letter: Optional[str] = Form(None),
        resume: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    Отправка отклика на вакансию
    """
    # Проверка существования вакансии
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    # Проверка формата файла (разрешены только word и pdf)
    allowed_extensions = ['doc', 'docx', 'pdf']
    if not validate_file_extension(resume.filename, allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Разрешены только файлы в формате Word (doc, docx) и PDF"
        )

    # Чтение содержимого файла
    resume_content = await resume.read()

    # Создание данных для отклика
    application_data = VacancyApplicationCreate(
        vacancy_id=vacancy_id,
        last_name=last_name,
        first_name=first_name,
        email=email,
        phone=phone,
        cover_letter=cover_letter,
        resume_filename=resume.filename
    )

    # Создание отклика в базе данных
    application = crud.create_vacancy_application(
        db=db,
        application=application_data,
        resume_content=resume_content
    )

    # Получаем заголовок вакансии с учетом мультиязычности
    vacancy_title = vacancy.title_ru or vacancy.title_kz or "Вакансия"

    # Отправка уведомления о новом отклике на указанную в вакансии почту
    # Убираем параметр attachments, так как он не поддерживается
    background_tasks.add_task(
        send_email,
        recipient_email=vacancy.contact_email,
        subject=f"Новый отклик на вакансию '{vacancy_title}'",
        message=f"""
        Здравствуйте!

        Получен новый отклик на вакансию "{vacancy_title}".

        Данные кандидата:
        - Имя: {first_name} {last_name}
        - Email: {email}
        - Телефон: {phone or "Не указан"}

        Сопроводительное письмо:
        {cover_letter or "Не указано"}

        Резюме кандидата сохранено в системе. Вы можете загрузить его из административной панели.

        С уважением,
        Система управления вакансиями
        """
    )

    return application


# Add these routes to the existing router in vacancy API

@router.get("/{vacancy_id}/applications", response_model=List[VacancyApplication])
def get_vacancy_applications(
        vacancy_id: int,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Получение списка откликов на вакансию (только для авторизованных администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Проверяем существование вакансии
    vacancy = crud.get_vacancy(db, vacancy_id=vacancy_id)
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )

    # Получаем список откликов
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


@router.patch("/{vacancy_id}/applications/{application_id}", response_model=VacancyApplication)
def update_vacancy_application_status(
        vacancy_id: int,
        application_id: int,
        status_update: dict,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Обновление статуса отклика на вакансию (только для авторизованных администраторов)
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

    # Обновляем статус отклика
    updated_application = crud.update_vacancy_application_status(
        db,
        application_id=application_id,
        status=status_update.get("status")
    )

    return updated_application