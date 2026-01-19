from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from app.database import get_db
from app.leisure_models import (
    LeisureCategory, Ticket, TicketGallery,
    Place, PlaceGallery, PromoAction
)
from app.schemas import ModerationStats, ModerationStatus
from app.oauth2 import get_current_admin
from app.rbac import Module, Permission, require_module_access, require_permission, apply_owner_filter
from app import models
from typing import List, Optional
import os
import uuid
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v2/leisure", tags=["Досуг"])

BASE_URL = "https://api.saryarqa-jastary.kz"


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_full_url(path: Optional[str]) -> Optional[str]:
    """Формирует полный URL"""
    if not path:
        return None
    if path.startswith('http'):
        return path
    return f"{BASE_URL}{path}"


async def save_uploaded_file(file: UploadFile, folder: str) -> str:
    """Сохранение файла"""
    upload_dir = f"uploads/{folder}"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return f"/{file_path}"


# ========================================
# КАТЕГОРИИ
# ========================================

@router.post("/categories")
async def create_category(
        name: str = Form(...),
        name_ru: str = Form(...),
        icon: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Создание категории"""
    icon_url = None
    if icon:
        icon_url = await save_uploaded_file(icon, "categories")

    category = LeisureCategory(
        name=name,
        name_ru=name_ru,
        icon_url=icon_url
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "message": "Категория создана",
        "id": category.id,
        "name": category.name,
        "name_ru": category.name_ru,
        "icon_url": get_full_url(category.icon_url)
    }


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Получить все категории"""
    categories = db.query(LeisureCategory).order_by(LeisureCategory.name).all()

    return [
        {
            "id": cat.id,
            "name": cat.name,
            "name_ru": cat.name_ru,
            "icon_url": get_full_url(cat.icon_url)
        }
        for cat in categories
    ]


@router.put("/categories/{category_id}")
async def update_category(
        category_id: int,
        name: Optional[str] = Form(None),
        name_ru: Optional[str] = Form(None),
        icon: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Обновить категорию"""
    category = db.query(LeisureCategory).filter(LeisureCategory.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    if name:
        category.name = name
    if name_ru:
        category.name_ru = name_ru
    if icon:
        category.icon_url = await save_uploaded_file(icon, "categories")

    db.commit()
    return {"message": "Категория обновлена"}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Удалить категорию"""
    category = db.query(LeisureCategory).filter(LeisureCategory.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    db.delete(category)
    db.commit()
    return {"message": "Категория удалена"}


# ========================================
# БИЛЕТЫ (СОБЫТИЯ)
# ========================================

@router.post("/tickets")
async def create_ticket(
        title: str = Form(...),
        title_ru: str = Form(...),
        description: str = Form(...),
        description_ru: str = Form(...),
        event_date: str = Form(...),  # ISO формат
        address: str = Form(...),
        price: str = Form(None),
        address_link: str = Form(None),
        instagram_url: str = Form(None),
        tiktok_url: str = Form(None),
        whatsapp_number: str = Form(None),
        main_photo: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Создание билета на событие"""
    photo_url = None
    if main_photo:
        photo_url = await save_uploaded_file(main_photo, "tickets")

    ticket = Ticket(
        title=title,
        title_ru=title_ru,
        description=description,
        description_ru=description_ru,
        event_date=datetime.fromisoformat(event_date),
        address=address,
        price=price,
        main_photo_url=photo_url,
        address_link=address_link,
        instagram_url=instagram_url,
        tiktok_url=tiktok_url,
        whatsapp_number=whatsapp_number
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "message": "Билет создан",
        "id": ticket.id,
        "title": ticket.title
    }


@router.get("/tickets")
def get_tickets(
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Получить список билетов"""
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)

    tickets = query.order_by(Ticket.event_date).offset(skip).limit(limit).all()

    result = []
    for ticket in tickets:
        gallery_count = db.query(func.count(TicketGallery.id)).filter(
            TicketGallery.ticket_id == ticket.id
        ).scalar()

        result.append({
            "id": ticket.id,
            "title": ticket.title,
            "title_ru": ticket.title_ru,
            "description": ticket.description,
            "description_ru": ticket.description_ru,
            "event_date": ticket.event_date,
            "address": ticket.address,
            "price": ticket.price,
            "main_photo_url": get_full_url(ticket.main_photo_url),
            "address_link": ticket.address_link,
            "instagram_url": ticket.instagram_url,
            "tiktok_url": ticket.tiktok_url,
            "whatsapp_number": ticket.whatsapp_number,
            "status": ticket.status,
            "gallery_count": gallery_count,
            "created_at": ticket.created_at
        })

    return result


@router.get("/tickets/{ticket_id}")
def get_ticket_detail(ticket_id: int, db: Session = Depends(get_db)):
    """Получить детальную информацию о билете"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    gallery = db.query(TicketGallery).filter(
        TicketGallery.ticket_id == ticket_id
    ).all()

    # Проверяем есть ли активные промо-акции
    now = datetime.utcnow()
    promo = db.query(PromoAction).filter(
        PromoAction.related_type == "ticket",
        PromoAction.related_id == ticket_id,
        PromoAction.status == "active",
        PromoAction.start_date <= now,
        PromoAction.end_date >= now
    ).first()

    return {
        "id": ticket.id,
        "title": ticket.title,
        "title_ru": ticket.title_ru,
        "description": ticket.description,
        "description_ru": ticket.description_ru,
        "event_date": ticket.event_date,
        "address": ticket.address,
        "price": ticket.price,
        "main_photo_url": get_full_url(ticket.main_photo_url),
        "address_link": ticket.address_link,
        "instagram_url": ticket.instagram_url,
        "tiktok_url": ticket.tiktok_url,
        "whatsapp_number": ticket.whatsapp_number,
        "status": ticket.status,
        "gallery": [
            {
                "id": img.id,
                "image_url": get_full_url(img.image_url),
                "description": img.description
            }
            for img in gallery
        ],
        "promo": {
            "id": promo.id,
            "title": promo.title,
            "title_ru": promo.title_ru,
            "description": promo.description,
            "discount_text": promo.discount_text,
            "promo_code": promo.promo_code,
            "end_date": promo.end_date
        } if promo else None
    }


@router.put("/tickets/{ticket_id}")
async def update_ticket(
        ticket_id: int,
        title: Optional[str] = Form(None),
        title_ru: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        description_ru: Optional[str] = Form(None),
        event_date: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        price: Optional[str] = Form(None),
        address_link: Optional[str] = Form(None),
        instagram_url: Optional[str] = Form(None),
        tiktok_url: Optional[str] = Form(None),
        whatsapp_number: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        main_photo: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Обновить билет"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    if title:
        ticket.title = title
    if title_ru:
        ticket.title_ru = title_ru
    if description:
        ticket.description = description
    if description_ru:
        ticket.description_ru = description_ru
    if event_date:
        ticket.event_date = datetime.fromisoformat(event_date)
    if address:
        ticket.address = address
    if price:
        ticket.price = price
    if address_link:
        ticket.address_link = address_link
    if instagram_url:
        ticket.instagram_url = instagram_url
    if tiktok_url:
        ticket.tiktok_url = tiktok_url
    if whatsapp_number:
        ticket.whatsapp_number = whatsapp_number
    if status:
        ticket.status = status
    if main_photo:
        ticket.main_photo_url = await save_uploaded_file(main_photo, "tickets")

    db.commit()
    return {"message": "Билет обновлен"}


@router.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Удалить билет"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    # Удаляем галерею
    db.query(TicketGallery).filter(TicketGallery.ticket_id == ticket_id).delete()

    # Удаляем промо
    db.query(PromoAction).filter(
        PromoAction.related_type == "ticket",
        PromoAction.related_id == ticket_id
    ).delete()

    db.delete(ticket)
    db.commit()
    return {"message": "Билет удален"}


# === ГАЛЕРЕЯ ДЛЯ БИЛЕТОВ ===

@router.post("/tickets/{ticket_id}/gallery")
async def add_ticket_gallery(
        ticket_id: int,
        image: UploadFile = File(...),
        description: str = Form(None),
        db: Session = Depends(get_db)
):
    """Добавить фото в галерею билета"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден")

    image_url = await save_uploaded_file(image, "ticket_gallery")

    gallery_item = TicketGallery(
        ticket_id=ticket_id,
        image_url=image_url,
        description=description
    )

    db.add(gallery_item)
    db.commit()
    db.refresh(gallery_item)

    return {
        "message": "Фото добавлено",
        "id": gallery_item.id,
        "image_url": get_full_url(gallery_item.image_url)
    }


@router.delete("/tickets/gallery/{gallery_id}")
def delete_ticket_gallery(gallery_id: int, db: Session = Depends(get_db)):
    """Удалить фото из галереи"""
    gallery_item = db.query(TicketGallery).filter(TicketGallery.id == gallery_id).first()

    if not gallery_item:
        raise HTTPException(status_code=404, detail="Фото не найдено")

    db.delete(gallery_item)
    db.commit()
    return {"message": "Фото удалено"}


# ========================================
# МЕСТА
# ========================================

@router.post("/places")
async def create_place(
        title: str = Form(...),
        title_ru: str = Form(...),
        description: str = Form(...),
        description_ru: str = Form(...),
        address: str = Form(...),
        category_id: int = Form(None),
        event_date: str = Form(None),
        price: str = Form(None),
        address_link: str = Form(None),
        instagram_url: str = Form(None),
        tiktok_url: str = Form(None),
        whatsapp_number: str = Form(None),
        main_photo: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Создание места"""
    photo_url = None
    if main_photo:
        photo_url = await save_uploaded_file(main_photo, "places")

    place = Place(
        title=title,
        title_ru=title_ru,
        description=description,
        description_ru=description_ru,
        category_id=category_id,
        event_date=datetime.fromisoformat(event_date) if event_date else None,
        address=address,
        price=price,
        main_photo_url=photo_url,
        address_link=address_link,
        instagram_url=instagram_url,
        tiktok_url=tiktok_url,
        whatsapp_number=whatsapp_number
    )

    db.add(place)
    db.commit()
    db.refresh(place)

    return {
        "message": "Место создано",
        "id": place.id,
        "title": place.title
    }


@router.get("/places")
def get_places(
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Получить список мест"""
    query = db.query(Place)

    if category_id:
        query = query.filter(Place.category_id == category_id)

    if status:
        query = query.filter(Place.status == status)

    places = query.order_by(desc(Place.rating), desc(Place.views_count)).offset(skip).limit(limit).all()

    result = []
    for place in places:
        gallery_count = db.query(func.count(PlaceGallery.id)).filter(
            PlaceGallery.place_id == place.id
        ).scalar()

        category = None
        if place.category_id:
            cat = db.query(LeisureCategory).filter(LeisureCategory.id == place.category_id).first()
            if cat:
                category = {"id": cat.id, "name": cat.name, "name_ru": cat.name_ru}

        result.append({
            "id": place.id,
            "title": place.title,
            "title_ru": place.title_ru,
            "description": place.description,
            "description_ru": place.description_ru,
            "category": category,
            "event_date": place.event_date,
            "address": place.address,
            "price": place.price,
            "main_photo_url": get_full_url(place.main_photo_url),
            "address_link": place.address_link,
            "instagram_url": place.instagram_url,
            "tiktok_url": place.tiktok_url,
            "whatsapp_number": place.whatsapp_number,
            "rating": float(place.rating),
            "views_count": place.views_count,
            "status": place.status,
            "gallery_count": gallery_count,
            "created_at": place.created_at
        })

    return result


@router.get("/places/{place_id}")
def get_place_detail(place_id: int, db: Session = Depends(get_db)):
    """Получить детальную информацию о месте"""
    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено")

    # Увеличиваем счетчик просмотров
    place.views_count += 1
    db.commit()

    gallery = db.query(PlaceGallery).filter(
        PlaceGallery.place_id == place_id
    ).all()

    category = None
    if place.category_id:
        cat = db.query(LeisureCategory).filter(LeisureCategory.id == place.category_id).first()
        if cat:
            category = {"id": cat.id, "name": cat.name, "name_ru": cat.name_ru}

    # Проверяем промо-акции
    now = datetime.utcnow()
    promo = db.query(PromoAction).filter(
        PromoAction.related_type == "place",
        PromoAction.related_id == place_id,
        PromoAction.status == "active",
        PromoAction.start_date <= now,
        PromoAction.end_date >= now
    ).first()

    return {
        "id": place.id,
        "title": place.title,
        "title_ru": place.title_ru,
        "description": place.description,
        "description_ru": place.description_ru,
        "category": category,
        "event_date": place.event_date,
        "address": place.address,
        "price": place.price,
        "main_photo_url": get_full_url(place.main_photo_url),
        "address_link": place.address_link,
        "instagram_url": place.instagram_url,
        "tiktok_url": place.tiktok_url,
        "whatsapp_number": place.whatsapp_number,
        "rating": float(place.rating),
        "views_count": place.views_count,
        "status": place.status,
        "gallery": [
            {
                "id": img.id,
                "image_url": get_full_url(img.image_url),
                "description": img.description
            }
            for img in gallery
        ],
        "promo": {
            "id": promo.id,
            "title": promo.title,
            "title_ru": promo.title_ru,
            "description": promo.description,
            "discount_text": promo.discount_text,
            "promo_code": promo.promo_code,
            "end_date": promo.end_date
        } if promo else None
    }


@router.put("/places/{place_id}")
async def update_place(
        place_id: int,
        title: Optional[str] = Form(None),
        title_ru: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        description_ru: Optional[str] = Form(None),
        category_id: Optional[int] = Form(None),
        event_date: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        price: Optional[str] = Form(None),
        address_link: Optional[str] = Form(None),
        instagram_url: Optional[str] = Form(None),
        tiktok_url: Optional[str] = Form(None),
        whatsapp_number: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        rating: Optional[float] = Form(None),
        main_photo: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Обновить место"""
    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено")

    if title:
        place.title = title
    if title_ru:
        place.title_ru = title_ru
    if description:
        place.description = description
    if description_ru:
        place.description_ru = description_ru
    if category_id is not None:
        place.category_id = category_id
    if event_date:
        place.event_date = datetime.fromisoformat(event_date)
    if address:
        place.address = address
    if price:
        place.price = price
    if address_link:
        place.address_link = address_link
    if instagram_url:
        place.instagram_url = instagram_url
    if tiktok_url:
        place.tiktok_url = tiktok_url
    if whatsapp_number:
        place.whatsapp_number = whatsapp_number
    if status:
        place.status = status
    if rating is not None:
        place.rating = rating
    if main_photo:
        place.main_photo_url = await save_uploaded_file(main_photo, "places")

    # await save_uploaded_file(main_photo, "places")

    db.commit()
    return {"message": "Место обновлено"}


@router.delete("/places/{place_id}")
def delete_place(place_id: int, db: Session = Depends(get_db)):
    """Удалить место"""
    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено")

    # Удаляем галерею
    db.query(PlaceGallery).filter(PlaceGallery.place_id == place_id).delete()

    # Удаляем промо
    db.query(PromoAction).filter(
        PromoAction.related_type == "place",
        PromoAction.related_id == place_id
    ).delete()

    db.delete(place)
    db.commit()
    return {"message": "Место удалено"}


# === ГАЛЕРЕЯ ДЛЯ МЕСТ ===

@router.post("/places/{place_id}/gallery")
async def add_place_gallery(
        place_id: int,
        image: UploadFile = File(...),
        description: str = Form(None),
        db: Session = Depends(get_db)
):
    """Добавить фото в галерею места"""
    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено")

    image_url = await save_uploaded_file(image, "place_gallery")

    gallery_item = PlaceGallery(
        place_id=place_id,
        image_url=image_url,
        description=description
    )

    db.add(gallery_item)
    db.commit()
    db.refresh(gallery_item)

    return {
        "message": "Фото добавлено",
        "id": gallery_item.id,
        "image_url": get_full_url(gallery_item.image_url)
    }


@router.delete("/places/gallery/{gallery_id}")
def delete_place_gallery(gallery_id: int, db: Session = Depends(get_db)):
    """Удалить фото из галереи"""
    gallery_item = db.query(PlaceGallery).filter(PlaceGallery.id == gallery_id).first()

    if not gallery_item:
        raise HTTPException(status_code=404, detail="Фото не найдено")

    db.delete(gallery_item)
    db.commit()
    return {"message": "Фото удалено"}


# ========================================
# ПРОМО-АКЦИИ
# ========================================

@router.post("/promo")
async def create_promo(
        related_type: str = Form(...),  # "ticket" или "place"
        related_id: int = Form(...),
        title: str = Form(...),
        title_ru: str = Form(...),
        description: str = Form(...),
        description_ru: str = Form(...),
        discount_text: str = Form(None),
        promo_code: str = Form(None),
        start_date: str = Form(...),
        end_date: str = Form(...),
        promo_image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Создание промо-акции"""
    if related_type not in ["ticket", "place"]:
        raise HTTPException(status_code=400, detail="related_type должен быть 'ticket' или 'place'")

    # Проверяем существование объекта
    if related_type == "ticket":
        obj = db.query(Ticket).filter(Ticket.id == related_id).first()
    else:
        obj = db.query(Place).filter(Place.id == related_id).first()

    if not obj:
        raise HTTPException(status_code=404, detail=f"{related_type} не найден")

    image_url = None
    if promo_image:
        image_url = await save_uploaded_file(promo_image, "promo")

    promo = PromoAction(
        related_type=related_type,
        related_id=related_id,
        title=title,
        title_ru=title_ru,
        description=description,
        description_ru=description_ru,
        discount_text=discount_text,
        promo_code=promo_code,
        start_date=datetime.fromisoformat(start_date),
        end_date=datetime.fromisoformat(end_date),
        promo_image_url=image_url
    )

    db.add(promo)
    db.commit()
    db.refresh(promo)

    return {
        "message": "Промо-акция создана",
        "id": promo.id,
        "title": promo.title
    }


@router.get("/promo")
def get_all_promos(
        related_type: Optional[str] = None,
        status: Optional[str] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Получить все промо-акции"""
    query = db.query(PromoAction)

    if related_type:
        query = query.filter(PromoAction.related_type == related_type)

    if status:
        query = query.filter(PromoAction.status == status)

    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            PromoAction.status == "active",
            PromoAction.start_date <= now,
            PromoAction.end_date >= now
        )

    promos = query.order_by(desc(PromoAction.created_at)).offset(skip).limit(limit).all()

    result = []
    for promo in promos:
        # Получаем информацию о связанном объекте
        related_obj = None
        if promo.related_type == "ticket":
            ticket = db.query(Ticket).filter(Ticket.id == promo.related_id).first()
            if ticket:
                related_obj = {
                    "id": ticket.id,
                    "title": ticket.title,
                    "title_ru": ticket.title_ru,
                    "photo_url": get_full_url(ticket.main_photo_url)
                }
        else:
            place = db.query(Place).filter(Place.id == promo.related_id).first()
            if place:
                related_obj = {
                    "id": place.id,
                    "title": place.title,
                    "title_ru": place.title_ru,
                    "photo_url": get_full_url(place.main_photo_url)
                }

        result.append({
            "id": promo.id,
            "related_type": promo.related_type,
            "related_id": promo.related_id,
            "related_object": related_obj,
            "title": promo.title,
            "title_ru": promo.title_ru,
            "description": promo.description,
            "description_ru": promo.description_ru,
            "discount_text": promo.discount_text,
            "promo_code": promo.promo_code,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
            "promo_image_url": get_full_url(promo.promo_image_url),
            "status": promo.status,
            "created_at": promo.created_at
        })

    return result


@router.get("/promo/{promo_id}")
def get_promo_detail(promo_id: int, db: Session = Depends(get_db)):
    """Получить детали промо-акции"""
    promo = db.query(PromoAction).filter(PromoAction.id == promo_id).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Промо-акция не найдена")

    # Получаем полную информацию о связанном объекте
    related_obj = None
    if promo.related_type == "ticket":
        ticket = db.query(Ticket).filter(Ticket.id == promo.related_id).first()
        if ticket:
            related_obj = {
                "id": ticket.id,
                "title": ticket.title,
                "title_ru": ticket.title_ru,
                "description": ticket.description,
                "event_date": ticket.event_date,
                "address": ticket.address,
                "photo_url": get_full_url(ticket.main_photo_url)
            }
    else:
        place = db.query(Place).filter(Place.id == promo.related_id).first()
        if place:
            related_obj = {
                "id": place.id,
                "title": place.title,
                "title_ru": place.title_ru,
                "description": place.description,
                "address": place.address,
                "photo_url": get_full_url(place.main_photo_url)
            }

    return {
        "id": promo.id,
        "related_type": promo.related_type,
        "related_id": promo.related_id,
        "related_object": related_obj,
        "title": promo.title,
        "title_ru": promo.title_ru,
        "description": promo.description,
        "description_ru": promo.description_ru,
        "discount_text": promo.discount_text,
        "promo_code": promo.promo_code,
        "start_date": promo.start_date,
        "end_date": promo.end_date,
        "promo_image_url": get_full_url(promo.promo_image_url),
        "status": promo.status,
        "created_at": promo.created_at
    }


@router.put("/promo/{promo_id}")
async def update_promo(
        promo_id: int,
        title: Optional[str] = Form(None),
        title_ru: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        description_ru: Optional[str] = Form(None),
        discount_text: Optional[str] = Form(None),
        promo_code: Optional[str] = Form(None),
        start_date: Optional[str] = Form(None),
        end_date: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        promo_image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """Обновить промо-акцию"""
    promo = db.query(PromoAction).filter(PromoAction.id == promo_id).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Промо-акция не найдена")

    if title:
        promo.title = title
    if title_ru:
        promo.title_ru = title_ru
    if description:
        promo.description = description
    if description_ru:
        promo.description_ru = description_ru
    if discount_text:
        promo.discount_text = discount_text
    if promo_code:
        promo.promo_code = promo_code
    if start_date:
        promo.start_date = datetime.fromisoformat(start_date)
    if end_date:
        promo.end_date = datetime.fromisoformat(end_date)
    if status:
        promo.status = status
    if promo_image:
        promo.promo_image_url = await save_uploaded_file(promo_image, "promo")

    db.commit()
    return {"message": "Промо-акция обновлена"}


@router.delete("/promo/{promo_id}")
def delete_promo(promo_id: int, db: Session = Depends(get_db)):
    """Удалить промо-акцию"""
    promo = db.query(PromoAction).filter(PromoAction.id == promo_id).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Промо-акция не найдена")

    db.delete(promo)
    db.commit()
    return {"message": "Промо-акция удалена"}


# ========================================
# ПОИСК
# ========================================

@router.get("/search")
def search_leisure(
        q: str,
        search_in: Optional[str] = None,  # "tickets", "places", "all"
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """Поиск по билетам и местам"""
    results = {
        "query": q,
        "tickets": [],
        "places": []
    }

    if search_in in [None, "all", "tickets"]:
        tickets = db.query(Ticket).filter(
            or_(
                Ticket.title.ilike(f"%{q}%"),
                Ticket.title_ru.ilike(f"%{q}%"),
                Ticket.description.ilike(f"%{q}%"),
                Ticket.description_ru.ilike(f"%{q}%")
            )
        ).limit(limit).all()

        results["tickets"] = [
            {
                "id": t.id,
                "title": t.title,
                "title_ru": t.title_ru,
                "description": t.description[:200] + "..." if len(t.description) > 200 else t.description,
                "event_date": t.event_date,
                "price": t.price,
                "photo_url": get_full_url(t.main_photo_url)
            }
            for t in tickets
        ]

    if search_in in [None, "all", "places"]:
        query = db.query(Place).filter(
            or_(
                Place.title.ilike(f"%{q}%"),
                Place.title_ru.ilike(f"%{q}%"),
                Place.description.ilike(f"%{q}%"),
                Place.description_ru.ilike(f"%{q}%")
            )
        )

        if category_id:
            query = query.filter(Place.category_id == category_id)

        places = query.limit(limit).all()

        results["places"] = [
            {
                "id": p.id,
                "title": p.title,
                "title_ru": p.title_ru,
                "description": p.description[:200] + "..." if len(p.description) > 200 else p.description,
                "address": p.address,
                "price": p.price,
                "rating": float(p.rating),
                "photo_url": get_full_url(p.main_photo_url)
            }
            for p in places
        ]

    return results


# ========================================
# СТАТИСТИКА
# ========================================

@router.get("/stats")
def get_leisure_stats(db: Session = Depends(get_db)):
    """Общая статистика раздела досуг"""
    total_tickets = db.query(func.count(Ticket.id)).scalar()
    active_tickets = db.query(func.count(Ticket.id)).filter(Ticket.status == "active").scalar()

    total_places = db.query(func.count(Place.id)).scalar()
    active_places = db.query(func.count(Place.id)).filter(Place.status == "active").scalar()

    total_categories = db.query(func.count(LeisureCategory.id)).scalar()

    now = datetime.utcnow()
    active_promos = db.query(func.count(PromoAction.id)).filter(
        PromoAction.status == "active",
        PromoAction.start_date <= now,
        PromoAction.end_date >= now
    ).scalar()

    # Топ-5 популярных мест
    top_places = db.query(Place).filter(
        Place.status == "active"
    ).order_by(desc(Place.views_count)).limit(5).all()

    return {
        "total_tickets": total_tickets,
        "active_tickets": active_tickets,
        "total_places": total_places,
        "active_places": active_places,
        "total_categories": total_categories,
        "active_promos": active_promos,
        "top_places": [
            {
                "id": p.id,
                "title": p.title,
                "title_ru": p.title_ru,
                "views_count": p.views_count,
                "rating": float(p.rating)
            }
            for p in top_places
        ]
    }


# ========== ADMIN ENDPOINTS WITH RBAC FOR PLACES ==========

@router.get("/admin/places/list")
def admin_list_places(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Admin: List places with RBAC filtering (MSB sees only their own)"""
    query = db.query(Place)

    # Apply owner-based filtering for MSB/NPO roles
    query = apply_owner_filter(query, Place, current_admin)

    # Apply filters
    if category_id:
        query = query.filter(Place.category_id == category_id)
    if status:
        query = query.filter(Place.status == status)
    if search:
        query = query.filter(
            (Place.title.ilike(f"%{search}%")) |
            (Place.title_ru.ilike(f"%{search}%"))
        )

    places = query.order_by(Place.created_at.desc()).offset(skip).limit(limit).all()
    return places


@router.post("/admin/places/create", status_code=status.HTTP_201_CREATED)
def admin_create_place(
    place_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.CREATE))
):
    """Admin: Create place with auto-approval for administrators/super_admins"""
    # Determine moderation status based on admin role
    is_admin_created = current_admin.role in ['administrator', 'super_admin']
    moderation_status = 'approved' if is_admin_created else 'pending'

    new_place = Place(
        **place_data,
        admin_id=current_admin.id,
        moderation_status=moderation_status,
        is_admin_created=is_admin_created,
        moderated_at=datetime.utcnow() if is_admin_created else None,
        moderated_by=current_admin.id if is_admin_created else None
    )
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place


@router.put("/admin/places/{place_id}")
def admin_update_place(
    place_id: int,
    place_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Admin: Update place with ownership check and re-moderation logic"""
    query = db.query(Place).filter(Place.id == place_id)
    query = apply_owner_filter(query, Place, current_admin)

    place = query.first()
    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено или у вас нет прав на его редактирование")

    # Define major fields that trigger re-moderation
    major_fields = ['title', 'title_ru', 'description', 'description_ru', 'price', 'main_photo_url']
    major_update = any(field in place_data for field in major_fields)

    # Check if admin bypasses moderation
    is_admin = current_admin.role in ['administrator', 'super_admin']

    # Apply re-moderation logic
    if major_update and not is_admin and place.moderation_status == 'approved':
        place.moderation_status = 'pending'
        place.moderated_at = None
        place.moderated_by = None
    elif major_update and is_admin:
        place.moderated_at = datetime.utcnow()
        place.moderated_by = current_admin.id

    for key, value in place_data.items():
        setattr(place, key, value)

    db.commit()
    db.refresh(place)
    return place


@router.delete("/admin/places/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.DELETE))
):
    """Admin: Delete place with ownership check"""
    query = db.query(Place).filter(Place.id == place_id)
    query = apply_owner_filter(query, Place, current_admin)

    place = query.first()
    if not place:
        raise HTTPException(status_code=404, detail="Место не найдено или у вас нет прав на его удаление")

    db.delete(place)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ========== ADMIN ENDPOINTS WITH RBAC FOR TICKETS ==========

@router.get("/admin/tickets/list")
def admin_list_tickets(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Admin: List tickets with RBAC filtering (MSB sees only their own)"""
    query = db.query(Ticket)

    # Apply owner-based filtering for MSB/NPO roles
    query = apply_owner_filter(query, Ticket, current_admin)

    # Apply filters
    if status:
        query = query.filter(Ticket.status == status)
    if search:
        query = query.filter(
            (Ticket.title.ilike(f"%{search}%")) |
            (Ticket.title_ru.ilike(f"%{search}%"))
        )

    tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()
    return tickets


@router.post("/admin/tickets/create", status_code=status.HTTP_201_CREATED)
def admin_create_ticket(
    ticket_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.CREATE))
):
    """Admin: Create ticket with auto-approval for administrators/super_admins"""
    # Determine moderation status based on admin role
    is_admin_created = current_admin.role in ['administrator', 'super_admin']
    moderation_status = 'approved' if is_admin_created else 'pending'

    new_ticket = Ticket(
        **ticket_data,
        admin_id=current_admin.id,
        moderation_status=moderation_status,
        is_admin_created=is_admin_created,
        moderated_at=datetime.utcnow() if is_admin_created else None,
        moderated_by=current_admin.id if is_admin_created else None
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


@router.put("/admin/tickets/{ticket_id}")
def admin_update_ticket(
    ticket_id: int,
    ticket_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Admin: Update ticket with ownership check and re-moderation logic"""
    query = db.query(Ticket).filter(Ticket.id == ticket_id)
    query = apply_owner_filter(query, Ticket, current_admin)

    ticket = query.first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден или у вас нет прав на его редактирование")

    # Define major fields that trigger re-moderation
    major_fields = ['title', 'title_ru', 'description', 'description_ru', 'event_date', 'price']
    major_update = any(field in ticket_data for field in major_fields)

    # Check if admin bypasses moderation
    is_admin = current_admin.role in ['administrator', 'super_admin']

    # Apply re-moderation logic
    if major_update and not is_admin and ticket.moderation_status == 'approved':
        ticket.moderation_status = 'pending'
        ticket.moderated_at = None
        ticket.moderated_by = None
    elif major_update and is_admin:
        ticket.moderated_at = datetime.utcnow()
        ticket.moderated_by = current_admin.id

    for key, value in ticket_data.items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/admin/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.DELETE))
):
    """Admin: Delete ticket with ownership check"""
    query = db.query(Ticket).filter(Ticket.id == ticket_id)
    query = apply_owner_filter(query, Ticket, current_admin)

    ticket = query.first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Билет не найден или у вас нет прав на его удаление")

    db.delete(ticket)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ========== ADMIN ENDPOINTS WITH RBAC FOR PROMO ACTIONS ==========

@router.get("/admin/promo/list")
def admin_list_promos(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    related_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Admin: List promo actions with RBAC filtering (MSB sees only their own)"""
    query = db.query(PromoAction)

    # Apply owner-based filtering for MSB/NPO roles
    query = apply_owner_filter(query, PromoAction, current_admin)

    # Apply filters
    if status:
        query = query.filter(PromoAction.status == status)
    if related_type:
        query = query.filter(PromoAction.related_type == related_type)

    promos = query.order_by(PromoAction.created_at.desc()).offset(skip).limit(limit).all()
    return promos


@router.post("/admin/promo/create", status_code=status.HTTP_201_CREATED)
def admin_create_promo(
    promo_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.CREATE))
):
    """Admin: Create promo action with auto-approval for administrators/super_admins"""
    # Determine moderation status based on admin role
    is_admin_created = current_admin.role in ['administrator', 'super_admin']
    moderation_status = 'approved' if is_admin_created else 'pending'

    new_promo = PromoAction(
        **promo_data,
        admin_id=current_admin.id,
        moderation_status=moderation_status,
        is_admin_created=is_admin_created,
        moderated_at=datetime.utcnow() if is_admin_created else None,
        moderated_by=current_admin.id if is_admin_created else None
    )
    db.add(new_promo)
    db.commit()
    db.refresh(new_promo)
    return new_promo


@router.put("/admin/promo/{promo_id}")
def admin_update_promo(
    promo_id: int,
    promo_data: dict,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Admin: Update promo action with ownership check and re-moderation logic"""
    query = db.query(PromoAction).filter(PromoAction.id == promo_id)
    query = apply_owner_filter(query, PromoAction, current_admin)

    promo = query.first()
    if not promo:
        raise HTTPException(status_code=404, detail="Промо-акция не найдена или у вас нет прав на её редактирование")

    # Define major fields that trigger re-moderation
    major_fields = ['title', 'title_ru', 'description', 'description_ru', 'discount_text', 'promo_code']
    major_update = any(field in promo_data for field in major_fields)

    # Check if admin bypasses moderation
    is_admin = current_admin.role in ['administrator', 'super_admin']

    # Apply re-moderation logic
    if major_update and not is_admin and promo.moderation_status == 'approved':
        promo.moderation_status = 'pending'
        promo.moderated_at = None
        promo.moderated_by = None
    elif major_update and is_admin:
        promo.moderated_at = datetime.utcnow()
        promo.moderated_by = current_admin.id

    for key, value in promo_data.items():
        setattr(promo, key, value)

    db.commit()
    db.refresh(promo)
    return promo


@router.delete("/admin/promo/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_promo(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.DELETE))
):
    """Admin: Delete promo action with ownership check"""
    query = db.query(PromoAction).filter(PromoAction.id == promo_id)
    query = apply_owner_filter(query, PromoAction, current_admin)

    promo = query.first()
    if not promo:
        raise HTTPException(status_code=404, detail="Промо-акция не найдена или у вас нет прав на её удаление")

    db.delete(promo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ========== MODERATION ENDPOINTS FOR PLACES ==========

@router.get("/admin/places/moderation/stats", response_model=ModerationStats)
def get_places_moderation_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get place moderation statistics"""
    total = db.query(Place).count()
    pending = db.query(Place).filter(Place.moderation_status == 'pending').count()
    approved = db.query(Place).filter(Place.moderation_status == 'approved').count()
    rejected = db.query(Place).filter(Place.moderation_status == 'rejected').count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }


@router.get("/admin/places/moderation/pending")
def get_pending_places(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all pending places awaiting moderation"""
    places = db.query(Place).filter(
        Place.moderation_status == 'pending'
    ).offset(skip).limit(limit).all()
    return places


@router.get("/admin/places/moderation/all-statuses")
def get_all_places_with_status(
    moderation_status: Optional[ModerationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all places with optional status filter"""
    query = db.query(Place)

    if moderation_status:
        query = query.filter(Place.moderation_status == moderation_status.value)

    places = query.offset(skip).limit(limit).all()
    return places


@router.post("/admin/places/moderation/{place_id}/approve")
def approve_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Approve a place"""
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    place.moderation_status = 'approved'
    place.moderated_at = datetime.utcnow()
    place.moderated_by = current_admin.id

    db.commit()
    db.refresh(place)
    return place


@router.post("/admin/places/moderation/{place_id}/reject")
def reject_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Reject a place"""
    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    place.moderation_status = 'rejected'
    place.moderated_at = datetime.utcnow()
    place.moderated_by = current_admin.id

    db.commit()
    db.refresh(place)
    return place


# ========== MODERATION ENDPOINTS FOR TICKETS ==========

@router.get("/admin/tickets/moderation/stats", response_model=ModerationStats)
def get_tickets_moderation_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get ticket moderation statistics"""
    total = db.query(Ticket).count()
    pending = db.query(Ticket).filter(Ticket.moderation_status == 'pending').count()
    approved = db.query(Ticket).filter(Ticket.moderation_status == 'approved').count()
    rejected = db.query(Ticket).filter(Ticket.moderation_status == 'rejected').count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }


@router.get("/admin/tickets/moderation/pending")
def get_pending_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all pending tickets awaiting moderation"""
    tickets = db.query(Ticket).filter(
        Ticket.moderation_status == 'pending'
    ).offset(skip).limit(limit).all()
    return tickets


@router.get("/admin/tickets/moderation/all-statuses")
def get_all_tickets_with_status(
    moderation_status: Optional[ModerationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all tickets with optional status filter"""
    query = db.query(Ticket)

    if moderation_status:
        query = query.filter(Ticket.moderation_status == moderation_status.value)

    tickets = query.offset(skip).limit(limit).all()
    return tickets


@router.post("/admin/tickets/moderation/{ticket_id}/approve")
def approve_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Approve a ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    ticket.moderation_status = 'approved'
    ticket.moderated_at = datetime.utcnow()
    ticket.moderated_by = current_admin.id

    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/admin/tickets/moderation/{ticket_id}/reject")
def reject_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Reject a ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    ticket.moderation_status = 'rejected'
    ticket.moderated_at = datetime.utcnow()
    ticket.moderated_by = current_admin.id

    db.commit()
    db.refresh(ticket)
    return ticket


# ========== MODERATION ENDPOINTS FOR PROMO ACTIONS ==========

@router.get("/admin/promo/moderation/stats", response_model=ModerationStats)
def get_promo_moderation_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get promo action moderation statistics"""
    total = db.query(PromoAction).count()
    pending = db.query(PromoAction).filter(PromoAction.moderation_status == 'pending').count()
    approved = db.query(PromoAction).filter(PromoAction.moderation_status == 'approved').count()
    rejected = db.query(PromoAction).filter(PromoAction.moderation_status == 'rejected').count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }


@router.get("/admin/promo/moderation/pending")
def get_pending_promo(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all pending promo actions awaiting moderation"""
    promos = db.query(PromoAction).filter(
        PromoAction.moderation_status == 'pending'
    ).offset(skip).limit(limit).all()
    return promos


@router.get("/admin/promo/moderation/all-statuses")
def get_all_promo_with_status(
    moderation_status: Optional[ModerationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.LEISURE, allow_read_only=True))
):
    """Get all promo actions with optional status filter"""
    query = db.query(PromoAction)

    if moderation_status:
        query = query.filter(PromoAction.moderation_status == moderation_status.value)

    promos = query.offset(skip).limit(limit).all()
    return promos


@router.post("/admin/promo/moderation/{promo_id}/approve")
def approve_promo(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Approve a promo action"""
    promo = db.query(PromoAction).filter(PromoAction.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo action not found")

    promo.moderation_status = 'approved'
    promo.moderated_at = datetime.utcnow()
    promo.moderated_by = current_admin.id

    db.commit()
    db.refresh(promo)
    return promo


@router.post("/admin/promo/moderation/{promo_id}/reject")
def reject_promo(
    promo_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.LEISURE, Permission.UPDATE))
):
    """Reject a promo action"""
    promo = db.query(PromoAction).filter(PromoAction.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo action not found")

    promo.moderation_status = 'rejected'
    promo.moderated_at = datetime.utcnow()
    promo.moderated_by = current_admin.id

    db.commit()
    db.refresh(promo)
    return promo