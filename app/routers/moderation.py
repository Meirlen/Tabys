from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app import models
from app.project_models import Project
from app.leisure_models import Place, Ticket, PromoAction
from app.oauth2 import get_current_admin
from app.rbac import require_module_access, Module
from app.schemas import ModerationStats

router = APIRouter(prefix="/api/v1/moderation", tags=["Unified Moderation"])


class ModerationItem(BaseModel):
    """Unified moderation item across all entities"""
    id: int
    entity_type: str  # 'event', 'vacancy', 'course', 'project', 'place', 'ticket', 'promo'
    title: str
    description: Optional[str] = None
    moderation_status: str
    created_at: datetime
    admin_id: Optional[int] = None

    class Config:
        from_attributes = True


class UnifiedStats(BaseModel):
    """Statistics across all entities"""
    events: ModerationStats
    vacancies: ModerationStats
    courses: ModerationStats
    projects: ModerationStats
    places: ModerationStats
    tickets: ModerationStats
    promo_actions: ModerationStats
    total_pending: int


@router.get("/stats", response_model=UnifiedStats)
def get_unified_moderation_stats(
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(get_current_admin)
):
    """
    Get unified moderation statistics across all entities.
    Requires admin authentication.
    """
    def get_stats(model_class):
        total = db.query(model_class).count()
        pending = db.query(model_class).filter(model_class.moderation_status == 'pending').count()
        approved = db.query(model_class).filter(model_class.moderation_status == 'approved').count()
        rejected = db.query(model_class).filter(model_class.moderation_status == 'rejected').count()
        return ModerationStats(total=total, pending=pending, approved=approved, rejected=rejected)

    events_stats = get_stats(models.Event)
    vacancies_stats = get_stats(models.Vacancy)
    courses_stats = get_stats(models.Course)
    projects_stats = get_stats(Project)
    places_stats = get_stats(Place)
    tickets_stats = get_stats(Ticket)
    promo_stats = get_stats(PromoAction)

    total_pending = (
        events_stats.pending +
        vacancies_stats.pending +
        courses_stats.pending +
        projects_stats.pending +
        places_stats.pending +
        tickets_stats.pending +
        promo_stats.pending
    )

    return UnifiedStats(
        events=events_stats,
        vacancies=vacancies_stats,
        courses=courses_stats,
        projects=projects_stats,
        places=places_stats,
        tickets=tickets_stats,
        promo_actions=promo_stats,
        total_pending=total_pending
    )


@router.get("/queue", response_model=List[ModerationItem])
def get_unified_moderation_queue(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: event, vacancy, course, project, place, ticket, promo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(get_current_admin)
):
    """
    Get unified moderation queue showing pending items from all entities.
    Returns all pending items sorted by creation date (newest first).
    """
    items = []

    def to_item(obj, type_name):
        """Convert database object to ModerationItem"""
        # Get title - different entities have different field names
        if hasattr(obj, 'title'):
            title = obj.title
        elif hasattr(obj, 'title_kz'):
            title = obj.title_kz or obj.title_ru if hasattr(obj, 'title_ru') else ''
        elif hasattr(obj, 'profession'):
            title = obj.profession or 'Unnamed Vacancy'
        else:
            title = f'{type_name.capitalize()} #{obj.id}'

        # Get description
        if hasattr(obj, 'description'):
            desc = obj.description
        elif hasattr(obj, 'description_kz'):
            desc = obj.description_kz or obj.description_ru if hasattr(obj, 'description_ru') else None
        else:
            desc = None

        return ModerationItem(
            id=obj.id,
            entity_type=type_name,
            title=title,
            description=desc[:200] if desc else None,
            moderation_status=obj.moderation_status,
            created_at=obj.created_at,
            admin_id=getattr(obj, 'admin_id', None)
        )

    # Query each entity type
    if not entity_type or entity_type == 'event':
        events = db.query(models.Event).filter(
            models.Event.moderation_status == 'pending'
        ).all()
        items.extend([to_item(e, 'event') for e in events])

    if not entity_type or entity_type == 'vacancy':
        vacancies = db.query(models.Vacancy).filter(
            models.Vacancy.moderation_status == 'pending'
        ).all()
        items.extend([to_item(v, 'vacancy') for v in vacancies])

    if not entity_type or entity_type == 'course':
        courses = db.query(models.Course).filter(
            models.Course.moderation_status == 'pending'
        ).all()
        items.extend([to_item(c, 'course') for c in courses])

    if not entity_type or entity_type == 'project':
        projects = db.query(Project).filter(
            Project.moderation_status == 'pending'
        ).all()
        items.extend([to_item(p, 'project') for p in projects])

    if not entity_type or entity_type == 'place':
        places = db.query(Place).filter(
            Place.moderation_status == 'pending'
        ).all()
        items.extend([to_item(pl, 'place') for pl in places])

    if not entity_type or entity_type == 'ticket':
        tickets = db.query(Ticket).filter(
            Ticket.moderation_status == 'pending'
        ).all()
        items.extend([to_item(t, 'ticket') for t in tickets])

    if not entity_type or entity_type == 'promo':
        promos = db.query(PromoAction).filter(
            PromoAction.moderation_status == 'pending'
        ).all()
        items.extend([to_item(pr, 'promo') for pr in promos])

    # Sort by created_at descending (newest first)
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Apply pagination
    return items[skip:skip+limit]


@router.get("/recent", response_model=List[ModerationItem])
def get_recent_moderated_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(get_current_admin)
):
    """
    Get recently moderated items (approved or rejected).
    Shows items that have been moderated in the last 30 days.
    """
    items = []

    def to_item(obj, type_name):
        """Convert database object to ModerationItem"""
        if hasattr(obj, 'title'):
            title = obj.title
        elif hasattr(obj, 'title_kz'):
            title = obj.title_kz or obj.title_ru if hasattr(obj, 'title_ru') else ''
        elif hasattr(obj, 'profession'):
            title = obj.profession or 'Unnamed Vacancy'
        else:
            title = f'{type_name.capitalize()} #{obj.id}'

        if hasattr(obj, 'description'):
            desc = obj.description
        elif hasattr(obj, 'description_kz'):
            desc = obj.description_kz or obj.description_ru if hasattr(obj, 'description_ru') else None
        else:
            desc = None

        return ModerationItem(
            id=obj.id,
            entity_type=type_name,
            title=title,
            description=desc[:200] if desc else None,
            moderation_status=obj.moderation_status,
            created_at=obj.created_at,
            admin_id=getattr(obj, 'admin_id', None)
        )

    # Query moderated items from each entity
    for model_class, type_name in [
        (models.Event, 'event'),
        (models.Vacancy, 'vacancy'),
        (models.Course, 'course'),
        (Project, 'project'),
        (Place, 'place'),
        (Ticket, 'ticket'),
        (PromoAction, 'promo')
    ]:
        moderated = db.query(model_class).filter(
            model_class.moderation_status.in_(['approved', 'rejected']),
            model_class.moderated_at != None
        ).order_by(model_class.moderated_at.desc()).limit(limit).all()

        items.extend([to_item(obj, type_name) for obj in moderated])

    # Sort by moderated_at descending
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Apply pagination
    return items[skip:skip+limit]
