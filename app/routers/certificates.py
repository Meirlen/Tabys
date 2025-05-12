from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime

from app.database import get_db
from app.schemas import Certificate, CertificateCreate
from app import crud
from app.oauth2 import get_current_user

router = APIRouter(prefix="/api/v2/certificates", tags=["Certificates"])

# Путь для сохранения файлов сертификатов
CERTIFICATES_DIR = "uploads/certificates"
os.makedirs(CERTIFICATES_DIR, exist_ok=True)


@router.get("/", response_model=List[Certificate])
def list_certificates(
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение списка сертификатов
    """
    # Проверка прав доступа (обычные пользователи видят только свои сертификаты)
    if not current_user.is_admin:
        return crud.get_user_certificates(db, user_id=current_user.id, skip=skip, limit=limit)

    return crud.get_certificates(db, status=status, skip=skip, limit=limit)


@router.get("/my", response_model=List[Certificate])
def list_my_certificates(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение списка сертификатов текущего пользователя
    """
    return crud.get_user_certificates(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{certificate_id}", response_model=Certificate)
def get_certificate_details(
        certificate_id: int = Path(..., title="ID сертификата", ge=1),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
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

    # Проверка прав доступа (только владелец сертификата или администратор)
    if certificate.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для просмотра этого сертификата"
        )

    return certificate


@router.post("/", response_model=Certificate, status_code=status.HTTP_201_CREATED)
async def create_certificate(
        # Убираем user_id из параметров, так как будем определять его из токена
        title: str = Form(...),
        description: Optional[str] = Form(None),
        course_id: Optional[int] = Form(None),
        image: Optional[UploadFile] = File(None),
        pdf_file: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Создание нового сертификата (только для администраторов)
    """
    # Проверка прав доступа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для создания сертификатов"
        )

    # Используем ID текущего пользователя, если создаем сертификат для себя
    # или админ может указать конкретного пользователя через Form параметр user_id
    user_id = current_user.id

    # Если передан user_id через Form, и текущий пользователь админ,
    # то используем переданный user_id
    # form_user_id = Form(None)
    # if form_user_id and current_user.is_admin:
    # user_id = form_user_id

    # Проверка существования пользователя
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Проверка существования курса, только если ID курса указан
    if course_id:
        course = crud.get_course(db, course_id=course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Курс не найден"
            )

    # Проверка, что загружен хотя бы один файл
    if not image and not pdf_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо загрузить изображение или PDF-файл сертификата"
        )

    # Создаем директории для сохранения файлов, если они не существуют
    user_cert_dir = os.path.join(CERTIFICATES_DIR, str(user_id))
    os.makedirs(user_cert_dir, exist_ok=True)

    image_url = None
    file_url = None

    # Сохраняем изображение сертификата, если оно было загружено
    if image:
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        image_filename = f"certificate_{user_id}_{timestamp}.{image.filename.split('.')[-1]}"
        image_path = os.path.join(user_cert_dir, image_filename)

        # Сохраняем файл
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Сохраняем URL к изображению (относительный путь)
        image_url = os.path.join("certificates", str(user_id), image_filename)

    # Сохраняем PDF-файл сертификата, если он был загружен
    if pdf_file:
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"certificate_{user_id}_{timestamp}.pdf"
        pdf_path = os.path.join(user_cert_dir, pdf_filename)

        # Сохраняем файл
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        # Сохраняем URL к файлу (относительный путь)
        file_url = os.path.join("certificates", str(user_id), pdf_filename)

    # Создаем сертификат в базе данных
    return crud.create_certificate(
        db=db,
        user_id=user_id,
        title=title,
        description=description,
        course_id=course_id,
        image_url=image_url,
        file_url=file_url
    )


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate(
        certificate_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Удаление сертификата (только для администраторов)
    """
    # Проверка прав доступа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для удаления сертификатов"
        )

    # Получаем сертификат
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Удаляем файлы сертификата, если они существуют
    if certificate.image_url:
        image_path = os.path.join("uploads", certificate.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)

    if certificate.file_url:
        file_path = os.path.join("uploads", certificate.file_url)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Удаляем сертификат из базы данных
    result = crud.delete_certificate(db, certificate_id=certificate_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить сертификат"
        )

    return None


@router.post("/{certificate_id}/revoke", response_model=Certificate)
def revoke_certificate(
        certificate_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Отзыв сертификата (только для администраторов)
    """
    # Проверка прав доступа
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для отзыва сертификатов"
        )

    # Получаем сертификат
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Отзываем сертификат
    updated_certificate = crud.revoke_certificate(db, certificate_id=certificate_id)
    if not updated_certificate:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отозвать сертификат"
        )

    return updated_certificate


@router.get("/{certificate_id}/download")
def download_certificate(
        certificate_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Скачивание файла сертификата
    """
    # Получаем сертификат
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Проверка прав доступа (только владелец сертификата или администратор)
    if certificate.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для скачивания этого сертификата"
        )

    # Проверяем, есть ли файл для скачивания
    if not certificate.file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл сертификата не найден"
        )

    # Формируем полный путь к файлу
    file_path = os.path.join("uploads", certificate.file_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл сертификата не найден на сервере"
        )

    # Формируем имя файла для скачивания
    filename = f"certificate_{certificate_id}.pdf"

    # Возвращаем файл
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/{certificate_id}/image")
def get_certificate_image(
        certificate_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение изображения сертификата
    """
    # Получаем сертификат
    certificate = crud.get_certificate(db, certificate_id=certificate_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сертификат не найден"
        )

    # Проверка прав доступа (только владелец сертификата или администратор)
    if certificate.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для просмотра этого сертификата"
        )

    # Проверяем, есть ли изображение
    if not certificate.image_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Изображение сертификата не найдено"
        )

    # Формируем полный путь к изображению
    image_path = os.path.join("uploads", certificate.image_url)
    if not os.path.exists(image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Изображение сертификата не найдено на сервере"
        )

    # Определяем тип медиа на основе расширения файла
    file_ext = image_path.split('.')[-1].lower()
    media_type = f"image/{file_ext}"
    if file_ext == "jpg" or file_ext == "jpeg":
        media_type = "image/jpeg"

    # Возвращаем изображение
    return FileResponse(
        path=image_path,
        media_type=media_type
    )