from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import Base, engine
from app.routers import auth, users, leaderboard, products, transactions, achievements, announcements, panel
from app import models  # noqa: F401 – registers all models for table creation

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Аркадиум API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(achievements.router, prefix="/api")
app.include_router(announcements.router, prefix="/api")
app.include_router(panel.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Аркадиум"}


# Seed demo data if DB is empty
@app.on_event("startup")
def seed_demo_data():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(models.Announcement).count() == 0:
            announcements_data = [
                models.Announcement(
                    title="Аркадиум",
                    description="Масштабная интерактивная выставка, на которой участники смогут погрузиться в игровые эпохи и миры. 23 апреля!",
                    sort_order=1,
                ),
                models.Announcement(
                    title="Зоны проекта",
                    description="— Зона активных игр\n— Зона интерактивов\n— Зона консольных игр\n— Зона турниров",
                    sort_order=2,
                ),
                models.Announcement(
                    title="Аркоины",
                    description="За каждую активность накапливай аркоины и обменивай их на призы от спонсоров!",
                    sort_order=3,
                ),
            ]
            db.add_all(announcements_data)

        if db.query(models.Product).count() == 0:
            products_data = [
                models.Product(name="Футболка с Аркавриком", price=700, quantity=15, is_featured=True,
                               description="Крутая футболка с символикой Аркадиума. Ограниченная серия!"),
                models.Product(name="Портативная колонка", price=1500, quantity=5, is_featured=True,
                               description="Компактная bluetooth-колонка. Отличный приз за активность!"),
                models.Product(name="Стикерпак Аркадиум", price=200, quantity=50, is_featured=False,
                               description="Набор стикеров с персонажами Аркадиума"),
                models.Product(name="Кружка игровая", price=400, quantity=20, is_featured=False,
                               description="Кружка с принтом 8-bit"),
                models.Product(name="Значок коллекционный", price=100, quantity=100, is_featured=False,
                               description="Металлический значок с символикой выставки"),
            ]
            db.add_all(products_data)

        if db.query(models.Achievement).count() == 0:
            achievements_data = [
                models.Achievement(name="Первый шаг", description="Зарегистрировался в приложении",
                                   coins_reward=50, icon="👋", achievement_type="auto"),
                models.Achievement(name="Пришёл на мероприятие", description="Посетил Аркадиум 23 апреля",
                                   coins_reward=200, icon="🎮", achievement_type="auto"),
                models.Achievement(name="Чемпион турнира", description="Выиграл турнир",
                                   coins_reward=500, icon="🏆", achievement_type="manual"),
                models.Achievement(name="Коллекционер", description="Посетил все зоны проекта",
                                   coins_reward=300, icon="⭐", achievement_type="auto"),
                models.Achievement(name="Лучший косплей", description="Победил в конкурсе косплея",
                                   coins_reward=400, icon="🎭", achievement_type="manual"),
            ]
            db.add_all(achievements_data)

        db.commit()
    finally:
        db.close()
