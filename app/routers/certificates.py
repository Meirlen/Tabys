from fastapi import APIRouter, Depends, status, Query, Response, BackgroundTasks, HTTPException, File, UploadFile, Form, \
    Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import *
from app.models import Certificate, CertificateApplication
from app import crud
from app.utils import send_email, validate_file_extension, save_upload_file
from app.oauth2 import get_current_user
import os

router = APIRouter(prefix="/api/v2/certificates", tags=["Certificates"])


@router.get("/", response_model=List[CertificateList])
def list_certificates(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    Получение списка всех сертификатов
    """
    certificates = crud.get_certificates(db, skip=skip, limit=limit)
    return certificates


@router.get("/my", response_model=List[CertificateList])
def list_my_certificates(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение списка сертификатов текущего пользователя
    """
    certificates = crud.get_user_certificates(db, user_id=current_user.id, skip=skip, limit=limit)
    return certificates


@router.get("/search", response_model=List[CertificateList])
def search_certificates(
        db: Session = Depends(get_db),
        course_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20
):
    """
    Поиск и фильтрация сертификатов по различным параметрам
    """
    filters = CertificateFilter(
        course_id=course_id,
        status=status,
        search=search,
        from_date=from_date,
        to_date=to_date
    )

    certificates = crud.filter_certificates(
        db,
        filters=filters,
        skip=skip,
        limit=limit
    )

    return certificates


@router.get("/{certificate_id}", response_model=CertificateDetail)
def get_certificate_details(
        certificate_id: int = Path(..., title="ID сертификата", ge=1),
        db: Session = Depends(get_db)
):
    """
    Получение детальной информации о сертификате
    """
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    return certificate


@router.post("/", response_model=CertificateDetail, status_code=status.HTTP_201_CREATED)
async def create_certificate(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        title: str = Form(...),
        description: str = Form(...),
        issuer: str = Form(...),
        issue_date: datetime = Form(...),
        course_id: Optional[int] = Form(None),
        certificate_url: Optional[str] = Form(None),
        certificate_image: Optional[UploadFile] = File(None)
):
    """
    Создание нового сертификата
    """
    # Создаем папку для хранения сертификатов, если она еще не существует
    upload_dir = os.path.join("uploads", "certificates")
    os.makedirs(upload_dir, exist_ok=True)

    # Сохраняем изображение сертификата, если оно было загружено
    certificate_image_path = None
    if certificate_image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        if not validate_file_extension(certificate_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений и PDF (jpg, jpeg, png, pdf)"
            )
        certificate_image_path = await save_upload_file(certificate_image, upload_dir)

    # Создаем объект сертификата
    certificate_data = CertificateCreate(
        title=title,
        description=description,
        issuer=issuer,
        issue_date=issue_date,
        course_id=course_id
    )

    # Создаем сертификат в базе данных
    certificate = crud.create_certificate(
        db=db,
        certificate=certificate_data,
        user_id=current_user.id
    )

    # Обновляем пути к файлам
    certificate_update = CertificateUpdate(
        certificate_url=certificate_url,
        certificate_image=certificate_image_path
    )

    updated_certificate = crud.update_certificate(
        db=db,
        certificate_id=certificate.id,
        certificate_update=certificate_update
    )

    # Отправляем уведомление администратору о новом сертификате на модерацию
    admin_email = "admin@example.com"  # Замените на реальный адрес администратора
    background_tasks.add_task(
        send_email,
        recipient_email=admin_email,
        subject=f"Новый сертификат на модерацию: {certificate.title}",
        message=f"""
        Здравствуйте!

        Пользователь загрузил новый сертификат "{certificate.title}" и отправил его на модерацию.

        Пожалуйста, проверьте сертификат и примите решение о его публикации.

        С уважением,
        Система управления сертификатами
        """
    )

    return updated_certificate


@router.put("/{certificate_id}", response_model=CertificateDetail)
async def update_certificate(
        certificate_id: int = Path(..., title="ID сертификата", ge=1),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        issuer: Optional[str] = Form(None),
        issue_date: Optional[datetime] = Form(None),
        course_id: Optional[int] = Form(None),
        certificate_url: Optional[str] = Form(None),
        certificate_image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление существующего сертификата
    """
    # Проверяем существование сертификата
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Проверяем права доступа (владелец сертификата или администратор)
    if certificate.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Создаем папку для хранения сертификатов, если она еще не существует
    upload_dir = os.path.join("uploads", "certificates")
    os.makedirs(upload_dir, exist_ok=True)

    # Сохраняем изображение сертификата, если оно было загружено
    certificate_image_path = None
    if certificate_image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        if not validate_file_extension(certificate_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений и PDF (jpg, jpeg, png, pdf)"
            )
        certificate_image_path = await save_upload_file(certificate_image, upload_dir)

    # Создаем объект обновления сертификата
    certificate_update = CertificateUpdate(
        title=title,
        description=description,
        issuer=issuer,
        issue_date=issue_date,
        course_id=course_id,
        certificate_url=certificate_url,
        certificate_image=certificate_image_path if certificate_image else None
    )

    # Обновляем сертификат в базе данных
    updated_certificate = crud.update_certificate(
        db=db,
        certificate_id=certificate_id,
        certificate_update=certificate_update
    )

    # После обновления сертификат снова отправляется на модерацию
    if not current_user.is_admin:
        crud.update_certificate_status(
            db=db,
            certificate_id=certificate_id,
            status_update=CertificateStatusUpdate(
                status="pending",
                status_comment="Сертификат обновлен и ожидает повторной модерации"
            )
        )

    return updated_certificate


@router.patch("/{certificate_id}/status", response_model=CertificateDetail)
def update_certificate_status(
        certificate_id: int,
        status_update: CertificateStatusUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление статуса сертификата (только для администраторов)
    """
    # Проверка прав доступа (администратор)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Проверяем существование сертификата
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Обновляем статус сертификата
    updated_certificate = crud.update_certificate_status(
        db=db,
        certificate_id=certificate_id,
        status_update=status_update
    )

    # Отправляем уведомление владельцу сертификата о результате модерации
    if status_update.status in ["approved", "rejected"]:
        # Получаем пользователя
        user = crud.get_user(db, user_id=certificate.user_id)
        if user and hasattr(user, 'email') and user.email:
            status_text = "одобрен" if status_update.status == "approved" else "отклонен"
            subject = f"Статус вашего сертификата '{certificate.title}' изменен"
            message = f"""
            Здравствуйте, {user.user_name}!

            Статус вашего сертификата "{certificate.title}" был изменен на "{status_text}".

            {f"Комментарий: {status_update.status_comment}" if status_update.status_comment else ""}

            С уважением,
            Администрация платформы
            """
            send_email(
                recipient_email=user.email,
                subject=subject,
                message=message
            )

    return updated_certificate


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate(
        certificate_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Удаление сертификата (только для владельца или администратора)
    """
    # Проверяем существование сертификата
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Проверяем права доступа (владелец сертификата или администратор)
    if certificate.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Удаляем сертификат
    crud.delete_certificate(db=db, certificate_id=certificate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Эндпоинты для заявок на сертификацию

@router.post("/applications", response_model=CertificateApplication, status_code=status.HTTP_201_CREATED)
def create_application(
        application: CertificateApplicationCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Создание заявки на сертификацию
    """
    # Создаем заявку
    application = crud.create_certificate_application(
        db=db,
        application=application,
        user_id=current_user.id
    )

    # Отправляем уведомление менеджеру проекта
    manager_email = "manager@example.com"  # Замените на реальный адрес менеджера
    background_tasks.add_task(
        send_email,
        recipient_email=manager_email,
        subject=f"Новая заявка на сертификацию от {application.full_name}",
        message=f"""
        Здравствуйте!

        Пользователь {application.full_name} оставил заявку на сертификацию.

        Контактная информация:
        Email: {application.email}
        Телефон: {application.phone or "Не указан"}

        Сообщение: {application.message or "Отсутствует"}

        Пожалуйста, свяжитесь с пользователем в течение двух рабочих дней.

        С уважением,
        Система управления сертификациями
        """
    )

    # Отправляем подтверждение пользователю
    if application.email:
        background_tasks.add_task(
            send_email,
            recipient_email=application.email,
            subject="Заявка на сертификацию принята",
            message=f"""
            Здравствуйте, {application.full_name}!

            Ваша заявка на сертификацию успешно принята.

            Менеджер проекта свяжется с вами в течение двух рабочих дней. В случае, если ответ не будет получен, 
            пожалуйста, свяжитесь с нами по адресу ___________ или позвоните по указанным на портале номерам.

            С уважением,
            Администрация платформы
            """
        )

    return application


@router.get("/applications", response_model=List[CertificateApplication])
def list_applications(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение списка заявок на сертификацию (для администраторов - все заявки, для пользователей - только свои)
    """
    if current_user.is_admin:
        applications = crud.get_certificate_applications(db, skip=skip, limit=limit)
    else:
        applications = crud.get_user_applications(db, user_id=current_user.id, skip=skip, limit=limit)

    return applications


@router.get("/applications/{application_id}", response_model=CertificateApplication)
def get_application_details(
        application_id: str,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение детальной информации о заявке
    """
    application = crud.get_certificate_application(db, application_id=application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    # Проверяем права доступа (владелец заявки или администратор)
    if application.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    return application


@router.patch("/applications/{application_id}/status")
def update_application_status(
        application_id: str,
        status: CertificationStatus,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление статуса заявки на сертификацию (только для администраторов)
    """
    # Проверка прав доступа (администратор)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Обновляем статус
    updated_application = crud.update_application_status(
        db=db,
        application_id=application_id,
        status=status
    )

    if not updated_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    return updated_application