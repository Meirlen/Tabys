from fastapi import APIRouter, Depends, status, Query, Response, BackgroundTasks, HTTPException, File, UploadFile, Form, \
    Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import *
from app.models import Course
from app import crud, models
from app.utils import send_email, validate_file_extension, save_upload_file
from app.oauth2 import get_current_user
from app.rbac import Module, Permission, require_permission, require_module_access
from datetime import datetime
import os

router = APIRouter(prefix="/api/v2/courses", tags=["Courses"])


@router.get("/", response_model=List[CourseList])
def list_courses(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    Получение списка всех активных курсов
    """
    courses = crud.get_courses(db, skip=skip, limit=limit)
    return courses


@router.get("/recommended", response_model=List[CourseList])
def list_recommended_courses(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка рекомендуемых курсов
    """
    courses = crud.get_recommended_courses(db, skip=skip, limit=limit)
    return courses


@router.get("/popular", response_model=List[CourseList])
def list_popular_courses(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка популярных курсов
    """
    courses = crud.get_popular_courses(db, skip=skip, limit=limit)
    return courses


@router.get("/most-searched", response_model=List[CourseList])
def list_most_searched_courses(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка часто ищемых курсов
    """
    courses = crud.get_most_searched_courses(db, skip=skip, limit=limit)
    return courses


@router.get("/free", response_model=List[CourseList])
def list_free_courses(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Получение списка бесплатных курсов
    """
    courses = crud.get_free_courses(db, skip=skip, limit=limit)
    return courses


@router.get("/search", response_model=List[CourseList])
def search_courses(
        db: Session = Depends(get_db),
        category_id: Optional[int] = None,
        language: Optional[str] = None,
        level: Optional[str] = None,
        is_free: Optional[bool] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
):
    """
    Поиск и фильтрация курсов по различным параметрам
    """
    filters = CourseFilter(
        category_id=category_id,
        language=language,
        level=level,
        is_free=is_free,
        price_min=price_min,
        price_max=price_max,
        search=search
    )

    courses = crud.filter_courses(
        db,
        filters=filters,
        skip=skip,
        limit=limit
    )

    return courses

@router.get("/my", response_model=List[CourseEnrollmentWithCourse])
def list_my_courses(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение списка курсов пользователя с полной информацией о курсах
    """
    enrollments_with_courses = crud.get_user_enrollments_with_courses(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return enrollments_with_courses


@router.get("/categories", response_model=List[CourseCategory])
def list_categories(
        db: Session = Depends(get_db)
):
    """
    Получение списка всех категорий курсов
    """
    categories = crud.get_course_categories(db)
    return categories


@router.get("/{course_id}", response_model=CourseDetail)
def get_course_details(
        course_id: int = Path(..., title="ID курса", ge=1),
        db: Session = Depends(get_db)
):
    """
    Получение детальной информации о курсе
    """
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Увеличиваем счетчик просмотров
    crud.increment_course_views(db, course_id=course_id)

    return course

@router.post("/", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
async def create_course(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user),
        title: str = Form(...),
        description: str = Form(...),
        course_url: str = Form(...),
        language: str = Form(...),
        duration: int = Form(...),
        skills: str = Form(...),
        currency: str = Form(...),
        price: float = Form(...),
        level: Optional[str] = Form(None),
        is_free: bool = Form(False),
        categories: List[int] = Form([]),
        cover_image: Optional[UploadFile] = File(None),
        video_preview: Optional[str] = Form(None)  # Изменено с File на Form
):
    """
    Создание нового курса (необходима авторизация пользователя)
    """
    # Создаем папку для хранения файлов курса, если она еще не существует
    upload_dir = os.path.join("uploads", "courses")
    os.makedirs(upload_dir, exist_ok=True)

    # Сохраняем файлы обложки, если они были загружены
    cover_image_path = None
    if cover_image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        if not validate_file_extension(cover_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений (jpg, jpeg, png, gif)"
            )
        cover_image_path = await save_upload_file(cover_image, upload_dir)

    # Для видео превью просто используем ссылку как есть
    video_preview_path = video_preview

    # Создаем объект курса
    course_data = CourseCreate(
        title=title,
        description=description,
        course_url=course_url,
        language=language,
        duration=duration,
        skills=skills,
        currency=currency,
        price=price,
        level=level,
        cover_image=cover_image_path,
        video_preview=video_preview_path,
        categories=categories,
        is_free=is_free
    )

    # Создаем курс в базе данных
    course = crud.create_course(
        db=db,
        course=course_data,
        author_id=1
    )

    # Отправляем уведомление администратору о новом курсе на модерацию
    admin_email = "admin@example.com"  # Замените на реальный адрес администратора
    background_tasks.add_task(
        send_email,
        recipient_email=admin_email,
        subject=f"Новый курс на модерацию: {course.title}",
        message=f"""
        Здравствуйте!

        Пользователь создал новый курс "{course.title}" и отправил его на модерацию.

        Пожалуйста, проверьте курс и примите решение о его публикации.

        С уважением,
        Система управления курсами
        """
    )

    return course

@router.post("/categories", response_model=CourseCategory, status_code=status.HTTP_201_CREATED)
def create_category(
        category: CourseCategoryCreate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Создание новой категории курса (только для администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    category = crud.create_course_category(db=db, category=category)
    return category


@router.post("/{course_id}/enroll", response_model=CourseEnrollment, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
        course_id: int = Path(..., title="ID курса", ge=1),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Запись пользователя на курс
    """
    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Проверяем, не записан ли пользователь уже на этот курс
    existing_enrollment = crud.get_enrollment(db, user_id=current_user.id, course_id=course_id)
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже записаны на этот курс"
        )

    # Создаем запись о зачислении на курс
    enrollment = crud.create_enrollment(
        db=db,
        user_id=current_user.id,
        course_id=course_id
    )

    return enrollment

@router.put("/{course_id}", response_model=CourseDetail)
async def update_course(
        course_id: int = Path(..., title="ID курса", ge=1),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        course_url: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        duration: Optional[int] = Form(None),
        skills: Optional[str] = Form(None),
        currency: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        level: Optional[str] = Form(None),
        is_free: Optional[bool] = Form(None),
        categories: Optional[List[int]] = Form(None),
        cover_image: Optional[UploadFile] = File(None),
        video_preview: Optional[str] = Form(None),  # Изменено с File на Form
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Обновление существующего курса (только для автора курса или администратора)
    """
    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Проверяем права доступа (автор курса или администратор)
    # if course.author_id != current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Создаем папку для хранения файлов курса, если она еще не существует
    upload_dir = os.path.join("uploads", "courses")
    os.makedirs(upload_dir, exist_ok=True)

    # Сохраняем обложку, если она была загружена
    cover_image_path = None
    if cover_image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        if not validate_file_extension(cover_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений (jpg, jpeg, png, gif)"
            )
        cover_image_path = await save_upload_file(cover_image, upload_dir)

    # Для видео превью просто используем ссылку как есть
    video_preview_path = video_preview

    # Создаем объект обновления курса
    course_update = CourseUpdate(
        title=title,
        description=description,
        course_url=course_url,
        language=language,
        duration=duration,
        skills=skills,
        currency=currency,
        price=price,
        level=level,
        cover_image=cover_image_path,
        video_preview=video_preview_path,
        categories=categories,
        is_free=is_free
    )

    # Обновляем курс в базе данных
    updated_course = crud.update_course(
        db=db,
        course_id=course_id,
        course_update=course_update
    )

    # # После обновления курс снова отправляется на модерацию
    # if not current_user.is_admin:
    #     # Сбрасываем статус на "pending" только если обновление выполнил не администратор
    #     crud.update_course_status(
    #         db=db,
    #         course_id=course_id,
    #         status="pending",
    #         status_comment="Курс обновлен и ожидает повторной модерации"
    #     )

    return updated_course


@router.patch("/{course_id}/status", response_model=CourseDetail)
def update_course_status(
        course_id: int,
        status_update: CourseStatusUpdate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Обновление статуса курса (только для администраторов)
    """
    # Проверка прав доступа (администратор)
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Обновляем статус курса
    updated_course = crud.update_course_status(
        db=db,
        course_id=course_id,
        status=status_update.status,
        status_comment=status_update.status_comment
    )

    # Отправляем уведомление автору курса о результате модерации
    if status_update.status in ["approved", "rejected"]:
        # Получаем автора курса
        author = crud.get_user(db, user_id=course.author_id)
        if author and hasattr(author, 'email') and author.email:
            status_text = "одобрен" if status_update.status == "approved" else "отклонен"
            subject = f"Статус вашего курса '{course.title}' изменен"
            message = f"""
            Здравствуйте, {author.user_name}!

            Статус вашего курса "{course.title}" был изменен на "{status_text}".

            {f"Комментарий: {status_update.status_comment}" if status_update.status_comment else ""}

            С уважением,
            Администрация платформы
            """
            send_email(
                recipient_email=author.email,
                subject=subject,
                message=message
            )

    return updated_course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
        course_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Удаление курса (только для автора курса или администратора)
    """
    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Проверяем права доступа (автор курса или администратор)
    if course.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас недостаточно прав для выполнения этого действия"
        )

    # Удаляем курс
    crud.delete_course(db=db, course_id=course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Методы для работы с содержимым курса (главы, уроки, тесты)

@router.post("/{course_id}/chapters", response_model=CourseDetail)
def add_chapter(
        course_id: int,
        chapter_data: CourseChapterCreate,
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Добавление новой главы к курсу (только для автора курса или администратора)
    """
    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Проверяем права доступа (автор курса или администратор)
    # if course.author_id != current_user.id and not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Добавляем главу и получаем обновленный курс
    updated_course = crud.add_chapter_to_course(
        db=db,
        course_id=course_id,
        chapter=chapter_data
    )

    # После обновления контента курс снова отправляется на модерацию
    # if not current_user.is_admin:
    #     crud.update_course_status(
    #         db=db,
    #         course_id=course_id,
    #         status="pending",
    #         status_comment="Курс обновлен и ожидает повторной модерации"
    #     )

    return updated_course




@router.post("/{course_id}/chapters/{chapter_id}/lessons", response_model=CourseDetail)
async def add_lesson(
        course_id: int,
        chapter_id: int,
        title: str = Form(...),
        description: str = Form(...),
        order: int = Form(...),
        video_url: str = Form(...),  # Заменяем File на Form для получения ссылки
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Добавление нового урока к главе курса (только для автора курса или администратора)
    """
    # Проверяем существование курса и главы
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    chapter = crud.get_chapter(db, chapter_id=chapter_id)
    if not chapter or chapter.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Глава не найдена или не принадлежит указанному курсу"
        )

    # Проверка валидности URL (можно добавить)
    # if not is_valid_video_url(video_url):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Недопустимый формат ссылки на видео"
    #     )

    # Создаем новый урок
    lesson_data = CourseLessonCreate(
        title=title,
        description=description,
        video_url=video_url,  # Теперь просто передаем URL
        order=order,
        tests=[]
    )

    # Добавляем урок и получаем обновленный курс
    updated_course = crud.add_lesson_to_chapter(
        db=db,
        chapter_id=chapter_id,
        lesson=lesson_data
    )

    return updated_course

@router.post("/{course_id}/chapters/{chapter_id}/lessons/{lesson_id}/tests", response_model=CourseDetail)
async def add_test(
        course_id: int,
        chapter_id: int,
        lesson_id: int,
        question: str = Form(...),
        answers: List[str] = Form(...),
        correct_answers: List[int] = Form(...),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        # current_user=Depends(get_current_user)
):
    """
    Добавление нового теста к уроку (только для автора курса или администратора)
    """
    # Проверяем существование курса, главы и урока
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    chapter = crud.get_chapter(db, chapter_id=chapter_id)
    if not chapter or chapter.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Глава не найдена или не принадлежит указанному курсу"
        )

    lesson = crud.get_lesson(db, lesson_id=lesson_id)
    if not lesson or lesson.chapter_id != chapter_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Урок не найден или не принадлежит указанной главе"
        )

    # Проверяем права доступа (автор курса или администратор)
    # if course.author_id != current_user.id and not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="У вас недостаточно прав для выполнения этого действия"
    #     )

    # Проверяем корректность индексов правильных ответов
    if any(idx < 0 or idx >= len(answers) for idx in correct_answers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные индексы правильных ответов"
        )

    # Обрабатываем изображение, если оно было загружено
    image_path = None
    if image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        if not validate_file_extension(image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений (jpg, jpeg, png, gif)"
            )

        upload_dir = os.path.join("uploads", "courses", str(course_id), "tests")
        os.makedirs(upload_dir, exist_ok=True)
        image_path = await save_upload_file(image, upload_dir)

    # Создаем ответы на тест
    test_answers = []
    for i, answer_text in enumerate(answers):
        test_answers.append(CourseTestAnswerCreate(
            answer_text=answer_text,
            is_correct=(i in correct_answers)
        ))

    # Создаем новый тест
    test_data = CourseTestCreate(
        question=question,
        image=image_path,
        answers=test_answers
    )

    # Добавляем тест и получаем обновленный курс
    updated_course = crud.add_test_to_lesson(
        db=db,
        lesson_id=lesson_id,
        test=test_data
    )

    # После обновления контента курс снова отправляется на модерацию
    # if not current_user.is_admin:
    #     crud.update_course_status(
    #         db=db,
    #         course_id=course_id,
    #         status="pending",
    #         status_comment="Курс обновлен и ожидает повторной модерации"
    #     )

    return updated_course


# Методы для отслеживания прогресса пользователя

@router.get("/{course_id}/progress")
def get_course_progress(
        course_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Получение информации о прогрессе пользователя по курсу
    """
    # Проверяем существование курса
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Проверяем наличие записи на курс
    enrollment = crud.get_enrollment(db, user_id=current_user.id, course_id=course_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не записаны на этот курс"
        )

    # Получаем полную информацию о прогрессе
    progress_data = crud.get_enrollment_with_progress(db, current_user.id, course_id)
    if not progress_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Информация о прогрессе не найдена"
        )

    return progress_data



@router.post("/{course_id}/lessons/{lesson_id}/complete")
def complete_lesson(
        course_id: int,
        lesson_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Отметка урока как завершенного
    """
    # Проверяем существование курса и урока
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    lesson = crud.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Урок не найден"
        )

    # Проверяем, принадлежит ли урок указанному курсу
    chapter = crud.get_chapter(db, chapter_id=lesson.chapter_id)
    if chapter.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Урок не принадлежит указанному курсу"
        )

    # Проверяем наличие записи на курс
    enrollment = crud.get_enrollment(db, user_id=current_user.id, course_id=course_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не записаны на этот курс"
        )

    # Отмечаем урок как завершенный и обновляем общий прогресс
    progress_data = crud.complete_lesson(
        db=db,
        enrollment_id=enrollment.id,
        lesson_id=lesson_id
    )

    # Возвращаем полную информацию о прогрессе
    return progress_data


@router.post("/{course_id}/tests/{test_id}/submit", response_model=dict)
def submit_test_answers(
        course_id: int,
        test_id: int,
        answers: List[int],
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Отправка ответов на тест и проверка результатов
    """
    # Проверяем существование курса и теста
    course = crud.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    test = crud.get_test(db, test_id=test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест не найден"
        )

    # Проверяем, принадлежит ли тест уроку из указанного курса
    lesson = crud.get_lesson(db, lesson_id=test.lesson_id)
    chapter = crud.get_chapter(db, chapter_id=lesson.chapter_id)
    if chapter.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Тест не принадлежит указанному курсу"
        )

    # Проверяем наличие записи на курс
    enrollment = crud.get_enrollment(db, user_id=current_user.id, course_id=course_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не записаны на этот курс"
        )

    # Проверяем ответы и сохраняем результаты
    result = crud.submit_test_answers(
        db=db,
        enrollment_id=enrollment.id,
        test_id=test_id,
        answer_ids=answers
    )

    # ВАЖНО! Убедитесь, что функция возвращает result!
    return result


@router.get("/moderation/pending", response_model=List[CourseList])
def list_pending_courses(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    courses = db.query(Course).filter(Course.status == "pending").offset(skip).limit(limit).all()
    return courses


# ============================================
# Moderation Endpoints
# ============================================

@router.get("/admin/moderation/stats", response_model=ModerationStats)
def get_courses_moderation_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.COURSES, allow_read_only=True))
):
    """
    Get course moderation statistics.
    Shows total, pending, approved, and rejected course counts.
    """
    total = db.query(models.Course).count()
    pending = db.query(models.Course).filter(models.Course.moderation_status == 'pending').count()
    approved = db.query(models.Course).filter(models.Course.moderation_status == 'approved').count()
    rejected = db.query(models.Course).filter(models.Course.moderation_status == 'rejected').count()

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected
    }


@router.get("/admin/moderation/pending", response_model=List[CourseDetail])
def get_pending_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.COURSES, allow_read_only=True))
):
    """
    Get all pending courses awaiting moderation.
    Returns courses with moderation_status='pending'.
    """
    courses = db.query(models.Course).filter(
        models.Course.moderation_status == 'pending'
    ).offset(skip).limit(limit).all()

    return courses


@router.get("/admin/moderation/all-statuses", response_model=List[CourseDetail])
def get_all_courses_with_status(
    moderation_status: Optional[ModerationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_module_access(Module.COURSES, allow_read_only=True))
):
    """
    Get all courses with optional status filter.
    Admin endpoint - shows all courses regardless of moderation status.
    """
    query = db.query(models.Course)

    if moderation_status:
        query = query.filter(models.Course.moderation_status == moderation_status.value)

    courses = query.offset(skip).limit(limit).all()
    return courses


@router.post("/admin/moderation/{course_id}/approve", response_model=CourseDetail)
def approve_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.COURSES, Permission.UPDATE))
):
    """
    Approve a course.
    Changes moderation_status to 'approved' and records moderator info.
    """
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    course.moderation_status = 'approved'
    course.moderated_at = datetime.utcnow()
    course.moderated_by = current_admin.id

    db.commit()
    db.refresh(course)
    return course


@router.post("/admin/moderation/{course_id}/reject", response_model=CourseDetail)
def reject_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.COURSES, Permission.UPDATE))
):
    """
    Reject a course.
    Changes moderation_status to 'rejected' and records moderator info.
    """
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    course.moderation_status = 'rejected'
    course.moderated_at = datetime.utcnow()
    course.moderated_by = current_admin.id

    db.commit()
    db.refresh(course)
    return course


# ========== ADMIN CRUD ENDPOINTS WITH AUTO-APPROVAL ==========

@router.post("/admin/create", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
async def admin_create_course(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.COURSES, Permission.CREATE)),
    title: str = Form(...),
    description: str = Form(...),
    course_url: str = Form(...),
    language: str = Form(...),
    duration: int = Form(...),
    skills: str = Form(...),
    currency: str = Form(...),
    price: float = Form(...),
    level: Optional[str] = Form(None),
    is_free: bool = Form(False),
    categories: List[int] = Form([]),
    cover_image: Optional[UploadFile] = File(None),
    video_preview: Optional[str] = Form(None)
):
    """
    Admin: Create course with auto-approval for administrators/super_admins
    """
    # Create upload directory
    upload_dir = os.path.join("uploads", "courses")
    os.makedirs(upload_dir, exist_ok=True)

    # Save cover image if uploaded
    cover_image_path = None
    if cover_image:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        if not validate_file_extension(cover_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений (jpg, jpeg, png, gif)"
            )
        cover_image_path = await save_upload_file(cover_image, upload_dir)

    video_preview_path = video_preview

    # Create course data
    course_data = CourseCreate(
        title=title,
        description=description,
        course_url=course_url,
        language=language,
        duration=duration,
        skills=skills,
        currency=currency,
        price=price,
        level=level,
        cover_image=cover_image_path,
        video_preview=video_preview_path,
        categories=categories,
        is_free=is_free
    )

    # Create course with auto-approval logic
    course = crud.create_course(
        db=db,
        course=course_data,
        author_id=current_admin.id,
        admin_role=current_admin.role
    )

    return course


@router.put("/admin/{course_id}", response_model=CourseDetail)
async def admin_update_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(require_permission(Module.COURSES, Permission.UPDATE)),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    course_url: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    skills: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    level: Optional[str] = Form(None),
    is_free: Optional[bool] = Form(None),
    categories: Optional[List[int]] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    video_preview: Optional[str] = Form(None)
):
    """
    Admin: Update course with re-moderation logic for major field changes
    """
    # Check if course exists
    existing_course = crud.get_course(db, course_id=course_id)
    if not existing_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )

    # Handle cover image upload
    cover_image_path = None
    if cover_image:
        upload_dir = os.path.join("uploads", "courses")
        os.makedirs(upload_dir, exist_ok=True)

        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        if not validate_file_extension(cover_image.filename, allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Разрешены только файлы изображений (jpg, jpeg, png, gif)"
            )
        cover_image_path = await save_upload_file(cover_image, upload_dir)

    # Build update data
    course_update = CourseUpdate(
        title=title,
        description=description,
        course_url=course_url,
        language=language,
        duration=duration,
        skills=skills,
        currency=currency,
        price=price,
        level=level,
        cover_image=cover_image_path if cover_image else None,
        video_preview=video_preview,
        categories=categories,
        is_free=is_free
    )

    # Update course with re-moderation logic
    updated_course = crud.update_course(
        db=db,
        course_id=course_id,
        course_update=course_update,
        admin_id=current_admin.id,
        admin_role=current_admin.role
    )

    return updated_course



