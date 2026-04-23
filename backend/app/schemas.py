from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class TelegramAuthRequest(BaseModel):
    init_data: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ── User ──────────────────────────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    full_name: str
    university: str
    course: int
    group: str


class UserOut(BaseModel):
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
    role: str
    qr_token: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserCharacterUpdate(BaseModel):
    character_id: int


class AdminBalanceUpdate(BaseModel):
    amount: int
    reason: str


# ── Leaderboard ───────────────────────────────────────────────────────────────
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    telegram_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    photo_url: Optional[str]
    balance: int
    is_current_user: bool = False

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    current_user_rank: int


# ── Product ───────────────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: int
    quantity: int
    image_url: Optional[str] = None
    is_featured: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    quantity: Optional[int] = None
    image_url: Optional[str] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: int
    quantity: int
    image_url: Optional[str]
    is_active: bool
    is_featured: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseResult(BaseModel):
    """Ответ после успешной покупки в магазине."""
    balance: int
    product: ProductOut


class ProductPurchaseRow(BaseModel):
    """Строка для админки: кто что купил."""
    id: int
    created_at: datetime
    price_paid: int
    product_id: int
    product_name: str
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    full_name: Optional[str]

    class Config:
        from_attributes = True


# ── Transaction ───────────────────────────────────────────────────────────────
class TransactionCreate(BaseModel):
    user_id: int
    amount: int
    reason: str
    category: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    user_id: int
    operator_id: Optional[int]
    amount: int
    reason: str
    category: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Achievement ───────────────────────────────────────────────────────────────
class AchievementCreate(BaseModel):
    name: str
    description: Optional[str] = None
    coins_reward: int = 0
    icon: Optional[str] = None
    achievement_type: str = "manual"


class AchievementOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    coins_reward: int
    icon: Optional[str]
    achievement_type: str
    is_active: bool

    class Config:
        from_attributes = True


class UserAchievementOut(BaseModel):
    id: int
    achievement: AchievementOut
    is_claimed: bool
    completed_at: datetime
    claimed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Announcement ──────────────────────────────────────────────────────────────
class AnnouncementCreate(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_draft: bool = False
    sort_order: int = 0


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_draft: Optional[bool] = None
    sort_order: Optional[int] = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    image_url: Optional[str]
    is_active: bool
    is_draft: bool
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()
