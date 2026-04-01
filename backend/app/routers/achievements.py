from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("", response_model=List[schemas.AchievementOut])
def list_achievements(
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(models.Achievement).filter(models.Achievement.is_active == True).all()


@router.get("/me", response_model=List[schemas.UserAchievementOut])
def my_achievements(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == current_user.id)
        .all()
    )


@router.post("/me/{achievement_id}/claim", response_model=schemas.UserAchievementOut)
def claim_achievement(
    achievement_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ua = (
        db.query(models.UserAchievement)
        .filter(
            models.UserAchievement.user_id == current_user.id,
            models.UserAchievement.achievement_id == achievement_id,
        )
        .first()
    )
    if not ua:
        raise HTTPException(status_code=404, detail="Achievement not found for this user")
    if ua.is_claimed:
        raise HTTPException(status_code=400, detail="Already claimed")

    ua.is_claimed = True
    ua.claimed_at = datetime.utcnow()
    current_user.balance += ua.achievement.coins_reward

    transaction = models.Transaction(
        user_id=current_user.id,
        amount=ua.achievement.coins_reward,
        reason=f"Достижение: {ua.achievement.name}",
        category="achievement",
    )
    db.add(transaction)
    db.commit()
    db.refresh(ua)
    return ua


@router.post("/{user_id}/grant/{achievement_id}")
def grant_achievement(
    user_id: int,
    achievement_id: int,
    operator: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if operator.role not in ("organizer", "admin"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    achievement = db.query(models.Achievement).filter(models.Achievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    existing = (
        db.query(models.UserAchievement)
        .filter(
            models.UserAchievement.user_id == user_id,
            models.UserAchievement.achievement_id == achievement_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already granted")

    ua = models.UserAchievement(user_id=user_id, achievement_id=achievement_id)
    db.add(ua)
    db.commit()
    return {"ok": True}


@router.post("", response_model=schemas.AchievementOut)
def create_achievement(
    data: schemas.AchievementCreate,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    a = models.Achievement(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a
