# Добавьте следующие строки в ваш main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import experts, auth, vacancies,admin_auth_router, events, certificates, projects  # Добавить projects
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

# Настройка статических файлов (добавить новые директории)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/certificates", StaticFiles(directory="uploads"), name="uploads")
app.mount("/courses", StaticFiles(directory="uploads"), name="uploads")

# Настройка CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:8000",
    "https://example.com",
    "https://js-front-git-main-meirlens-projects-05b45419.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",          # можно указать ["*"] для теста
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Включение маршрутов (добавить projects)
app.include_router(experts.router)
app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(events.router)
app.include_router(courses_router.router)
app.include_router(certificates.router)
app.include_router(projects.router)  # Новая строка
app.include_router(admin_auth_router.router)  # Новая строка

# Корневой маршрут
@app.get("/")
def read_root():
    return {
        "message": "Добро пожаловать в API платформы экспертов",
        "version": "2.0.0",
        "documentation": "/docs",
        "new_features": ["Projects", "Voting", "Applications"]  # Можно добавить для информации
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

#Запуск:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

