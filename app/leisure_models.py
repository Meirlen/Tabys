from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


# === КАТЕГОРИИ ===
class LeisureCategory(Base):
    """Категории для мест досуга"""
    __tablename__ = "leisure_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # аквапарки и бассейны
    name_ru = Column(String(255), nullable=False)  # аквапарки и бассейны
    icon_url = Column(String(500), nullable=True)  # иконка категории
    created_at = Column(DateTime, default=func.now())


# === БИЛЕТЫ (СОБЫТИЯ) ===
class Ticket(Base):
    """Билеты на события"""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    title_ru = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)

    # Основная информация
    event_date = Column(DateTime, nullable=False)  # дата события
    address = Column(String(500), nullable=False)
    price = Column(String(100), nullable=True)  # "от 5000 тг" или "Бесплатно"

    # Медиа
    main_photo_url = Column(String(500), nullable=True)

    # Контакты и ссылки
    address_link = Column(String(500), nullable=True)  # ссылка на карты
    instagram_url = Column(String(500), nullable=True)
    tiktok_url = Column(String(500), nullable=True)
    whatsapp_number = Column(String(50), nullable=True)

    # Статус
    status = Column(String(50), default="active")  # active, inactive, sold_out

    # Owner tracking for RBAC
    admin_id = Column(Integer, nullable=True, index=True)  # ID of admin who created this ticket

    # Moderation fields
    moderation_status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    moderated_at = Column(DateTime, nullable=True)  # Timestamp when moderation action was taken
    moderated_by = Column(Integer, nullable=True)  # Admin ID who performed moderation
    moderation_comment = Column(Text, nullable=True)  # Optional comment/reason for rejection
    is_admin_created = Column(Boolean, default=False, nullable=False)  # True if created by administrator/super_admin

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# === ГАЛЕРЕЯ ДЛЯ БИЛЕТОВ ===
class TicketGallery(Base):
    """Фотогалерея для билетов"""
    __tablename__ = "ticket_gallery"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, nullable=False)  # ID билета
    image_url = Column(String(500), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())


# === МЕСТА ===
class Place(Base):
    """Места для посещения"""
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, nullable=True)  # ID категории

    title = Column(String(255), nullable=False)
    title_ru = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)

    # Основная информация
    event_date = Column(DateTime, nullable=True)  # если есть конкретная дата
    address = Column(String(500), nullable=False)
    price = Column(String(100), nullable=True)  # "средний чек 10000 тг"

    # Медиа
    main_photo_url = Column(String(500), nullable=True)

    # Контакты и ссылки
    address_link = Column(String(500), nullable=True)
    instagram_url = Column(String(500), nullable=True)
    tiktok_url = Column(String(500), nullable=True)
    whatsapp_number = Column(String(50), nullable=True)

    # Рейтинг и популярность
    rating = Column(Numeric(3, 2), default=0.0)  # 0.00 - 5.00
    views_count = Column(Integer, default=0)

    # Статус
    status = Column(String(50), default="active")  # active, inactive

    # Owner tracking for RBAC
    admin_id = Column(Integer, nullable=True, index=True)  # ID of admin who created this place

    # Moderation fields
    moderation_status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    moderated_at = Column(DateTime, nullable=True)  # Timestamp when moderation action was taken
    moderated_by = Column(Integer, nullable=True)  # Admin ID who performed moderation
    moderation_comment = Column(Text, nullable=True)  # Optional comment/reason for rejection
    is_admin_created = Column(Boolean, default=False, nullable=False)  # True if created by administrator/super_admin

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# === ГАЛЕРЕЯ ДЛЯ МЕСТ ===
class PlaceGallery(Base):
    """Фотогалерея для мест"""
    __tablename__ = "place_gallery"

    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(Integer, nullable=False)  # ID места
    image_url = Column(String(500), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())


# === ПРОМО-АКЦИИ ===
class PromoAction(Base):
    """Промо-акции для досуга"""
    __tablename__ = "promo_actions"

    id = Column(Integer, primary_key=True, index=True)

    # Связь с местом или билетом
    related_type = Column(String(50), nullable=False)  # "ticket" или "place"
    related_id = Column(Integer, nullable=False)  # ID билета или места

    title = Column(String(255), nullable=False)
    title_ru = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    description_ru = Column(Text, nullable=False)

    # Условия акции
    discount_text = Column(String(255), nullable=True)  # "скидка 30%"
    promo_code = Column(String(100), nullable=True)  # промокод

    # Сроки
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Медиа
    promo_image_url = Column(String(500), nullable=True)

    # Статус
    status = Column(String(50), default="active")  # active, inactive, expired

    # Owner tracking for RBAC
    admin_id = Column(Integer, nullable=True, index=True)  # ID of admin who created this promo

    # Moderation fields
    moderation_status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    moderated_at = Column(DateTime, nullable=True)  # Timestamp when moderation action was taken
    moderated_by = Column(Integer, nullable=True)  # Admin ID who performed moderation
    moderation_comment = Column(Text, nullable=True)  # Optional comment/reason for rejection
    is_admin_created = Column(Boolean, default=False, nullable=False)  # True if created by administrator/super_admin

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())