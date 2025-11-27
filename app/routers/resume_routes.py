from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.database import get_db
from app import oauth2
from app.resume_models import (
    Resume, ResumeEducation, ResumeWorkExperience, ResumeSkill,
    Profession, Region, City, Skill
)
from app.resume_schemas import (
    ResumeCreate, ResumeUpdate, ResumeResponse, ResumeFullResponse, ResumeFullCreate,
    ResumeEducationCreate, ResumeEducationUpdate, ResumeEducationResponse,
    ResumeWorkExperienceCreate, ResumeWorkExperienceUpdate, ResumeWorkExperienceResponse,
    ResumeSkillCreate, ResumeSkillResponse,
    ProfessionCreate, ProfessionResponse,
    RegionCreate, RegionResponse,
    CityCreate, CityResponse,
    SkillCreate, SkillResponse
)
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/v2/resumes", tags=["Resumes"])


# === СПРАВОЧНИКИ ===

@router.post("/professions", response_model=ProfessionResponse)
def create_profession(
        profession_data: ProfessionCreate,
        db: Session = Depends(get_db)
):
    """Создание новой профессии"""
    profession = Profession(**profession_data.dict())
    db.add(profession)
    db.commit()
    db.refresh(profession)

    return profession



@router.get("/professions", response_model=List[ProfessionResponse])
def get_professions(
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Получение списка профессий"""
    professions = db.query(Profession).all()

    # if category:
    #     query = query.filter(Profession.category == category)
    #
    # if search:
    #     query = query.filter(
    #         Profession.name_ru.ilike(f"%{search}%") |
    #         Profession.name_kz.ilike(f"%{search}%")
    #     )

    # professions = query.order_by(Profession.name_ru).offset(skip).limit(limit).all()
    return professions


@router.delete("/professions/{profession_id}")
def delete_profession(
        profession_id: int,
        db: Session = Depends(get_db)
):
    """Удаление профессии (мягкое удаление)"""
    profession = db.query(Profession).filter(Profession.id == profession_id).first()

    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профессия не найдена"
        )

    profession.is_active = False
    db.commit()

    return {"message": "Профессия успешно удалена"}


@router.post("/regions", response_model=RegionResponse)
def create_region(
        region_data: RegionCreate,
        db: Session = Depends(get_db)
):
    """Создание новой области"""
    region = Region(**region_data.dict())
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@router.get("/regions", response_model=List[RegionResponse])
def get_regions(
        skip: int = 0,
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """Получение списка областей"""
    regions = db.query(Region).filter(Region.is_active == True) \
        .order_by(Region.name_ru).offset(skip).limit(limit).all()
    return regions


@router.post("/cities", response_model=CityResponse)
def create_city(
        city_data: CityCreate,
        db: Session = Depends(get_db)
):
    """Создание нового города"""
    city = City(**city_data.dict())
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


@router.get("/cities", response_model=List[CityResponse])
def get_cities(
        region_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Получение списка городов"""
    query = db.query(City).filter(City.is_active == True)

    if region_id:
        query = query.filter(City.region_id == region_id)

    if search:
        query = query.filter(
            City.name_ru.ilike(f"%{search}%") |
            City.name_kz.ilike(f"%{search}%")
        )

    cities = query.order_by(City.name_ru).offset(skip).limit(limit).all()
    return cities


@router.post("/skills", response_model=SkillResponse)
def create_skill(
        skill_data: SkillCreate,
        db: Session = Depends(get_db)
):
    """Создание нового навыка"""
    skill = Skill(**skill_data.dict())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/skills", response_model=List[SkillResponse])
def get_skills(
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """Получение списка навыков"""
    query = db.query(Skill).filter(Skill.is_active == True)

    if category:
        query = query.filter(Skill.category == category)

    if search:
        query = query.filter(
            Skill.name_ru.ilike(f"%{search}%") |
            Skill.name_kz.ilike(f"%{search}%")
        )

    skills = query.order_by(Skill.name_ru).offset(skip).limit(limit).all()
    return skills


# === ОСНОВНЫЕ ОПЕРАЦИИ С РЕЗЮМЕ ===

@router.post("/", response_model=dict)
def create_resume(
        resume_data: ResumeCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Создание нового резюме"""
    # Проверяем, что у пользователя нет активного резюме
    # existing_resume = db.query(Resume).filter(
    #     Resume.user_id == current_user.id,
    #     Resume.is_active == True
    # ).first()

    # if existing_resume:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="У вас уже есть активное резюме. Деактивируйте его перед созданием нового."
    #     )

    # Проверяем существование профессии
    profession = db.query(Profession).filter(Profession.id == resume_data.profession_id).first()
    if not profession:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профессия не найдена"
        )

    # Проверяем существование города
    city = db.query(City).filter(City.id == resume_data.city_id).first()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Город не найден"
        )

    # Создаем резюме
    resume = Resume(
        user_id=current_user.id,
        **resume_data.dict()
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "message": "Резюме успешно создано",
        "resume_id": resume.id,
        "user_id": resume.user_id
    }


@router.get("/", response_model=List[ResumeResponse])
def get_resumes(
        profession_id: Optional[int] = None,
        city_id: Optional[int] = None,
        gender: Optional[str] = None,
        published_only: bool = True,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Получение списка резюме с фильтрами"""
    query = db.query(Resume).filter(Resume.is_active == True)

    if published_only:
        query = query.filter(Resume.is_published == True)

    if profession_id:
        query = query.filter(Resume.profession_id == profession_id)

    if city_id:
        query = query.filter(Resume.city_id == city_id)

    if gender:
        query = query.filter(Resume.gender == gender)

    resumes = query.order_by(desc(Resume.updated_at)).offset(skip).limit(limit).all()
    return resumes


@router.get("/my", response_model=List[ResumeResponse])
def get_my_resumes(
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Получение резюме текущего пользователя"""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(desc(Resume.updated_at)).all()

    return resumes


@router.get("/{resume_id}", response_model=ResumeFullResponse)
def get_resume_detail(
        resume_id: int,
        db: Session = Depends(get_db)
):
    """Получение детальной информации о резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    # Получаем образование
    education = db.query(ResumeEducation).filter(
        ResumeEducation.resume_id == resume_id
    ).all()

    # Получаем опыт работы
    work_experience = db.query(ResumeWorkExperience).filter(
        ResumeWorkExperience.resume_id == resume_id
    ).order_by(desc(ResumeWorkExperience.start_date)).all()

    # Получаем навыки
    skills = db.query(ResumeSkill).filter(
        ResumeSkill.resume_id == resume_id
    ).all()

    # Формируем ответ
    result = ResumeFullResponse.from_orm(resume)
    result.education = education
    result.work_experience = work_experience
    result.skills = skills

    return result


@router.put("/{resume_id}", response_model=dict)
def update_resume(
        resume_id: int,
        resume_data: ResumeUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Обновление резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    # Обновляем поля
    update_data = resume_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(resume, key):
            setattr(resume, key, value)

    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме успешно обновлено"}


@router.delete("/{resume_id}")
def delete_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление резюме (мягкое удаление)"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    resume.is_active = False
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме успешно удалено"}


# === ОБРАЗОВАНИЕ ===

@router.post("/{resume_id}/education", response_model=ResumeEducationResponse)
def add_education(
        resume_id: int,
        education_data: ResumeEducationCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Добавление образования к резюме"""
    # Проверяем, что резюме принадлежит пользователю
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    education = ResumeEducation(
        resume_id=resume_id,
        **education_data.dict()
    )

    db.add(education)
    db.commit()
    db.refresh(education)

    return education


@router.get("/{resume_id}/education", response_model=List[ResumeEducationResponse])
def get_resume_education(
        resume_id: int,
        db: Session = Depends(get_db)
):
    """Получение образования по резюме"""
    education = db.query(ResumeEducation).filter(
        ResumeEducation.resume_id == resume_id
    ).all()

    return education


@router.put("/education/{education_id}", response_model=dict)
def update_education(
        education_id: int,
        education_data: ResumeEducationUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Обновление образования"""
    education = db.query(ResumeEducation).join(Resume).filter(
        ResumeEducation.id == education_id,
        Resume.user_id == current_user.id
    ).first()

    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Образование не найдено"
        )

    update_data = education_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(education, key):
            setattr(education, key, value)

    db.commit()

    return {"message": "Образование обновлено"}


@router.delete("/education/{education_id}")
def delete_education(
        education_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление образования"""
    education = db.query(ResumeEducation).join(Resume).filter(
        ResumeEducation.id == education_id,
        Resume.user_id == current_user.id
    ).first()

    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Образование не найдено"
        )

    db.delete(education)
    db.commit()

    return {"message": "Образование удалено"}


# === ОПЫТ РАБОТЫ ===

@router.post("/{resume_id}/work-experience", response_model=ResumeWorkExperienceResponse)
def add_work_experience(
        resume_id: int,
        experience_data: ResumeWorkExperienceCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Добавление опыта работы к резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    experience = ResumeWorkExperience(
        resume_id=resume_id,
        **experience_data.dict()
    )

    db.add(experience)
    db.commit()
    db.refresh(experience)

    return experience


@router.get("/{resume_id}/work-experience", response_model=List[ResumeWorkExperienceResponse])
def get_resume_work_experience(
        resume_id: int,
        db: Session = Depends(get_db)
):
    """Получение опыта работы по резюме"""
    experience = db.query(ResumeWorkExperience).filter(
        ResumeWorkExperience.resume_id == resume_id
    ).order_by(desc(ResumeWorkExperience.start_date)).all()

    return experience


@router.put("/work-experience/{experience_id}", response_model=dict)
def update_work_experience(
        experience_id: int,
        experience_data: ResumeWorkExperienceUpdate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Обновление опыта работы"""
    experience = db.query(ResumeWorkExperience).join(Resume).filter(
        ResumeWorkExperience.id == experience_id,
        Resume.user_id == current_user.id
    ).first()

    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опыт работы не найден"
        )

    update_data = experience_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(experience, key):
            setattr(experience, key, value)

    db.commit()

    return {"message": "Опыт работы обновлен"}


@router.delete("/work-experience/{experience_id}")
def delete_work_experience(
        experience_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление опыта работы"""
    experience = db.query(ResumeWorkExperience).join(Resume).filter(
        ResumeWorkExperience.id == experience_id,
        Resume.user_id == current_user.id
    ).first()

    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опыт работы не найден"
        )

    db.delete(experience)
    db.commit()

    return {"message": "Опыт работы удален"}


# === НАВЫКИ ===

@router.post("/{resume_id}/skills", response_model=ResumeSkillResponse)
def add_skill_to_resume(
        resume_id: int,
        skill_data: ResumeSkillCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Добавление навыка к резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    # Проверяем, что навык существует
    skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Навык не найден"
        )

    # Проверяем, что навык еще не добавлен к резюме
    existing_skill = db.query(ResumeSkill).filter(
        ResumeSkill.resume_id == resume_id,
        ResumeSkill.skill_id == skill_data.skill_id
    ).first()

    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот навык уже добавлен к резюме"
        )

    resume_skill = ResumeSkill(
        resume_id=resume_id,
        **skill_data.dict()
    )

    db.add(resume_skill)
    db.commit()
    db.refresh(resume_skill)

    return resume_skill


@router.get("/{resume_id}/skills", response_model=List[ResumeSkillResponse])
def get_resume_skills(
        resume_id: int,
        db: Session = Depends(get_db)
):
    """Получение навыков по резюме"""
    skills = db.query(ResumeSkill).filter(
        ResumeSkill.resume_id == resume_id
    ).all()

    return skills


@router.delete("/skills/{skill_id}")
def delete_resume_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Удаление навыка из резюме"""
    resume_skill = db.query(ResumeSkill).join(Resume).filter(
        ResumeSkill.id == skill_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Навык не найден"
        )

    db.delete(resume_skill)
    db.commit()

    return {"message": "Навык удален из резюме"}


# === ПУБЛИКАЦИЯ И УПРАВЛЕНИЕ СТАТУСОМ ===

@router.post("/{resume_id}/publish")
def publish_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Публикация резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    resume.is_published = True
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме опубликовано"}


@router.post("/{resume_id}/unpublish")
def unpublish_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Снятие резюме с публикации"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    resume.is_published = False
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме снято с публикации"}


# === СОЗДАНИЕ ПОЛНОГО РЕЗЮМЕ ===

@router.post("/full", response_model=dict)
def create_full_resume(
        resume_data: ResumeFullCreate,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Создание полного резюме с образованием, опытом и навыками"""
    # Проверяем, что у пользователя нет активного резюме
    existing_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if existing_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть активное резюме"
        )

    try:
        # Создаем основное резюме
        resume = Resume(
            user_id=current_user.id,
            **resume_data.resume.dict()
        )
        db.add(resume)
        db.flush()  # Получаем ID резюме

        # Добавляем образование
        for edu_data in resume_data.education:
            education = ResumeEducation(
                resume_id=resume.id,
                **edu_data.dict()
            )
            db.add(education)

        # Добавляем опыт работы
        for exp_data in resume_data.work_experience:
            experience = ResumeWorkExperience(
                resume_id=resume.id,
                **exp_data.dict()
            )
            db.add(experience)

        # Добавляем навыки
        for skill_data in resume_data.skills:
            skill = ResumeSkill(
                resume_id=resume.id,
                **skill_data.dict()
            )
            db.add(skill)

        db.commit()

        return {
            "message": "Полное резюме успешно создано",
            "resume_id": resume.id,
            "education_count": len(resume_data.education),
            "experience_count": len(resume_data.work_experience),
            "skills_count": len(resume_data.skills)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании резюме: {str(e)}"
        )


# === СТАТИСТИКА ===

@router.get("/stats/user")
def get_user_resume_stats(
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Статистика резюме пользователя"""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()

    if not resume:
        return {
            "has_resume": False,
            "message": "У вас нет активного резюме"
        }

    education_count = db.query(func.count(ResumeEducation.id)).filter(
        ResumeEducation.resume_id == resume.id
    ).scalar()

    experience_count = db.query(func.count(ResumeWorkExperience.id)).filter(
        ResumeWorkExperience.resume_id == resume.id
    ).scalar()

    skills_count = db.query(func.count(ResumeSkill.id)).filter(
        ResumeSkill.resume_id == resume.id
    ).scalar()

    return {
        "has_resume": True,
        "resume_id": resume.id,
        "is_published": resume.is_published,
        "education_count": education_count,
        "experience_count": experience_count,
        "skills_count": skills_count,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at
    }


# === ПОИСК РЕЗЮМЕ ===

@router.get("/search")
def search_resumes(
        query: str,
        profession_id: Optional[int] = None,
        city_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Поиск резюме по ключевым словам"""
    search_query = db.query(Resume).filter(
        Resume.is_active == True,
        Resume.is_published == True
    )

    # Поиск по имени или описанию
    if query:
        search_query = search_query.filter(
            Resume.full_name.ilike(f"%{query}%") |
            Resume.about_me.ilike(f"%{query}%")
        )

    if profession_id:
        search_query = search_query.filter(Resume.profession_id == profession_id)

    if city_id:
        search_query = search_query.filter(Resume.city_id == city_id)

    resumes = search_query.order_by(desc(Resume.updated_at)).offset(skip).limit(limit).all()

    return {
        "query": query,
        "total_found": len(resumes),
        "resumes": [
            {
                "id": resume.id,
                "full_name": resume.full_name,
                "profession_id": resume.profession_id,
                "city_id": resume.city_id,
                "salary_expectation": resume.salary_expectation,
                "employment_type": resume.employment_type,
                "updated_at": resume.updated_at
            }
            for resume in resumes
        ]
    }




@router.post("/{resume_id}/activate")
def activate_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Активация резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    resume.is_active = True
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме активировано"}


@router.post("/{resume_id}/deactivate")
def deactivate_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        current_user: dict = Depends(oauth2.get_current_user)
):
    """Деактивация резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Резюме не найдено"
        )

    resume.is_active = False
    resume.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Резюме деактивировано"}





from sqlalchemy import func
from typing import Optional, List

from app import models, schemas,resume_models
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

@router.get("/professions/search",)
def search_professions(
        query: str = Query(..., min_length=1, description="Поисковый запрос"),
        language: str = Query("ru", regex="^(ru|kz)$", description="Приоритетный язык поиска (ru или kz)"),
        limit: int = Query(10, ge=1, le=100, description="Максимальное количество результатов"),
        db: Session = Depends(get_db)
):
    """
    Поиск профессий по названию с приоритетом языка

    - **query**: поисковый запрос (минимум 1 символ)
    - **language**: приоритетный язык поиска (ru или kz), по умолчанию ru
    - **limit**: максимальное количество результатов (1-100), по умолчанию 10

    Алгоритм поиска:
    1. Сначала ищет точные совпадения в приоритетном языке
    2. Затем ищет частичные совпадения в приоритетном языке
    3. После этого ищет во втором языке
    4. Возвращает уникальные результаты в порядке релевантности
    """

    # Приводим поисковый запрос к нижнему регистру для поиска без учета регистра
    search_term = query.lower().strip()

    # Определяем поля для поиска в зависимости от приоритетного языка
    if language == "ru":
        primary_field = Profession.name_ru
        secondary_field = Profession.name_kz
    else:  # kz
        primary_field = Profession.name_kz
        secondary_field = Profession.name_ru

    # Список для хранения результатов с сохранением порядка
    results = []
    found_ids = set()

    # 1. Точные совпадения в приоритетном языке
    exact_matches_primary = db.query(Profession).filter(
        Profession.is_active == True,
        func.lower(primary_field) == search_term
    ).all()

    for profession in exact_matches_primary:
        if profession.id not in found_ids:
            results.append(profession)
            found_ids.add(profession.id)

    # 2. Частичные совпадения в приоритетном языке (начинающиеся с поискового запроса)
    if len(results) < limit:
        partial_matches_primary = db.query(Profession).filter(
            Profession.is_active == True,
            func.lower(primary_field).like(f"{search_term}%"),
            Profession.id.notin_(found_ids) if found_ids else True
        ).limit(limit - len(results)).all()

        for profession in partial_matches_primary:
            if profession.id not in found_ids:
                results.append(profession)
                found_ids.add(profession.id)

    # 3. Содержащие поисковый запрос в приоритетном языке
    if len(results) < limit:
        contains_matches_primary = db.query(Profession).filter(
            Profession.is_active == True,
            func.lower(primary_field).contains(search_term),
            Profession.id.notin_(found_ids) if found_ids else True
        ).limit(limit - len(results)).all()

        for profession in contains_matches_primary:
            if profession.id not in found_ids:
                results.append(profession)
                found_ids.add(profession.id)

    # 4. Точные совпадения во втором языке
    if len(results) < limit:
        exact_matches_secondary = db.query(Profession).filter(
            Profession.is_active == True,
            func.lower(secondary_field) == search_term,
            Profession.id.notin_(found_ids) if found_ids else True
        ).limit(limit - len(results)).all()

        for profession in exact_matches_secondary:
            if profession.id not in found_ids:
                results.append(profession)
                found_ids.add(profession.id)

    # 5. Частичные совпадения во втором языке
    if len(results) < limit:
        partial_matches_secondary = db.query(Profession).filter(
            Profession.is_active == True,
            func.lower(secondary_field).like(f"{search_term}%"),
            Profession.id.notin_(found_ids) if found_ids else True
        ).limit(limit - len(results)).all()

        for profession in partial_matches_secondary:
            if profession.id not in found_ids:
                results.append(profession)
                found_ids.add(profession.id)

    # 6. Содержащие поисковый запрос во втором языке
    if len(results) < limit:
        contains_matches_secondary = db.query(Profession).filter(
            Profession.is_active == True,
            func.lower(secondary_field).contains(search_term),
            Profession.id.notin_(found_ids) if found_ids else True
        ).limit(limit - len(results)).all()

        for profession in contains_matches_secondary:
            if profession.id not in found_ids:
                results.append(profession)
                found_ids.add(profession.id)

    # Ограничиваем количество результатов
    return results[:limit]