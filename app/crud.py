from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from . import models, schemas,resume_models
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status
from uuid import uuid4


def get_experts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Expert).offset(skip).limit(limit).all()


def get_expert(db: Session, expert_id: int):
    expert = db.query(models.Expert).filter(models.Expert.id == expert_id).first()
    if expert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Эксперт не найден")
    return expert


def filter_experts(
        db: Session,
        specialization: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
):
    query = db.query(models.Expert)

    if specialization:
        query = query.filter(models.Expert.specialization.ilike(f"%{specialization}%"))

    if city:
        query = query.filter(models.Expert.city.ilike(f"%{city}%"))

    if search:
        # Поиск по ФИО или специализации
        query = query.filter(
            or_(
                models.Expert.full_name.ilike(f"%{search}%"),
                models.Expert.specialization.ilike(f"%{search}%")
            )
        )

    return query.offset(skip).limit(limit).all()


def create_expert(db: Session, expert: schemas.ExpertCreate, avatar_url: Optional[str] = None) -> models.Expert:
    # Создаем словари для вложенных education и experience
    education_data = [edu.dict() for edu in expert.education]
    experience_data = [exp.dict() for exp in expert.experience]

    # Создаем объект Expert сначала без вложенных списков
    # Исключаем avatar_url из словаря схемы, так как он передается отдельным аргументом
    expert_dict = expert.dict(exclude={'education', 'experience', 'avatar_url'})

    db_expert = models.Expert(
        **expert_dict,
        avatar_url=avatar_url  # Устанавливаем avatar_url из параметра
    )

    # Добавляем эксперта в сессию, чтобы получить ID (если используется автоинкремент или ID нужен для внешних ключей)
    db.add(db_expert)
    db.flush() # Применяем изменения для получения ID, если это необходимо перед созданием связанных объектов

    # Создаем и связываем записи об образовании
    for edu_item in education_data:
        db_edu = models.Education(**edu_item, expert_id=db_expert.id)
        db.add(db_edu)

    # Создаем и связываем записи об опыте работы
    for exp_item in experience_data:
        db_exp = models.WorkExperience(**exp_item, expert_id=db_expert.id)
        db.add(db_exp)

    db.commit()
    db.refresh(db_expert)
    return db_expert


def create_collaboration_request(db: Session, expert_id: int, request: schemas.CollaborationRequestCreate):
    # Проверка существования эксперта
    expert = get_expert(db, expert_id)

    db_request = models.CollaborationRequest(
        expert_id=expert_id,
        user_name=request.user_name,
        user_email=request.user_email,
        user_phone=request.user_phone,
        message=request.message,
        request_id=str(uuid4())
    )

    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def update_collaboration_request_status(db: Session, request_id: str, status: str):
    request = db.query(models.CollaborationRequest).filter(
        models.CollaborationRequest.request_id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрос не найден")

    if status not in ["pending", "approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый статус. Разрешены: pending, approved, rejected"
        )

    request.status = status
    db.commit()
    db.refresh(request)
    return request


from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime

from app.models import Vacancy, VacancyApplication
from app.resume_models import Profession, City, Region, Skill, Resume
from app.schemas import VacancyCreate, VacancyUpdate

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime

from app.models import Vacancy, VacancyApplication, vacancy_skills
from app.resume_models import Profession, City, Region, Skill, Resume
from app.schemas import VacancyCreate, VacancyUpdate


def get_vacancies_filtered(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        keyword: Optional[str] = None,
        lang: str = "ru",
        profession_id: Optional[int] = None,
        city_id: Optional[int] = None,
        region_id: Optional[int] = None,
        employment_type: Optional[str] = None,
        work_type: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        is_active: bool = True
):
    """Получение списка вакансий"""
    query = db.query(Vacancy)

    if is_active:
        query = query.filter(Vacancy.is_active == True)

    if profession_id:
        query = query.filter(Vacancy.profession_id == profession_id)

    if city_id:
        query = query.filter(Vacancy.city_id == city_id)

    if region_id:
        query = query.join(City, Vacancy.city_id == City.id).filter(City.region_id == region_id)

    if employment_type:
        query = query.filter(Vacancy.employment_type == employment_type)

    if work_type:
        query = query.filter(Vacancy.work_type == work_type)

    if min_salary:
        query = query.filter(
            or_(
                Vacancy.salary_min >= min_salary,
                Vacancy.salary_max >= min_salary
            )
        )

    if max_salary:
        query = query.filter(
            or_(
                Vacancy.salary_max <= max_salary,
                Vacancy.salary_min <= max_salary
            )
        )

    if keyword:
        search_term = f"%{keyword}%"
        if lang == "kz":
            query = query.filter(
                or_(
                    Vacancy.description_kz.ilike(search_term),
                    Vacancy.requirements_kz.ilike(search_term)
                )
            )
        else:
            query = query.filter(
                or_(
                    Vacancy.description_ru.ilike(search_term),
                    Vacancy.requirements_ru.ilike(search_term)
                )
            )

    query = query.order_by(desc(Vacancy.created_at))
    vacancies = query.offset(skip).limit(limit).all()

    # Добавляем данные из справочников вручную
    result = []
    for vacancy in vacancies:
        vacancy_dict = {
            "id": vacancy.id,
            "profession_id": vacancy.profession_id,
            "city_id": vacancy.city_id,
            "description_kz": vacancy.description_kz,
            "description_ru": vacancy.description_ru,
            "requirements_kz": vacancy.requirements_kz,
            "requirements_ru": vacancy.requirements_ru,
            "employment_type": vacancy.employment_type,
            "work_type": vacancy.work_type,
            "salary_min": vacancy.salary_min,
            "salary_max": vacancy.salary_max,
            "experience_years": vacancy.experience_years,
            "company_name": vacancy.company_name,
            "contact_email": vacancy.contact_email,
            "contact_phone": vacancy.contact_phone,
            "deadline": vacancy.deadline,
            "is_active": vacancy.is_active,
            "created_at": vacancy.created_at,
            "updated_at": vacancy.updated_at,
        }

        # Получаем профессию
        if vacancy.profession_id:
            profession = db.query(Profession).filter(Profession.id == vacancy.profession_id).first()
            if profession:
                vacancy_dict["profession"] = {
                    "id": profession.id,
                    "name_ru": profession.name_ru,
                    "name_kz": profession.name_kz
                }

        # Получаем город
        if vacancy.city_id:
            city = db.query(City).filter(City.id == vacancy.city_id).first()
            if city:
                vacancy_dict["city"] = {
                    "id": city.id,
                    "name_ru": city.name_ru,
                    "name_kz": city.name_kz,
                    "region_id": city.region_id
                }

        # Получаем навыки
        skills = db.query(Skill).join(vacancy_skills).filter(
            vacancy_skills.c.vacancy_id == vacancy.id
        ).all()
        vacancy_dict["required_skills"] = [
            {"id": s.id, "name_ru": s.name_ru, "name_kz": s.name_kz}
            for s in skills
        ]

        result.append(vacancy_dict)

    return result


def filter_vacancies(
        db: Session,
        profession_id: Optional[int] = None,
        city_id: Optional[int] = None,
        region_id: Optional[int] = None,
        employment_type: Optional[str] = None,
        work_type: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
):
    """Поиск вакансий"""
    query = db.query(Vacancy).filter(Vacancy.is_active == True)

    if profession_id:
        query = query.filter(Vacancy.profession_id == profession_id)

    if city_id:
        query = query.filter(Vacancy.city_id == city_id)

    if region_id:
        query = query.join(City, Vacancy.city_id == City.id).filter(City.region_id == region_id)

    if employment_type:
        query = query.filter(Vacancy.employment_type == employment_type)

    if work_type:
        query = query.filter(Vacancy.work_type == work_type)

    if min_salary or max_salary:
        if min_salary and max_salary:
            query = query.filter(
                and_(
                    Vacancy.salary_min >= min_salary,
                    Vacancy.salary_max <= max_salary
                )
            )
        elif min_salary:
            query = query.filter(Vacancy.salary_min >= min_salary)
        elif max_salary:
            query = query.filter(Vacancy.salary_max <= max_salary)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Vacancy.description_ru.ilike(search_term),
                Vacancy.description_kz.ilike(search_term),
                Vacancy.requirements_ru.ilike(search_term),
                Vacancy.requirements_kz.ilike(search_term)
            )
        )

    return query.order_by(desc(Vacancy.created_at)).offset(skip).limit(limit).all()


def get_vacancy(db: Session, vacancy_id: int, include_inactive: bool = False):
    """Получение одной вакансии"""
    query = db.query(Vacancy).filter(Vacancy.id == vacancy_id)

    if not include_inactive:
        query = query.filter(Vacancy.is_active == True)

    vacancy = query.first()
    if not vacancy:
        return None

    # Добавляем данные вручную
    result = {
        "id": vacancy.id,
        "profession_id": vacancy.profession_id,
        "city_id": vacancy.city_id,
        "description_kz": vacancy.description_kz,
        "description_ru": vacancy.description_ru,
        "requirements_kz": vacancy.requirements_kz,
        "requirements_ru": vacancy.requirements_ru,
        "employment_type": vacancy.employment_type,
        "work_type": vacancy.work_type,
        "salary_min": vacancy.salary_min,
        "salary_max": vacancy.salary_max,
        "experience_years": vacancy.experience_years,
        "company_name": vacancy.company_name,
        "contact_email": vacancy.contact_email,
        "contact_phone": vacancy.contact_phone,
        "deadline": vacancy.deadline,
        "is_active": vacancy.is_active,
        "created_at": vacancy.created_at,
        "updated_at": vacancy.updated_at,
    }

    # Профессия
    if vacancy.profession_id:
        profession = db.query(Profession).filter(Profession.id == vacancy.profession_id).first()
        if profession:
            result["profession"] = {
                "id": profession.id,
                "name_ru": profession.name_ru,
                "name_kz": profession.name_kz
            }

    # Город
    if vacancy.city_id:
        city = db.query(City).filter(City.id == vacancy.city_id).first()
        if city:
            result["city"] = {
                "id": city.id,
                "name_ru": city.name_ru,
                "name_kz": city.name_kz,
                "region_id": city.region_id
            }
            # Регион
            region = db.query(Region).filter(Region.id == city.region_id).first()
            if region:
                result["region"] = {
                    "id": region.id,
                    "name_ru": region.name_ru,
                    "name_kz": region.name_kz
                }

    # Навыки
    skills = db.query(Skill).join(vacancy_skills).filter(
        vacancy_skills.c.vacancy_id == vacancy.id
    ).all()
    result["required_skills"] = [
        {"id": s.id, "name_ru": s.name_ru, "name_kz": s.name_kz}
        for s in skills
    ]

    return result


def create_vacancy(db: Session, vacancy: VacancyCreate):
    """Создание вакансии"""
    db_vacancy = Vacancy(
        profession_id=vacancy.profession_id,
        city_id=vacancy.city_id,
        description_kz=vacancy.description_kz,
        description_ru=vacancy.description_ru,
        requirements_kz=vacancy.requirements_kz,
        requirements_ru=vacancy.requirements_ru,
        employment_type=vacancy.employment_type,
        work_type=vacancy.work_type,
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        experience_years=vacancy.experience_years,
        contact_email=vacancy.contact_email,
        contact_phone=vacancy.contact_phone,
        company_name=vacancy.company_name,
        deadline=vacancy.deadline,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_vacancy)
    db.flush()

    # Добавляем навыки
    if vacancy.required_skills:
        for skill_id in vacancy.required_skills:
            db.execute(
                vacancy_skills.insert().values(
                    vacancy_id=db_vacancy.id,
                    skill_id=skill_id
                )
            )

    db.commit()
    db.refresh(db_vacancy)

    return get_vacancy(db, db_vacancy.id)


def update_vacancy(db: Session, vacancy_id: int, vacancy_update: VacancyUpdate):
    """Обновление вакансии"""
    db_vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not db_vacancy:
        return None

    update_data = vacancy_update.dict(exclude_unset=True, exclude={'required_skills'})

    for field, value in update_data.items():
        setattr(db_vacancy, field, value)

    # Обновляем навыки
    if vacancy_update.required_skills is not None:
        # Удаляем старые
        db.execute(
            vacancy_skills.delete().where(vacancy_skills.c.vacancy_id == vacancy_id)
        )
        # Добавляем новые
        for skill_id in vacancy_update.required_skills:
            db.execute(
                vacancy_skills.insert().values(
                    vacancy_id=vacancy_id,
                    skill_id=skill_id
                )
            )

    db_vacancy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_vacancy)

    return get_vacancy(db, vacancy_id)


def delete_vacancy(db: Session, vacancy_id: int):
    """Деактивация вакансии"""
    db_vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if db_vacancy:
        db_vacancy.is_active = False
        db_vacancy.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False


def create_vacancy_application(db: Session, user_id: int, application):
    """Создание отклика"""
    db_application = VacancyApplication(
        user_id=user_id,
        vacancy_id=application.vacancy_id,
        resume_id=application.resume_id,
        cover_letter=application.cover_letter,
        status="new",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    return db_application


def check_existing_application(db: Session, user_id: int, vacancy_id: int):
    """Проверка существующего отклика"""
    return db.query(VacancyApplication).filter(
        VacancyApplication.user_id == user_id,
        VacancyApplication.vacancy_id == vacancy_id
    ).first()


def get_user_applications(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None
):
    """Получение откликов пользователя"""
    query = db.query(VacancyApplication).filter(VacancyApplication.user_id == user_id)

    if status_filter:
        query = query.filter(VacancyApplication.status == status_filter)

    return query.order_by(desc(VacancyApplication.created_at)).offset(skip).limit(limit).all()


def get_vacancy_applications(
        db: Session,
        vacancy_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
):
    """Получение откликов на вакансию"""
    query = db.query(VacancyApplication).filter(
        VacancyApplication.vacancy_id == vacancy_id
    )

    if status_filter:
        query = query.filter(VacancyApplication.status == status_filter)

    return query.order_by(desc(VacancyApplication.created_at)).offset(skip).limit(limit).all()


def get_vacancy_application(db: Session, application_id: int, vacancy_id: int):
    """Получение конкретного отклика"""
    return db.query(VacancyApplication).filter(
        VacancyApplication.id == application_id,
        VacancyApplication.vacancy_id == vacancy_id
    ).first()


def update_vacancy_application_status(db: Session, application_id: int, status: str):
    """Обновление статуса отклика"""
    application = db.query(VacancyApplication).filter(
        VacancyApplication.id == application_id
    ).first()

    if application:
        application.status = status
        application.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(application)

    return application


def delete_vacancy_application(db: Session, application_id: int, user_id: int):
    """Удаление отклика"""
    application = db.query(VacancyApplication).filter(
        VacancyApplication.id == application_id,
        VacancyApplication.user_id == user_id
    ).first()

    if application:
        db.delete(application)
        db.commit()
        return True
    return False


def get_resume(db: Session, resume_id: int, user_id: int):
    """Получение резюме пользователя"""
    return db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user_id,
        Resume.is_active == True
    ).first()


def get_vacancies_stats(db: Session):
    """Общая статистика"""
    total_vacancies = db.query(func.count(Vacancy.id)).scalar()
    active_vacancies = db.query(func.count(Vacancy.id)).filter(Vacancy.is_active == True).scalar()
    total_applications = db.query(func.count(VacancyApplication.id)).scalar()
    new_applications = db.query(func.count(VacancyApplication.id)).filter(
        VacancyApplication.status == "new"
    ).scalar()

    return {
        "total_vacancies": total_vacancies,
        "active_vacancies": active_vacancies,
        "total_applications": total_applications,
        "new_applications": new_applications,
        "by_profession": get_vacancies_by_profession(db),
        "by_city": get_vacancies_by_city(db)
    }


def get_vacancies_by_profession(db: Session, limit: int = 10):
    """Статистика по профессиям"""
    result = db.query(
        Profession.id,
        Profession.name_ru,
        Profession.name_kz,
        func.count(Vacancy.id).label('count')
    ).join(Vacancy, Vacancy.profession_id == Profession.id).filter(
        Vacancy.is_active == True
    ).group_by(
        Profession.id, Profession.name_ru, Profession.name_kz
    ).order_by(desc('count')).limit(limit).all()

    return [
        {
            "profession_id": row.id,
            "profession_name_ru": row.name_ru,
            "profession_name_kz": row.name_kz,
            "vacancies_count": row.count
        }
        for row in result
    ]


def get_vacancies_by_city(db: Session, limit: int = 10):
    """Статистика по городам"""
    result = db.query(
        City.id,
        City.name_ru,
        City.name_kz,
        func.count(Vacancy.id).label('count')
    ).join(Vacancy, Vacancy.city_id == City.id).filter(
        Vacancy.is_active == True
    ).group_by(
        City.id, City.name_ru, City.name_kz
    ).order_by(desc('count')).limit(limit).all()

    return [
        {
            "city_id": row.id,
            "city_name_ru": row.name_ru,
            "city_name_kz": row.name_kz,
            "vacancies_count": row.count
        }
        for row in result
    ]
def get_vacancy_filters_stats(db: Session):
    """
    Получение статистики для фильтров (уникальные значения)
    """
    employment_types = db.query(Vacancy.employment_type).filter(
        Vacancy.employment_type.isnot(None),
        Vacancy.is_active == True
    ).distinct().all()

    work_types = db.query(Vacancy.work_type).filter(
        Vacancy.work_type.isnot(None),
        Vacancy.is_active == True
    ).distinct().all()

    salary_range = db.query(
        func.min(Vacancy.salary).label('min_salary'),
        func.max(Vacancy.salary).label('max_salary')
    ).filter(
        Vacancy.salary.isnot(None),
        Vacancy.is_active == True
    ).first()

    return {
        "employment_types": [et[0] for et in employment_types if et[0]],
        "work_types": [wt[0] for wt in work_types if wt[0]],
        "salary_range": {
            "min": salary_range.min_salary or 0,
            "max": salary_range.max_salary or 0
        }
    }


def get_vacancies(db: Session, skip: int = 0, limit: int = 100) -> List[Vacancy]:
    """
    Получение списка всех вакансий с пагинацией
    """
    return db.query(Vacancy).order_by(Vacancy.created_at.desc()).offset(skip).limit(limit).all()


def get_vacancy(db: Session, vacancy_id: int) -> Optional[Vacancy]:
    """
    Получение вакансии по ID
    """
    return db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()


def filter_vacancies(
        db: Session,
        employment_type: Optional[str] = None,
        work_type: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
) -> List[Vacancy]:
    """
    Поиск и фильтрация вакансий по различным параметрам
    """
    query = db.query(Vacancy)

    # Применяем фильтры, если они указаны
    if employment_type:
        query = query.filter(Vacancy.employment_type == employment_type)

    if work_type:
        query = query.filter(Vacancy.work_type == work_type)

    if city:
        query = query.filter(Vacancy.location.contains(city))

    if search:
        query = query.filter(
            or_(
                Vacancy.title.ilike(f"%{search}%"),
                Vacancy.description.ilike(f"%{search}%")
            )
        )

    # Применяем пагинацию и возвращаем результат
    return query.order_by(Vacancy.created_at.desc()).offset(skip).limit(limit).all()



# Add these functions to crud.py

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import VacancyApplication
from app.schemas import VacancyApplicationCreate


def get_user_resumes(db: Session, user_id: int) -> List[resume_models.Resume]:
    """Получение всех активных резюме пользователя"""
    return db.query(resume_models.Resume).filter(
        and_(
            resume_models.Resume.user_id == user_id,
            resume_models.Resume.is_active == True
        )
    ).all()


def get_resume(db: Session, resume_id: int, user_id: int) -> Optional[resume_models.Resume]:
    """Получение конкретного резюме пользователя"""
    return db.query(resume_models.Resume).filter(
        and_(
            resume_models.Resume.id == resume_id,
            resume_models.Resume.user_id == user_id,
            resume_models.Resume.is_active == True
        )
    ).first()


def delete_vacancy_application(db: Session, application_id: int, user_id: int) -> bool:
    """Удаление отклика (только автором)"""
    db_application = db.query(VacancyApplication).filter(
        and_(
            VacancyApplication.id == application_id,
            VacancyApplication.user_id == user_id
        )
    ).first()

    if db_application:
        db.delete(db_application)
        db.commit()
        return True

    return False



from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime

# Import your models and schemas
from app.models import Event, EventProgram, EventSpeaker, EventParticipant
from app.schemas import EventCreate, EventUpdate, EventParticipantCreate


def get_events(db: Session, skip: int = 0, limit: int = 100):
    """Get all events with pagination"""
    return db.query(Event).offset(skip).limit(limit).all()


def filter_events(
        db: Session,
        format: Optional[str] = None,
        search: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
):
    """Filter events by various parameters"""
    query = db.query(Event)

    # Apply filters
    if format:
        query = query.filter(Event.format == format)

    if search:
        query = query.filter(
            or_(
                Event.title.ilike(f"%{search}%"),
                Event.description.ilike(f"%{search}%"),
                Event.location.ilike(f"%{search}%")
            )
        )

    # Date range filter
    if from_date and to_date:
        query = query.filter(
            and_(
                Event.event_date >= from_date,
                Event.event_date <= to_date
            )
        )
    elif from_date:
        query = query.filter(Event.event_date >= from_date)
    elif to_date:
        query = query.filter(Event.event_date <= to_date)

    # Apply pagination
    return query.offset(skip).limit(limit).all()


def get_event(db: Session, event_id: int):
    """Get a specific event by ID"""
    return db.query(Event).filter(Event.id == event_id).first()


def create_event(db: Session, event: EventCreate):
    """Create a new event with programs and speakers"""
    # Extract nested objects
    programs = event.programs
    speakers = event.speakers

    # Create event object without nested objects
    db_event = Event(
        title=event.title,
        event_date=event.event_date,
        location=event.location,
        format=event.format,
        description=event.description,
        event_photo=event.event_photo
    )

    # Add event to session
    db.add(db_event)
    db.flush()

    # Create programs
    for program in programs:
        db_program = EventProgram(
            event_id=db_event.id,
            time=program.time,
            description=program.description
        )
        db.add(db_program)

    # Create speakers
    for speaker in speakers:
        db_speaker = EventSpeaker(
            event_id=db_event.id,
            first_name=speaker.first_name,
            last_name=speaker.last_name,
            middle_name=speaker.middle_name,
            bio=speaker.bio,
            photo_url=speaker.photo_url,
            linkedin_url=speaker.linkedin_url,
            instagram_url=speaker.instagram_url,
            facebook_url=speaker.facebook_url
        )
        db.add(db_speaker)

    db.commit()
    db.refresh(db_event)
    return db_event


def update_event(db: Session, event_id: int, event_update: EventUpdate):
    """Update an existing event"""
    db_event = db.query(Event).filter(Event.id == event_id).first()

    if db_event:
        # Update fields that are provided
        update_data = event_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_event, field, value)

        db_event.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_event)

    return db_event


def delete_event(db: Session, event_id: int):
    """Delete an event"""
    db_event = db.query(Event).filter(Event.id == event_id).first()

    if db_event:
        db.delete(db_event)
        db.commit()
        return True

    return False


def create_event_participant(db: Session, event_id: int, participant: EventParticipantCreate):
    """Create a new event participant (registration)"""
    db_participant = EventParticipant(
        event_id=event_id,
        first_name=participant.first_name,
        last_name=participant.last_name,
        company_name=participant.company_name,
        email=participant.email
    )

    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)

    return db_participant


def get_event_participants(db: Session, event_id: int, skip: int = 0, limit: int = 100):
    """Get all participants for a specific event"""
    return db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).offset(skip).limit(limit).all()


from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import (
    Course, CourseCategory, CourseChapter, CourseLesson, CourseTest, CourseTestAnswer,
    CourseEnrollment, CourseLessonProgress, CourseTestResult, course_category, User
)
from app.schemas import (
    CourseCreate, CourseUpdate, CourseFilter, CourseCategoryCreate,
    CourseChapterCreate, CourseLessonCreate, CourseTestCreate
)


# Операции с категориями курсов

def get_course_categories(db: Session) -> List[CourseCategory]:
    """Получение всех категорий курсов"""
    return db.query(CourseCategory).all()


def create_course_category(db: Session, category: CourseCategoryCreate) -> CourseCategory:
    """Создание новой категории курса"""
    db_category = CourseCategory(
        name=category.name,
        description=category.description
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_category(db: Session, category_id: int) -> Optional[CourseCategory]:
    """Получение категории по ID"""
    return db.query(CourseCategory).filter(CourseCategory.id == category_id).first()


# Операции с курсами

def get_courses(db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
    """Получение списка всех доступных курсов"""
    return db.query(Course).filter(Course.status == "approved").offset(skip).limit(limit).all()


def get_recommended_courses(db: Session, skip: int = 0, limit: int = 10) -> List[Course]:
    """Получение списка рекомендуемых курсов"""
    return db.query(Course).filter(
        and_(Course.is_recommended == True, Course.status == "approved")
    ).offset(skip).limit(limit).all()


def get_popular_courses(db: Session, skip: int = 0, limit: int = 10) -> List[Course]:
    """Получение списка популярных курсов"""
    return db.query(Course).filter(
        and_(Course.is_popular == True, Course.status == "approved")
    ).offset(skip).limit(limit).all()


def get_most_searched_courses(db: Session, skip: int = 0, limit: int = 10) -> List[Course]:
    """Получение списка часто ищемых курсов (по количеству просмотров)"""
    return db.query(Course).filter(Course.status == "approved").order_by(desc(Course.views_count)).offset(skip).limit(
        limit).all()


def get_free_courses(db: Session, skip: int = 0, limit: int = 10) -> List[Course]:
    """Получение списка бесплатных курсов"""
    return db.query(Course).filter(
        and_(Course.is_free == True, Course.status == "approved")
    ).offset(skip).limit(limit).all()


def filter_courses(db: Session, filters: CourseFilter, skip: int = 0, limit: int = 100) -> List[Course]:
    """Фильтрация курсов по различным параметрам"""
    query = db.query(Course).filter(Course.status == "approved")

    # Применяем фильтры
    if filters.category_id is not None:
        query = query.join(course_category).filter(course_category.c.category_id == filters.category_id)

    if filters.language is not None:
        query = query.filter(Course.language == filters.language)

    if filters.level is not None:
        query = query.filter(Course.level == filters.level)

    if filters.is_free is not None:
        query = query.filter(Course.is_free == filters.is_free)

    if filters.price_min is not None:
        query = query.filter(Course.price >= filters.price_min)

    if filters.price_max is not None:
        query = query.filter(Course.price <= filters.price_max)

    if filters.search is not None:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Course.title.ilike(search_term),
                Course.description.ilike(search_term),
                Course.skills.ilike(search_term)
            )
        )

    return query.offset(skip).limit(limit).all()


def get_course(db: Session, course_id: int) -> Optional[Course]:
    """Получение курса по ID"""
    return db.query(Course).filter(Course.id == course_id).first()


def create_course(db: Session, course: CourseCreate, author_id: int) -> Course:
    """Создание нового курса"""
    # Создаем курс
    db_course = Course(
        title=course.title,
        description=course.description,
        course_url=course.course_url,
        language=course.language,
        duration=course.duration,
        skills=course.skills,
        currency=course.currency,
        price=course.price,
        level=course.level,
        cover_image=course.cover_image,
        video_preview=course.video_preview,
        is_free=course.is_free,
        author_id=author_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_course)
    db.commit()
    db.refresh(db_course)

    # Добавляем категории
    if course.categories:
        for category_id in course.categories:
            category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
            if category:
                db_course.categories.append(category)

        db.commit()
        db.refresh(db_course)

    # Добавляем главы и уроки, если они есть
    if course.chapters:
        for chapter_data in course.chapters:
            add_chapter_to_course(db, db_course.id, chapter_data)

    return db_course


def update_course(db: Session, course_id: int, course_update: CourseUpdate) -> Optional[Course]:
    """Обновление существующего курса"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return None

    # Обновляем поля курса
    for field, value in course_update.dict(exclude_unset=True).items():
        if field == "categories":
            # Обработка категорий отдельно
            continue
        setattr(db_course, field, value)

    db_course.updated_at = datetime.utcnow()

    # Обновляем категории, если они были переданы
    if course_update.categories is not None:
        # Очищаем текущие категории
        db_course.categories = []

        # Добавляем новые категории
        for category_id in course_update.categories:
            category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
            if category:
                db_course.categories.append(category)

    db.commit()
    db.refresh(db_course)
    return db_course


def update_course_status(db: Session, course_id: int, status: str, status_comment: Optional[str] = None) -> Optional[
    Course]:
    """Обновление статуса курса"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return None

    db_course.status = status
    if status_comment:
        db_course.status_comment = status_comment

    db.commit()
    db.refresh(db_course)
    return db_course


def increment_course_views(db: Session, course_id: int) -> Optional[Course]:
    """Увеличение счетчика просмотров курса"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return None

    db_course.views_count += 1
    db.commit()
    return db_course


def delete_course(db: Session, course_id: int) -> bool:
    """Удаление курса"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return False

    db.delete(db_course)
    db.commit()
    return True


# Операции с главами курса

def get_chapter(db: Session, chapter_id: int) -> Optional[CourseChapter]:
    """Получение главы по ID"""
    return db.query(CourseChapter).filter(CourseChapter.id == chapter_id).first()


def add_chapter_to_course(db: Session, course_id: int, chapter: CourseChapterCreate) -> Course:
    """Добавление новой главы к курсу"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return None

    # Создаем главу
    db_chapter = CourseChapter(
        course_id=course_id,
        title=chapter.title,
        order=chapter.order
    )

    db.add(db_chapter)
    db.commit()
    db.refresh(db_chapter)

    # Добавляем уроки, если они есть
    if chapter.lessons:
        for lesson_data in chapter.lessons:
            add_lesson_to_chapter(db, db_chapter.id, lesson_data)

    # Возвращаем обновленный курс
    db.refresh(db_course)
    return db_course


# Операции с уроками

def get_lesson(db: Session, lesson_id: int) -> Optional[CourseLesson]:
    """Получение урока по ID"""
    return db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()


def add_lesson_to_chapter(db: Session, chapter_id: int, lesson: CourseLessonCreate) -> Course:
    """Добавление нового урока к главе"""
    db_chapter = db.query(CourseChapter).filter(CourseChapter.id == chapter_id).first()
    if not db_chapter:
        return None

    # Создаем урок
    db_lesson = CourseLesson(
        chapter_id=chapter_id,
        title=lesson.title,
        description=lesson.description,
        video_url=lesson.video_url,
        order=lesson.order
    )

    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)

    # Добавляем тесты, если они есть
    if lesson.tests:
        for test_data in lesson.tests:
            add_test_to_lesson(db, db_lesson.id, test_data)

    # Возвращаем обновленный курс
    db_course = db.query(Course).filter(Course.id == db_chapter.course_id).first()
    db.refresh(db_course)
    return db_course


# Операции с тестами

def get_test(db: Session, test_id: int) -> Optional[CourseTest]:
    """Получение теста по ID"""
    return db.query(CourseTest).filter(CourseTest.id == test_id).first()


def add_test_to_lesson(db: Session, lesson_id: int, test: CourseTestCreate) -> Course:
    """Добавление нового теста к уроку"""
    db_lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not db_lesson:
        return None

    # Создаем тест
    db_test = CourseTest(
        lesson_id=lesson_id,
        question=test.question,
        image=test.image
    )

    db.add(db_test)
    db.commit()
    db.refresh(db_test)

    # Добавляем варианты ответов
    for answer_data in test.answers:
        db_answer = CourseTestAnswer(
            test_id=db_test.id,
            answer_text=answer_data.answer_text,
            is_correct=answer_data.is_correct
        )
        db.add(db_answer)

    db.commit()

    # Возвращаем обновленный курс
    db_chapter = db.query(CourseChapter).filter(CourseChapter.id == db_lesson.chapter_id).first()
    db_course = db.query(Course).filter(Course.id == db_chapter.course_id).first()
    db.refresh(db_course)
    return db_course


# Операции с записями на курсы

def get_user_enrollments(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[CourseEnrollment]:
    """Получение списка курсов, на которые записан пользователь"""
    return db.query(CourseEnrollment).filter(CourseEnrollment.user_id == user_id).offset(skip).limit(limit).all()


def get_enrollment(db: Session, user_id: int, course_id: int) -> Optional[CourseEnrollment]:
    """Получение записи на курс для конкретного пользователя"""
    return db.query(CourseEnrollment).filter(
        and_(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id)
    ).first()


def create_enrollment(db: Session, user_id: int, course_id: int) -> CourseEnrollment:
    """Создание новой записи на курс"""
    # Создаем запись о зачислении
    db_enrollment = CourseEnrollment(
        user_id=user_id,
        course_id=course_id,
        enrollment_date=datetime.utcnow(),
        completed=False,
        progress=0.0
    )

    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)

    # Получаем все уроки курса для инициализации прогресса
    chapters = db.query(CourseChapter).filter(CourseChapter.course_id == course_id).all()
    for chapter in chapters:
        lessons = db.query(CourseLesson).filter(CourseLesson.chapter_id == chapter.id).all()
        for lesson in lessons:
            # Создаем запись о прогрессе для каждого урока
            lesson_progress = CourseLessonProgress(
                enrollment_id=db_enrollment.id,
                lesson_id=lesson.id,
                is_completed=False,
                last_viewed_at=datetime.utcnow()
            )
            db.add(lesson_progress)

    db.commit()
    db.refresh(db_enrollment)
    return db_enrollment


def complete_lesson(db: Session, enrollment_id: int, lesson_id: int) -> Dict[str, Any]:
    """Отметка урока как завершенного и обновление общего прогресса"""
    # Находим запись о прогрессе урока
    lesson_progress = db.query(CourseLessonProgress).filter(
        and_(
            CourseLessonProgress.enrollment_id == enrollment_id,
            CourseLessonProgress.lesson_id == lesson_id
        )
    ).first()

    if not lesson_progress:
        # Если запись не найдена, создаем новую
        lesson_progress = CourseLessonProgress(
            enrollment_id=enrollment_id,
            lesson_id=lesson_id,
            is_completed=True,
            last_viewed_at=datetime.utcnow()
        )
        db.add(lesson_progress)
    else:
        # Обновляем существующую запись
        lesson_progress.is_completed = True
        lesson_progress.last_viewed_at = datetime.utcnow()

    db.commit()

    # Обновляем общий прогресс по курсу
    enrollment = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()

    # Получаем общее количество уроков в курсе
    total_lessons_count = db.query(CourseLesson).join(
        CourseChapter, CourseLesson.chapter_id == CourseChapter.id
    ).filter(
        CourseChapter.course_id == enrollment.course_id
    ).count()

    # Получаем все завершенные уроки
    completed_lessons_progress = db.query(CourseLessonProgress).filter(
        and_(
            CourseLessonProgress.enrollment_id == enrollment_id,
            CourseLessonProgress.is_completed == True
        )
    ).all()

    completed_lessons_count = len(completed_lessons_progress)
    completed_lesson_ids = [progress.lesson_id for progress in completed_lessons_progress]

    # Рассчитываем процент выполнения
    if total_lessons_count > 0:
        progress = (completed_lessons_count / total_lessons_count) * 100
    else:
        progress = 0

    # Обновляем прогресс и проверяем, завершен ли курс
    enrollment.progress = progress
    if progress >= 100:
        enrollment.completed = True
        enrollment.completion_date = datetime.utcnow()

    db.commit()
    db.refresh(enrollment)

    # Получаем завершенные тесты
    completed_tests = get_completed_tests(db, enrollment.id)

    # Формируем полный ответ с прогрессом
    return {
        "enrollment": enrollment,
        "completed_lessons": completed_lesson_ids,
        "completed_tests": completed_tests
    }


def submit_test_answers(db: Session, enrollment_id: int, test_id: int, answer_ids: List[int]) -> Dict[str, Any]:
    """Отправка ответов на тест и проверка результатов"""
    # Получаем правильные ответы для теста
    correct_answers = db.query(CourseTestAnswer).filter(
        and_(
            CourseTestAnswer.test_id == test_id,
            CourseTestAnswer.is_correct == True
        )
    ).all()

    # Получаем выбранные пользователем ответы
    user_answers = db.query(CourseTestAnswer).filter(
        and_(
            CourseTestAnswer.test_id == test_id,
            CourseTestAnswer.id.in_(answer_ids)
        )
    ).all()

    # Проверяем ответы
    correct_answer_ids = {answer.id for answer in correct_answers}
    user_answer_ids = {answer.id for answer in user_answers}

    correct_count = len(correct_answer_ids.intersection(user_answer_ids))
    incorrect_count = len(user_answer_ids - correct_answer_ids)

    # Вычисляем процент правильных ответов
    total_correct_answers = len(correct_answers)
    if total_correct_answers > 0:
        score = (correct_count / total_correct_answers) * 100
    else:
        score = 0

    # Определяем, пройден ли тест
    passed = score >= 70  # Считаем тест пройденным, если набрано не менее 70%

    # Сохраняем результат
    test_result = db.query(CourseTestResult).filter(
        and_(
            CourseTestResult.enrollment_id == enrollment_id,
            CourseTestResult.test_id == test_id
        )
    ).first()

    if test_result:
        # Обновляем существующий результат
        test_result.is_passed = passed
        test_result.score = score
        test_result.attempt_count += 1
        test_result.last_attempt_at = datetime.utcnow()
    else:
        # Создаем новую запись о результате
        test_result = CourseTestResult(
            enrollment_id=enrollment_id,
            test_id=test_id,
            is_passed=passed,
            score=score,
            attempt_count=1,
            last_attempt_at=datetime.utcnow()
        )
        db.add(test_result)

    db.commit()

    # Формируем ответ
    return {
        "test_id": test_id,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "total_questions": total_correct_answers,
        "score": score,
        "passed": passed,
        "attempts": test_result.attempt_count
    }


# Вспомогательные функции

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Получение пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_completed_tests(db: Session, enrollment_id: int) -> List[int]:
    """
    Получение списка ID тестов, которые пользователь успешно прошел
    """
    # Получаем результаты тестов, которые пользователь прошел успешно
    results = db.query(CourseTestResult).filter(
        and_(
            CourseTestResult.enrollment_id == enrollment_id,
            CourseTestResult.is_passed == True
        )
    ).all()

    # Возвращаем список ID пройденных тестов
    return [result.test_id for result in results]


def get_enrollment_with_progress(db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
    """
    Получение полной информации о прогрессе пользователя по курсу,
    включая пройденные уроки и тесты
    """
    # Получаем запись о зачислении
    enrollment = db.query(CourseEnrollment).filter(
        and_(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id)
    ).first()

    if not enrollment:
        return None

    # Получаем пройденные уроки
    completed_lessons = db.query(CourseLessonProgress).filter(
        and_(
            CourseLessonProgress.enrollment_id == enrollment.id,
            CourseLessonProgress.is_completed == True
        )
    ).all()

    completed_lesson_ids = [progress.lesson_id for progress in completed_lessons]

    # Получаем пройденные тесты
    completed_tests = get_completed_tests(db, enrollment.id)

    # Формируем полную информацию о прогрессе
    return {
        "enrollment": enrollment,
        "completed_lessons": completed_lesson_ids,
        "completed_tests": completed_tests
    }


from sqlalchemy.orm import Session, joinedload
from typing import List, Optional


# Другие импорты...

# Уже существующие функции...

def get_user_enrollments(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[CourseEnrollment]:
    """Получение списка курсов, на которые записан пользователь"""
    return db.query(CourseEnrollment).filter(CourseEnrollment.user_id == user_id).offset(skip).limit(limit).all()


def get_user_enrollments_with_courses(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """
    Получение списка курсов пользователя с полной информацией о курсах
    """
    # Используем joinedload для загрузки связанных курсов за один запрос
    enrollments = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == user_id
    ).options(
        joinedload(CourseEnrollment.course)
    ).offset(skip).limit(limit).all()

    return enrollments


from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, List
from datetime import datetime
from app.models import Certificate, User, Course
from app.schemas import CertificateCreate


# Получение списка всех сертификатов с возможностью фильтрации по статусу
def get_certificates(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Certificate]:
    """
    Получение списка всех сертификатов с возможностью фильтрации
    """
    query = db.query(Certificate)

    # Применяем фильтр по статусу, если он указан
    if status:
        query = query.filter(Certificate.status == status)

    # Сортировка от новых к старым
    query = query.order_by(desc(Certificate.created_at))

    # Пагинация
    return query.offset(skip).limit(limit).all()


# Получение списка сертификатов конкретного пользователя
def get_user_certificates(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Certificate]:
    """
    Получение списка сертификатов определенного пользователя
    """
    return db.query(Certificate) \
        .filter(Certificate.user_id == user_id) \
        .order_by(desc(Certificate.created_at)) \
        .offset(skip) \
        .limit(limit) \
        .all()


# Получение конкретного сертификата по ID
def get_certificate(db: Session, certificate_id: int) -> Optional[Certificate]:
    """
    Получение сертификата по ID
    """
    return db.query(Certificate).filter(Certificate.id == certificate_id).first()


# Создание нового сертификата
def create_certificate(
        db: Session,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        course_id: Optional[int] = None,
        image_url: Optional[str] = None,
        file_url: Optional[str] = None
) -> Certificate:
    """
    Создание нового сертификата
    """
    # Создаем объект сертификата
    certificate = Certificate(
        user_id=user_id,
        title=title,
        description=description,
        course_id=course_id,
        image_url=image_url,
        file_url=file_url,
        issue_date=datetime.utcnow().date(),
        status="active"
    )

    # Добавляем в БД и коммитим
    db.add(certificate)
    db.commit()
    db.refresh(certificate)

    return certificate


# Обновление существующего сертификата
def update_certificate(
        db: Session,
        certificate_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        course_id: Optional[int] = None,
        image_url: Optional[str] = None,
        file_url: Optional[str] = None,
        status: Optional[str] = None
) -> Optional[Certificate]:
    """
    Обновление существующего сертификата
    """
    # Получаем сертификат по ID
    certificate = get_certificate(db, certificate_id)
    if not certificate:
        return None

    # Обновляем поля, если они переданы
    if title is not None:
        certificate.title = title
    if description is not None:
        certificate.description = description
    if course_id is not None:
        certificate.course_id = course_id
    if image_url is not None:
        certificate.image_url = image_url
    if file_url is not None:
        certificate.file_url = file_url
    if status is not None:
        certificate.status = status

    # Обновляем дату изменения
    certificate.updated_at = datetime.utcnow()

    # Коммитим изменения
    db.commit()
    db.refresh(certificate)

    return certificate


# Отзыв сертификата (изменение статуса)
def revoke_certificate(db: Session, certificate_id: int) -> Optional[Certificate]:
    """
    Отзыв сертификата (изменение статуса на 'revoked')
    """
    return update_certificate(db, certificate_id, status="revoked")


# Удаление сертификата
def delete_certificate(db: Session, certificate_id: int) -> bool:
    """
    Удаление сертификата
    """
    certificate = get_certificate(db, certificate_id)
    if not certificate:
        return False

    db.delete(certificate)
    db.commit()

    return True


# Получение пользователя по ID
def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Получение пользователя по ID
    """
    return db.query(User).filter(User.id == user_id).first()


# Получение курса по ID
def get_course(db: Session, course_id: int) -> Optional[Course]:
    """
    Получение курса по ID
    """
    return db.query(Course).filter(Course.id == course_id).first()