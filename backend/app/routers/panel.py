"""Admin web panel router — password-based login, full CRUD."""
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
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
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    q = db.query(models.User)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.User.first_name.ilike(like)
            | models.User.last_name.ilike(like)
            | models.User.username.ilike(like)
            | models.User.full_name.ilike(like)
        )
    return q.order_by(models.User.balance.desc()).offset(skip).limit(limit).all()


class EnsureUserFromBot(BaseModel):
    """Создать или обновить пользователя по данным из Telegram (бот /start)."""
    telegram_id: int
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None


@router.post("/users/ensure", response_model=PanelUserOut)
def ensure_user_from_bot(
    data: EnsureUserFromBot,
    _: None = Depends(require_panel),
    db: Session = Depends(get_db),
):
    """Upsert пользователя по telegram_id — вызывается ботом при /start."""
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
    db.delete(product)
    db.commit()
    return {"ok": True}


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


# ── Tournament registrations (Brawl Stars / Clash Royale) ───────────────────────

_ALLOWED_GAMES = frozenset({"brawl_stars", "clash_royale"})


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
    game_username: str  # ник в игре (из сообщения)


class PanelTournamentRow(BaseModel):
    id: int
    telegram_id: int
    telegram_username: Optional[str]  # снимок при записи
    first_name: str
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
        raise HTTPException(status_code=400, detail="game: ожидается brawl_stars или clash_royale")
    try:
        nick = _normalize_game_username(data.game_username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tg_un = (data.telegram_username or "").strip()
    if tg_un.startswith("@"):
        tg_un = tg_un[1:]
    if len(tg_un) > 100:
        tg_un = tg_un[:100]

    user = db.query(models.User).filter(models.User.telegram_id == data.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь ещё не заходил в мини-апп — откройте Аркадиум один раз")

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
                username=u.username,
                full_name=u.full_name,
                game=reg.game,
                game_username=nick,
                created_at=reg.created_at,
            )
        )
    return out
