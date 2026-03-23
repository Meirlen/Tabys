import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app import crud
from app import tech_task_models, tech_task_schemas
from app.oauth2 import get_current_user, get_current_admin
from app.rbac import Module, Permission, require_module_access, require_permission

router = APIRouter(prefix="/api/v2/tech-tasks", tags=["Tech Tasks"])

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "zip", "rar"}


# ── Public / User Endpoints ───────────────────────────────────────────────────

@router.get("/")
def list_tech_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    preferred_technology: Optional[str] = Query(None),
    field_of_application: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    lang: Optional[str] = Query("ru"),
    db: Session = Depends(get_db),
):
    return crud.get_tech_tasks_filtered(
        db,
        skip=skip,
        limit=limit,
        status=status,
        category=category,
        preferred_technology=preferred_technology,
        field_of_application=field_of_application,
        keyword=keyword,
        lang=lang,
    )


@router.get("/my-tasks")
def get_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_user_tech_tasks(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/my-solutions")
def get_my_solutions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_user_solutions(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{task_id}")
def get_tech_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_tech_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_tech_task(
    task_data: tech_task_schemas.TechTaskCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_tech_task(db, task_data=task_data, user_id=current_user.id)


@router.post("/{task_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_task_file(
    task_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task or not task.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only task owner can upload files")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    upload_dir = f"uploads/tech_tasks/{task_id}/files"
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return crud.create_task_file(
        db,
        task_id=task_id,
        file_path=f"/{file_path}",
        original_name=file.filename,
    )


@router.put("/{task_id}")
def update_tech_task(
    task_id: int,
    task_data: tech_task_schemas.TechTaskUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return crud.update_tech_task(db, task_id=task_id, task_data=task_data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tech_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    crud.delete_tech_task(db, task_id)


# ── Solutions ─────────────────────────────────────────────────────────────────

@router.get("/{task_id}/solutions")
def get_task_solutions(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    solutions = crud.get_tech_task_solutions(db, task_id=task_id, skip=skip, limit=limit)

    # Non-owners only see their own solutions
    if task.user_id != current_user.id:
        solutions = [s for s in solutions if s["user_id"] == current_user.id]

    return solutions


@router.post("/{task_id}/solutions", status_code=status.HTTP_201_CREATED)
def submit_solution(
    task_id: int,
    solution_data: tech_task_schemas.TechTaskSolutionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task or not task.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit solution to your own task",
        )
    if task.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already completed",
        )
    return crud.create_tech_task_solution(
        db, solution_data=solution_data, task_id=task_id, user_id=current_user.id
    )


@router.post("/{task_id}/solutions/{solution_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_solution_file(
    task_id: int,
    solution_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    solution = db.query(tech_task_models.TechTaskSolution).filter(
        tech_task_models.TechTaskSolution.id == solution_id,
        tech_task_models.TechTaskSolution.tech_task_id == task_id,
    ).first()
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")
    if solution.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    upload_dir = f"uploads/tech_tasks/solutions/{solution_id}"
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    file_record = crud.create_solution_file(
        db,
        solution_id=solution_id,
        file_path=f"/{file_path}",
        original_name=file.filename,
    )
    return file_record


@router.put("/{task_id}/solutions/{solution_id}/accept")
def accept_solution(
    task_id: int,
    solution_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only task owner can accept solutions")

    solution = db.query(tech_task_models.TechTaskSolution).filter(
        tech_task_models.TechTaskSolution.id == solution_id,
        tech_task_models.TechTaskSolution.tech_task_id == task_id,
    ).first()
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")

    updated = crud.update_solution_status(db, solution_id=solution_id, status="accepted")
    # Mark task as completed
    crud.update_tech_task(
        db, task_id=task_id, task_data=tech_task_schemas.TechTaskUpdate(status="completed")
    )
    return updated


@router.put("/{task_id}/solutions/{solution_id}/reject")
def reject_solution(
    task_id: int,
    solution_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only task owner can reject solutions")

    solution = db.query(tech_task_models.TechTaskSolution).filter(
        tech_task_models.TechTaskSolution.id == solution_id,
        tech_task_models.TechTaskSolution.tech_task_id == task_id,
    ).first()
    if not solution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found")

    return crud.update_solution_status(db, solution_id=solution_id, status="rejected")


# ── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/list")
def admin_list_tech_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_admin=Depends(require_module_access(Module.TECH_TASKS, allow_read_only=True)),
    db: Session = Depends(get_db),
):
    query = db.query(tech_task_models.TechTask)
    if status:
        query = query.filter(tech_task_models.TechTask.status == status)
    if category:
        query = query.filter(tech_task_models.TechTask.category == category)
    total = query.count()
    tasks = query.order_by(tech_task_models.TechTask.created_at.desc()).offset(skip).limit(limit).all()
    return {"tasks": [
        {**{c.name: getattr(t, c.name) for c in t.__table__.columns}} for t in tasks
    ], "total": total}


@router.get("/admin/{task_id}")
def admin_get_tech_task(
    task_id: int,
    current_admin=Depends(require_module_access(Module.TECH_TASKS, allow_read_only=True)),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    solutions = crud.get_tech_task_solutions(db, task_id=task_id)
    task_dict = {c.name: getattr(task, c.name) for c in task.__table__.columns}
    task_dict["solutions"] = solutions
    return task_dict


@router.delete("/admin/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_tech_task(
    task_id: int,
    current_admin=Depends(require_permission(Module.TECH_TASKS, Permission.DELETE)),
    db: Session = Depends(get_db),
):
    task = crud.get_tech_task_admin(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
