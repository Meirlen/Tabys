# Example: How to integrate RBAC into volunteer_admin_routes.py
# Copy and paste the relevant parts into your actual route file

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.rbac import Module, Permission, require_permission, require_module_access
from app import models, schemas

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers Admin"])


# ============================================================
# READ ROUTES - Allow read-only access (Government can view)
# ============================================================

@router.get("/")
def get_all_volunteers(
    skip: int = 0,
    limit: int = 100,
    admin = Depends(require_module_access(Module.VOLUNTEERS, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get all volunteers
    - Accessible by: volunteer_admin, administrator, super_admin, government (read-only)
    """
    volunteers = db.query(models.Volunteer).offset(skip).limit(limit).all()
    return volunteers


@router.get("/{volunteer_id}")
def get_volunteer_by_id(
    volunteer_id: int,
    admin = Depends(require_module_access(Module.VOLUNTEERS, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get volunteer by ID
    - Accessible by: volunteer_admin, administrator, super_admin, government (read-only)
    """
    volunteer = db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    return volunteer


# ============================================================
# CREATE ROUTES - Require create permission
# ============================================================

@router.post("/")
def create_volunteer(
    volunteer_data: schemas.VolunteerCreate,
    admin = Depends(require_permission(Module.VOLUNTEERS, Permission.CREATE)),
    db: Session = Depends(get_db)
):
    """
    Create new volunteer
    - Accessible by: volunteer_admin, administrator, super_admin
    - Blocked for: government (read-only)
    """
    new_volunteer = models.Volunteer(**volunteer_data.dict())
    db.add(new_volunteer)
    db.commit()
    db.refresh(new_volunteer)

    return new_volunteer


# ============================================================
# UPDATE ROUTES - Require update permission
# ============================================================

@router.put("/{volunteer_id}")
def update_volunteer(
    volunteer_id: int,
    volunteer_data: schemas.VolunteerUpdate,
    admin = Depends(require_permission(Module.VOLUNTEERS, Permission.UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Update volunteer
    - Accessible by: volunteer_admin, administrator, super_admin
    - Blocked for: government (read-only)
    """
    volunteer = db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    for key, value in volunteer_data.dict(exclude_unset=True).items():
        setattr(volunteer, key, value)

    db.commit()
    db.refresh(volunteer)

    return volunteer


@router.patch("/{volunteer_id}/status")
def update_volunteer_status(
    volunteer_id: int,
    status: str,
    admin = Depends(require_permission(Module.VOLUNTEERS, Permission.UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Update volunteer status
    - Accessible by: volunteer_admin, administrator, super_admin
    """
    volunteer = db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    volunteer.status = status
    db.commit()

    return {"message": "Статус обновлен", "status": status}


# ============================================================
# DELETE ROUTES - Require delete permission
# ============================================================

@router.delete("/{volunteer_id}")
def delete_volunteer(
    volunteer_id: int,
    admin = Depends(require_permission(Module.VOLUNTEERS, Permission.DELETE)),
    db: Session = Depends(get_db)
):
    """
    Delete volunteer
    - Accessible by: volunteer_admin, administrator, super_admin
    - Blocked for: government (read-only)
    """
    volunteer = db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    db.delete(volunteer)
    db.commit()

    return {"message": "Волонтер удален"}


# ============================================================
# CONDITIONAL LOGIC EXAMPLE
# ============================================================

from app.rbac import check_admin_permission

@router.get("/{volunteer_id}/details")
def get_volunteer_details(
    volunteer_id: int,
    admin = Depends(require_module_access(Module.VOLUNTEERS, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get volunteer details with conditional data hiding
    - If user has no edit permission, hide sensitive data
    """
    volunteer = db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()

    if not volunteer:
        raise HTTPException(status_code=404, detail="Волонтер не найден")

    # Hide sensitive data for read-only users
    if not check_admin_permission(admin, Module.VOLUNTEERS, Permission.UPDATE):
        volunteer_dict = volunteer.__dict__.copy()
        volunteer_dict['phone'] = "***"
        volunteer_dict['email'] = "***"
        volunteer_dict['address'] = "***"
        return volunteer_dict

    return volunteer
