# Example: How to integrate RBAC into vacancies.py
# Copy and paste the relevant parts into your actual route file

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.rbac import Module, Permission, require_permission, require_module_access
from app import models, schemas

router = APIRouter(prefix="/api/vacancies", tags=["Vacancies"])


# ============================================================
# READ ROUTES - Allow read-only access
# ============================================================

@router.get("/")
def get_all_vacancies(
    skip: int = 0,
    limit: int = 100,
    admin = Depends(require_module_access(Module.VACANCIES, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get all vacancies
    - Accessible by: msb, administrator, super_admin, government (read-only)
    """
    vacancies = db.query(models.Vacancy).offset(skip).limit(limit).all()
    return vacancies


@router.get("/{vacancy_id}")
def get_vacancy_by_id(
    vacancy_id: int,
    admin = Depends(require_module_access(Module.VACANCIES, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get vacancy by ID
    - Accessible by: msb, administrator, super_admin, government (read-only)
    """
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()

    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    return vacancy


# ============================================================
# CREATE ROUTES - Require create permission
# ============================================================

@router.post("/")
def create_vacancy(
    vacancy_data: schemas.VacancyCreate,
    admin = Depends(require_permission(Module.VACANCIES, Permission.CREATE)),
    db: Session = Depends(get_db)
):
    """
    Create new vacancy
    - Accessible by: msb, administrator, super_admin
    - Blocked for: government (read-only), npo, volunteer_admin
    """
    new_vacancy = models.Vacancy(**vacancy_data.dict())
    db.add(new_vacancy)
    db.commit()
    db.refresh(new_vacancy)

    return new_vacancy


# ============================================================
# UPDATE ROUTES - Require update permission
# ============================================================

@router.put("/{vacancy_id}")
def update_vacancy(
    vacancy_id: int,
    vacancy_data: schemas.VacancyUpdate,
    admin = Depends(require_permission(Module.VACANCIES, Permission.UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Update vacancy
    - Accessible by: msb, administrator, super_admin
    """
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()

    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    for key, value in vacancy_data.dict(exclude_unset=True).items():
        setattr(vacancy, key, value)

    db.commit()
    db.refresh(vacancy)

    return vacancy


# ============================================================
# DELETE ROUTES - Require delete permission
# ============================================================

@router.delete("/{vacancy_id}")
def delete_vacancy(
    vacancy_id: int,
    admin = Depends(require_permission(Module.VACANCIES, Permission.DELETE)),
    db: Session = Depends(get_db)
):
    """
    Delete vacancy
    - Accessible by: msb, administrator, super_admin
    """
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()

    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    db.delete(vacancy)
    db.commit()

    return {"message": "Вакансия удалена"}
