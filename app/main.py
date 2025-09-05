from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import experts, auth, vacancies, admin_auth_router, events, certificates, projects
from app.routers import courses_router
from app.database import engine, Base

# Импортируем модели проектов для создания таблиц
from app import project_models

import uvicorn
import os
from fastapi.staticfiles import StaticFiles

# Создание таблиц в базе данных (включая новые таблицы проектов)
Base.metadata.create_all(bind=engine)

# Инициализация FastAPI приложения
app = FastAPI(
    title="Experts Platform API",
    description="API для работы с экспертами на платформе",
    version="2.0.0"
)

# Настройка CORS - ВАЖНО: делается ДО подключения роутеров
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://js-front-git-main-meirlens-projects-05b45419.vercel.app",
    # Добавьте другие домены вашего фронтенда
]

app.add_middleware(
    CORSMiddleware,
    max_request_size=50 * 1024 * 1024,  # 50MB


    allow_origins=origins + ["*"],  # Для разработки можно оставить "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token",
        "X-API-Key"
    ],
    expose_headers=["*"]
)


# Добавляем обработчик для preflight запросов
@app.options("/{path:path}")
async def options_handler(request: Request, response: Response):
    return Response(
        content="",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600"
        }
    )


# Настройка статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/certificates", StaticFiles(directory="uploads"), name="certificates")
app.mount("/courses", StaticFiles(directory="uploads"), name="courses")

# Включение маршрутов - ПОСЛЕ настройки CORS
app.include_router(experts.router)
app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(events.router)
app.include_router(courses_router.router)
app.include_router(certificates.router)
app.include_router(projects.router)
app.include_router(admin_auth_router.router)


# Корневой маршрут
@app.get("/")
async def read_root():
    return {
        "message": "Добро пожаловать в API платформы экспертов",
        "version": "2.0.0",
        "documentation": "/docs",
        "new_features": ["Projects", "Voting", "Applications"],
        "cors_enabled": True
    }


# Middleware для добавления CORS заголовков ко всем ответам
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)

    # Добавляем CORS заголовки ко всем ответам
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
#Запуск:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

