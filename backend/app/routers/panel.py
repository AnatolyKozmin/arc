"""Admin web panel router — password-based login, full CRUD."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Font
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/panel", tags=["panel"])
_security = HTTPBearer(auto_error=False)
_PANEL_SUBJECT = "panel_admin"


# ── Auth ──────────────────────────────────────────────────────────────────────

class PanelLoginRequest(BaseModel):
    username: str
    password: str


class PanelTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _make_panel_token() -> str:
    expire = datetime.utcnow() + timedelta(hours=12)
    return jwt.encode(
        {"sub": _PANEL_SUBJECT, "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


def require_panel(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> None:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
        if payload.get("sub") != _PANEL_SUBJECT:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid panel token")


@router.post("/login", response_model=PanelTokenResponse)
def panel_login(data: PanelLoginRequest):
    if data.username != settings.panel_username or data.password != settings.panel_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong credentials")
    return PanelTokenResponse(access_token=_make_panel_token())


# ── Stats ─────────────────────────────────────────────────────────────────────

class PanelStats(BaseModel):
    total_users: int
    registered_users: int
    total_products: int
    total_announcements: int
    total_achievements: int


@router.get("/stats", response_model=PanelStats)
def get_stats(_: None = Depends(require_panel), db: Session = Depends(get_db)):
    return PanelStats(
        total_users=db.query(models.User).count(),
        registered_users=db.query(models.User).filter(models.User.is_registered == True).count(),
        total_products=db.query(models.Product).filter(models.Product.is_active == True).count(),
        total_announcements=db.query(models.Announcement).filter(models.Announcement.is_active == True).count(),
        total_achievements=db.query(models.Achievement).filter(models.Achievement.is_active == True).count(),
    )


class RegistrationStatRow(BaseModel):
    label: str
    count: int


class RegistrationBreakdown(BaseModel):
    """Разбивка по полям анкеты только для is_registered = true."""

    registered_total: int
    by_university: List[RegistrationStatRow]
    by_course: List[RegistrationStatRow]


@router.get("/stats/registrations", response_model=RegistrationBreakdown)
def get_registration_breakdown(
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    reg_filter = models.User.is_registered == True
    registered_total = db.query(models.User).filter(reg_filter).count()

    uni_rows = (
        db.query(models.User.university, func.count(models.User.id))
        .filter(reg_filter)
        .group_by(models.User.university)
        .order_by(func.count(models.User.id).desc())
        .all()
    )
    by_university = [
        RegistrationStatRow(label=(u or "— не указан"), count=int(c))
        for u, c in uni_rows
    ]

    course_rows = (
        db.query(models.User.course, func.count(models.User.id))
        .filter(reg_filter)
        .group_by(models.User.course)
        .all()
    )
    course_rows.sort(key=lambda r: (r[0] is None, r[0] if r[0] is not None else 0))

    by_course: List[RegistrationStatRow] = []
    for course_val, cnt in course_rows:
        if course_val is None:
            label = "— курс не указан"
        else:
            label = f"{course_val} курс"
        by_course.append(RegistrationStatRow(label=label, count=int(cnt)))

    return RegistrationBreakdown(
        registered_total=registered_total,
        by_university=by_university,
        by_course=by_course,
    )


# ── Users ─────────────────────────────────────────────────────────────────────

class PanelUserOut(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    full_name: Optional[str]
    university: Optional[str]
    course: Optional[int]
    group: Optional[str]
    balance: int
    is_registered: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PanelBalanceUpdate(BaseModel):
    amount: int
    reason: str = "Начисление от администратора"


@router.get("/users", response_model=List[PanelUserOut])
def list_users(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    registered_only: bool = False,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    q = db.query(models.User)
    if registered_only:
        q = q.filter(models.User.is_registered == True)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.User.first_name.ilike(like)
            | models.User.last_name.ilike(like)
            | models.User.username.ilike(like)
            | models.User.full_name.ilike(like)
        )
    return q.order_by(models.User.balance.desc()).offset(skip).limit(limit).all()


@router.get("/users/export")
def export_users_xlsx(
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Выгрузка в .xlsx только тех, кто прошёл регистрацию на мероприятие (анкета в боте / мини-аппе, is_registered)."""
    users = (
        db.query(models.User)
        .filter(models.User.is_registered == True)
        .order_by(models.User.id.asc())
        .all()
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Регистрация на мероприятие"
    headers = [
        "ID",
        "Telegram ID",
        "Username",
        "Имя (TG)",
        "Фамилия (TG)",
        "ФИО (анкета)",
        "ВУЗ",
        "Курс",
        "Группа",
        "Аркоины",
        "Дата создания записи в боте",
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for u in users:
        created = ""
        if u.created_at:
            if hasattr(u.created_at, "strftime"):
                created = u.created_at.strftime("%Y-%m-%d %H:%M")
            else:
                created = str(u.created_at)
        ws.append(
            [
                u.id,
                u.telegram_id,
                u.username or "",
                u.first_name,
                u.last_name or "",
                u.full_name or "",
                u.university or "",
                u.course if u.course is not None else "",
                u.group or "",
                u.balance,
                created,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"arkadium-meropriyatie-zaregistrirovani-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.xlsx"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
        },
    )


class EnsureUserFromBot(BaseModel):
    """Создать или обновить пользователя по данным из Telegram (бот /start)."""
    telegram_id: int
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None


def _upsert_user_from_ensure(db: Session, data: EnsureUserFromBot) -> models.User:
    """Общая логика upsert для ensure и resolve по @username."""
    user = db.query(models.User).filter(models.User.telegram_id == data.telegram_id).first()
    if not user:
        user = models.User(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name or "Участник",
            last_name=data.last_name,
            qr_token=str(uuid.uuid4()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.username = data.username
        if data.first_name:
            user.first_name = data.first_name
        user.last_name = data.last_name
        if not user.qr_token:
            user.qr_token = str(uuid.uuid4())
        db.commit()
        db.refresh(user)
    return user


# Telegram: публичный @username, 5–32 символа, с буквы
TG_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$")


def _normalize_public_username(raw: str) -> str:
    s = (raw or "").strip().lstrip("@").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Укажите username")
    if not TG_USERNAME_RE.match(s):
        raise HTTPException(
            status_code=400,
            detail="Некорректный username (латиница, цифры, _, от 5 до 32 символов)",
        )
    return s


def _resolve_telegram_private_chat(username: str) -> Tuple[int, dict]:
    """Telegram Bot API getChat — работает для пользователя, если он хотя бы раз писал боту / нажал Start."""
    if not settings.bot_token or settings.bot_token == "test_bot_token":
        raise HTTPException(
            status_code=503,
            detail="BOT_TOKEN не задан в настройках бэкенда",
        )
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{settings.bot_token}/getChat",
            params={"chat_id": f"@{username}"},
            timeout=15.0,
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка сети к Telegram: {e}") from e
    payload = r.json()
    if not payload.get("ok"):
        err = str(payload.get("description", ""))
        if "not found" in err.lower() or payload.get("error_code") == 400:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Пользователь не найден. Он должен хотя бы раз нажать Start у этого бота "
                    "или написать ему — иначе Telegram не отдаёт профиль по @username."
                ),
            )
        raise HTTPException(status_code=502, detail=f"Telegram: {err}")
    chat = payload["result"]
    if chat.get("type") != "private":
        raise HTTPException(
            status_code=400,
            detail="Нужен @username участника (личный чат), не канал и не группа.",
        )
    tid = chat.get("id")
    if tid is None or not isinstance(tid, int):
        raise HTTPException(status_code=502, detail="Неожиданный ответ Telegram")
    return tid, chat


class EnsureUserByUsername(BaseModel):
    """Добавить участника по публичному @username (через Bot API getChat)."""
    username: str


@router.post("/users/ensure", response_model=PanelUserOut)
def ensure_user_from_bot(
    data: EnsureUserFromBot,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Upsert пользователя по telegram_id — вызывается ботом при /start."""
    return _upsert_user_from_ensure(db, data)


@router.post("/users/ensure-by-username", response_model=PanelUserOut)
def ensure_user_by_username(
    data: EnsureUserByUsername,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Upsert по @username: резолв ID через getChat, затем как ensure."""
    uname = _normalize_public_username(data.username)
    tid, chat = _resolve_telegram_private_chat(uname)
    payload = EnsureUserFromBot(
        telegram_id=tid,
        username=chat.get("username"),
        first_name=chat.get("first_name") or "",
        last_name=chat.get("last_name"),
    )
    return _upsert_user_from_ensure(db, payload)


_ALLOWED_UPLOAD_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _upload_dir() -> Path:
    p = Path(settings.upload_dir)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    _: None = Depends(require_panel),
):
    """Загрузка изображения для объявлений/товаров; возвращает URL для поля image_url."""
    orig = (file.filename or "").lower()
    ext = Path(orig).suffix
    if ext not in _ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимы файлы: {', '.join(sorted(_ALLOWED_UPLOAD_EXT))}",
        )
    max_b = settings.max_upload_mb * 1024 * 1024
    body = await file.read()
    if len(body) > max_b:
        raise HTTPException(status_code=413, detail=f"Файл больше {settings.max_upload_mb} МБ")

    name = f"{uuid.uuid4().hex}{ext}"
    dest = _upload_dir() / name
    dest.write_bytes(body)
    # Тот же origin, что и API (nginx проксирует /api/)
    return {"url": f"/api/uploads/{name}"}


@router.patch("/users/{user_id}/balance", response_model=PanelUserOut)
def update_balance(
    user_id: int,
    data: PanelBalanceUpdate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.balance = max(0, user.balance + data.amount)
    tx = models.Transaction(user_id=user.id, amount=data.amount, reason=data.reason, category="admin")
    db.add(tx)
    db.commit()
    db.refresh(user)
    return user


class PanelRegisterByTelegramBody(BaseModel):
    """Регистрация на проект из бота — те же поля, что PUT /users/me/register + имя из анкеты."""

    telegram_id: int
    username: Optional[str] = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=200)
    university: str = Field(..., min_length=1, max_length=200)
    course: int = Field(..., ge=1, le=12)
    group: str = Field(..., min_length=1, max_length=50)


@router.post("/users/register-by-telegram", response_model=PanelUserOut)
def register_profile_by_telegram(
    data: PanelRegisterByTelegramBody,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.telegram_id == data.telegram_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден. Нажми /start у бота.",
        )
    user.first_name = data.first_name.strip()
    user.last_name = (data.last_name or "").strip() or None
    if data.username is not None:
        user.username = data.username
    user.full_name = data.full_name.strip()
    user.university = data.university.strip()
    user.course = data.course
    user.group = data.group.strip()
    user.is_registered = True
    db.commit()
    db.refresh(user)
    return user


# ── Announcements ─────────────────────────────────────────────────────────────

@router.get("/announcements", response_model=List[schemas.AnnouncementOut])
def list_announcements(_: None = Depends(require_panel), db: Session = Depends(get_db)):
    return (
        db.query(models.Announcement)
        .order_by(models.Announcement.sort_order, models.Announcement.created_at.desc())
        .all()
    )


@router.post("/announcements", response_model=schemas.AnnouncementOut)
def create_announcement(
    data: schemas.AnnouncementCreate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ann = models.Announcement(**data.model_dump())
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.put("/announcements/{ann_id}", response_model=schemas.AnnouncementOut)
def update_announcement(
    ann_id: int,
    data: schemas.AnnouncementUpdate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ann = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(ann, k, v)
    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/announcements/{ann_id}")
def delete_announcement(
    ann_id: int,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ann = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(ann)
    db.commit()
    return {"ok": True}


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/products", response_model=List[schemas.ProductOut])
def list_products(_: None = Depends(require_panel), db: Session = Depends(get_db)):
    return db.query(models.Product).order_by(models.Product.id).all()


@router.post("/products", response_model=schemas.ProductOut)
def create_product(
    data: schemas.ProductCreate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    data: schemas.ProductUpdate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Not found")
    n_p = db.query(models.ProductPurchase).filter(
        models.ProductPurchase.product_id == product_id
    ).count()
    if n_p:
        raise HTTPException(
            status_code=400,
            detail="Есть покупки этого товара. Сними с продажи (неактивен), не удаляй карточку.",
        )
    db.delete(product)
    db.commit()
    return {"ok": True}


@router.get("/purchases", response_model=List[schemas.ProductPurchaseRow])
def list_product_purchases(
    skip: int = 0,
    limit: int = 300,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Кто и что купил (мини-апп магазин)."""
    rows = (
        db.query(models.ProductPurchase, models.User)
        .join(models.User, models.ProductPurchase.user_id == models.User.id)
        .order_by(models.ProductPurchase.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        schemas.ProductPurchaseRow(
            id=pur.id,
            created_at=pur.created_at,
            price_paid=pur.price_paid,
            product_id=pur.product_id,
            product_name=pur.product_name,
            user_id=u.id,
            telegram_id=u.telegram_id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            full_name=u.full_name,
        )
        for pur, u in rows
    ]


# ── Achievements ──────────────────────────────────────────────────────────────

@router.get("/achievements", response_model=List[schemas.AchievementOut])
def list_achievements(_: None = Depends(require_panel), db: Session = Depends(get_db)):
    return db.query(models.Achievement).order_by(models.Achievement.id).all()


@router.post("/achievements", response_model=schemas.AchievementOut)
def create_achievement(
    data: schemas.AchievementCreate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ach = models.Achievement(**data.model_dump())
    db.add(ach)
    db.commit()
    db.refresh(ach)
    return ach


@router.put("/achievements/{ach_id}", response_model=schemas.AchievementOut)
def update_achievement(
    ach_id: int,
    data: schemas.AchievementCreate,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ach = db.query(models.Achievement).filter(models.Achievement.id == ach_id).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(ach, k, v)
    db.commit()
    db.refresh(ach)
    return ach


@router.delete("/achievements/{ach_id}")
def delete_achievement(
    ach_id: int,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    ach = db.query(models.Achievement).filter(models.Achievement.id == ach_id).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(ach)
    db.commit()
    return {"ok": True}


class AssignAchievementRequest(BaseModel):
    user_id: int
    achievement_id: int


@router.post("/achievements/assign")
def assign_achievement(
    data: AssignAchievementRequest,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == data.user_id).first()
    ach = db.query(models.Achievement).filter(models.Achievement.id == data.achievement_id).first()
    if not user or not ach:
        raise HTTPException(status_code=404, detail="User or achievement not found")
    existing = db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == data.user_id,
        models.UserAchievement.achievement_id == data.achievement_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already assigned")
    ua = models.UserAchievement(user_id=data.user_id, achievement_id=data.achievement_id)
    db.add(ua)
    db.commit()
    return {"ok": True}


# ── QR Scan ───────────────────────────────────────────────────────────────────

class ScannedUserOut(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    full_name: Optional[str]
    university: Optional[str]
    course: Optional[int]
    group: Optional[str]
    balance: int
    character_id: Optional[int]
    photo_url: Optional[str]
    is_registered: bool
    qr_token: str

    class Config:
        from_attributes = True


@router.get("/scan/{identifier}", response_model=ScannedUserOut)
def scan_qr(
    identifier: str,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Look up user by telegram_id (from QR) or qr_token (legacy)."""
    user = None
    # Try telegram_id first (numeric string)
    if identifier.isdigit():
        user = db.query(models.User).filter(
            models.User.telegram_id == int(identifier)
        ).first()
    # Fallback: try qr_token UUID
    if not user:
        user = db.query(models.User).filter(models.User.qr_token == identifier).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


# ── Admins management ─────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: int
    telegram_id: int
    added_by: Optional[int]
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AddAdminRequest(BaseModel):
    telegram_id: int
    note: Optional[str] = None


@router.get("/admins", response_model=List[AdminUserOut])
def list_admins(_: None = Depends(require_panel), db: Session = Depends(get_db)):
    return db.query(models.AdminUser).order_by(models.AdminUser.created_at.desc()).all()


@router.post("/admins", response_model=AdminUserOut)
def add_admin(
    data: AddAdminRequest,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    existing = db.query(models.AdminUser).filter(
        models.AdminUser.telegram_id == data.telegram_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Уже является администратором")
    admin = models.AdminUser(telegram_id=data.telegram_id, note=data.note)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.delete("/admins/{telegram_id}")
def remove_admin(
    telegram_id: int,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    admin = db.query(models.AdminUser).filter(
        models.AdminUser.telegram_id == telegram_id
    ).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Не найден")
    db.delete(admin)
    db.commit()
    return {"ok": True}


# ── Tournament registrations (BS/CR — ник в игре; MK/FIFA — без ника) ─────────

_GAMES_WITH_NICK = frozenset({"brawl_stars", "clash_royale"})
_GAMES_NAME_ONLY = frozenset({"mortal_kombat", "fifa"})
_ALLOWED_GAMES = _GAMES_WITH_NICK | _GAMES_NAME_ONLY


def _normalize_game_username(raw: str) -> str:
    s = raw.strip()
    if len(s) < 2:
        raise ValueError("Ник в игре — минимум 2 символа")
    if len(s) > 64:
        raise ValueError("Ник в игре слишком длинный")
    return s


class TournamentBotRegister(BaseModel):
    telegram_id: int
    telegram_username: Optional[str] = None  # снимок @username из Telegram
    game: str
    game_username: Optional[str] = None  # для BS/CR обязателен; для MK/FIFA не используется


class PanelTournamentRow(BaseModel):
    id: int
    telegram_id: int
    telegram_username: Optional[str]  # снимок при записи
    first_name: str
    last_name: Optional[str]
    username: Optional[str]  # актуальный username из профиля User
    full_name: Optional[str]
    game: str
    game_username: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/tournaments/register", response_model=PanelTournamentRow)
def register_tournament_via_bot(
    data: TournamentBotRegister,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Регистрация от имени пользователя по telegram_id (вызывается ботом)."""
    if data.game not in _ALLOWED_GAMES:
        raise HTTPException(
            status_code=400,
            detail="game: brawl_stars, clash_royale, mortal_kombat или fifa",
        )
    if data.game in _GAMES_WITH_NICK:
        raw_nick = (data.game_username or "").strip()
        if not raw_nick:
            raise HTTPException(status_code=400, detail="Ник в игре обязателен для Brawl Stars и Clash Royale")
        try:
            nick = _normalize_game_username(raw_nick)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        nick = ""

    tg_un = (data.telegram_username or "").strip()
    if tg_un.startswith("@"):
        tg_un = tg_un[1:]
    if len(tg_un) > 100:
        tg_un = tg_un[:100]

    user = db.query(models.User).filter(models.User.telegram_id == data.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь ещё не заходил в мини-апп — откройте Аркадиум один раз")
    if data.game in _GAMES_NAME_ONLY and not user.is_registered:
        raise HTTPException(
            status_code=400,
            detail="Сначала зарегистрируйся на мероприятие (анкета в мини-приложении или в боте).",
        )

    existing = (
        db.query(models.TournamentRegistration)
        .filter(
            models.TournamentRegistration.user_id == user.id,
            models.TournamentRegistration.game == data.game,
        )
        .first()
    )
    if existing:
        existing.telegram_username = tg_un or None
        existing.game_username = nick
        existing.player_tag = nick  # совместимость со старыми отчётами
        db.commit()
        db.refresh(existing)
        reg = existing
    else:
        reg = models.TournamentRegistration(
            user_id=user.id,
            game=data.game,
            telegram_username=tg_un or None,
            game_username=nick,
            player_tag=nick,
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)

    display_nick = reg.game_username or reg.player_tag or ""

    return PanelTournamentRow(
        id=reg.id,
        telegram_id=user.telegram_id,
        telegram_username=reg.telegram_username,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        full_name=user.full_name,
        game=reg.game,
        game_username=display_nick,
        created_at=reg.created_at,
    )


@router.get("/tournaments", response_model=List[PanelTournamentRow])
def list_tournament_registrations(
    game: Optional[str] = None,
    limit: int = 500,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    q = db.query(models.TournamentRegistration)
    if game:
        if game not in _ALLOWED_GAMES:
            raise HTTPException(status_code=400, detail="Неверная игра")
        q = q.filter(models.TournamentRegistration.game == game)
    rows = (
        q.order_by(models.TournamentRegistration.created_at.desc()).limit(max(1, min(limit, 2000))).all()
    )
    out: List[PanelTournamentRow] = []
    for reg in rows:
        u = db.query(models.User).filter(models.User.id == reg.user_id).first()
        if not u:
            continue
        nick = reg.game_username or reg.player_tag or ""
        out.append(
            PanelTournamentRow(
                id=reg.id,
                telegram_id=u.telegram_id,
                telegram_username=reg.telegram_username,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                full_name=u.full_name,
                game=reg.game,
                game_username=nick,
                created_at=reg.created_at,
            )
        )
    return out
