# Example: How to integrate RBAC into projects.py
# Copy and paste the relevant parts into your actual route file

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.rbac import Module, Permission, require_permission, require_module_access
from app import models, schemas

router = APIRouter(prefix="/api/projects", tags=["Projects"])


# ============================================================
# READ ROUTES - Allow read-only access
# ============================================================

@router.get("/")
def get_all_projects(
    skip: int = 0,
    limit: int = 100,
    admin = Depends(require_module_access(Module.PROJECTS, allow_read_only=True)),
    db: Session = Depends(get_db)
):
    """
    Get all projects
    - Accessible by: npo, administrator, super_admin, government (read-only)
    """
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects


# ============================================================
# CREATE ROUTES - Require create permission
# ============================================================

@router.post("/")
def create_project(
    project_data: schemas.ProjectCreate,
    admin = Depends(require_permission(Module.PROJECTS, Permission.CREATE)),
    db: Session = Depends(get_db)
):
    """
    Create new project
    - Accessible by: npo, administrator, super_admin
    - Blocked for: government (read-only), msb, volunteer_admin
    """
    new_project = models.Project(**project_data.dict())
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project


# ============================================================
# UPDATE ROUTES - Require update permission
# ============================================================

@router.put("/{project_id}")
def update_project(
    project_id: int,
    project_data: schemas.ProjectUpdate,
    admin = Depends(require_permission(Module.PROJECTS, Permission.UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Update project
    - Accessible by: npo, administrator, super_admin
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    for key, value in project_data.dict(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    return project


# ============================================================
# DELETE ROUTES - Require delete permission
# ============================================================

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    admin = Depends(require_permission(Module.PROJECTS, Permission.DELETE)),
    db: Session = Depends(get_db)
):
    """
    Delete project
    - Accessible by: npo, administrator, super_admin
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    db.delete(project)
    db.commit()

    return {"message": "Проект удален"}
