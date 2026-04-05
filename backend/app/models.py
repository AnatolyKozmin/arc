import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AdminUser(Base):
    """Admins managed via the web panel (in addition to .env ADMIN_TELEGRAM_IDS)."""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    added_by = Column(Integer, nullable=True)  # telegram_id of who added
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    university = Column(String(200), nullable=True)
    course = Column(Integer, nullable=True)
    group = Column(String(50), nullable=True)
    balance = Column(Integer, default=0, nullable=False)
    character_id = Column(Integer, nullable=True)
    photo_url = Column(String(500), nullable=True)
    is_registered = Column(Boolean, default=False)
    qr_token = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    transactions = relationship("Transaction", back_populates="user", foreign_keys="Transaction.user_id")
    user_achievements = relationship("UserAchievement", back_populates="user")

    @property
    def role(self):
        from app.config import settings
        from app.database import SessionLocal
        if self.telegram_id in settings.admin_telegram_ids:
            return "admin"
        # Check DB admins
        try:
            db = SessionLocal()
            is_db_admin = db.query(AdminUser).filter(
                AdminUser.telegram_id == self.telegram_id
            ).first() is not None
            db.close()
            if is_db_admin:
                return "admin"
        except Exception:
            pass
        if self.telegram_id in settings.organizer_telegram_ids:
            return "organizer"
        return "user"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    operator = relationship("User", foreign_keys=[operator_id])


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    coins_reward = Column(Integer, default=0, nullable=False)
    icon = Column(String(100), nullable=True)
    achievement_type = Column(String(50), default="manual")  # auto / manual
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    is_claimed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    claimed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_draft = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
