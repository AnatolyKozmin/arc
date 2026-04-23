# Аркадиум — Telegram Mini App

Telegram Mini App для интерактивной выставки **Аркадиум 2026**.

## Стек

| | Технология |
|---|---|
| Frontend | Vue 3 + Vite + Pinia + Vue Router |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Deploy | Docker Compose |

## Структура

```
ARKADIUM/
├── frontend/        # Vue 3 Mini App
│   ├── src/
│   │   ├── views/   # HomeView, TopView, ShopView, ProfileView
│   │   ├── components/
│   │   ├── stores/  # Pinia stores
│   │   └── api/     # axios client
│   └── ...
└── backend/         # FastAPI
    └── app/
        ├── routers/ # auth, users, products, leaderboard, achievements, announcements
        ├── models.py
        ├── schemas.py
        └── main.py
```

## Быстрый старт

### 1. Настройка

```bash
cp backend/.env.example backend/.env
# Заполните BOT_TOKEN, SECRET_KEY, ADMIN_TELEGRAM_IDS
```

### 2. Backend (локально)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполните переменные
uvicorn app.main:app --reload
# API docs: http://localhost:8000/api/docs
```

### 3. Frontend (локально)

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### 4. Docker Compose (продакшн)

```bash
cp .env.example .env
# DOMAIN, SITE_SLUG, BOT_TOKEN, SECRET_KEY, …
docker network create arkadium_shared  # один раз; TLS/80/443 — отдельно, см. infra/README.md
docker compose up -d --build
```

Файл **`.env`** в корне репозитория Docker Compose подставляет в `docker-compose.yml` сам; отдельный `--env-file` не нужен.

Корневой `docker-compose.yml` поднимает только **frontend, backend, bot** в сети `arkadium_shared` (встроенного nginx в этом файле **нет**).

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram бота от @BotFather |
| `SECRET_KEY` | Секретный ключ для JWT (сгенерируйте случайный) |
| `DATABASE_URL` | URL базы данных (SQLite по умолчанию) |
| `ADMIN_TELEGRAM_IDS` | Telegram ID администраторов через запятую |
| `ORGANIZER_TELEGRAM_IDS` | Telegram ID организаторов через запятую |
| `CORS_ORIGINS` | Разрешённые CORS домены через запятую |

## Роли пользователей

- **user** — обычный участник
- **organizer** — может начислять/списывать аркоины, управлять товарами
- **admin** — полный доступ, управление анонсами и достижениями

Роли задаются через `ADMIN_TELEGRAM_IDS` и `ORGANIZER_TELEGRAM_IDS` в `.env`.

## API

После запуска: `http://localhost:8000/api/docs` — интерактивная документация.

### Основные эндпоинты

```
POST /api/auth/telegram       — авторизация через Telegram initData
GET  /api/users/me            — текущий пользователь
PUT  /api/users/me/register   — регистрация (ФИО, ВУЗ, курс, группа)
PUT  /api/users/me/character  — выбор персонажа (1-4)
GET  /api/leaderboard         — топ + позиция пользователя
GET  /api/products            — список товаров
GET  /api/announcements       — объявления
GET  /api/achievements/me     — достижения пользователя
POST /api/achievements/me/{id}/claim — забрать награду за достижение
```

## Экраны приложения

1. **Главная** — баланс аркоинов, объявления (автослайдер 6-7с), горячие предложения
2. **Топ** — подиум топ-3 + рейтинг, позиция пользователя всегда видна
3. **Магазин** — все товары с ценой и остатком, описание по клику
4. **Профиль** — выбор персонажа (4 варианта), достижения с кнопкой "Забрать"

## Настройка в Telegram

1. Создайте бота через @BotFather
2. `/newapp` — создайте Mini App и укажите URL деплоя
3. Укажите токен бота в `.env`
