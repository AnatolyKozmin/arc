from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=schemas.LeaderboardResponse)
def get_leaderboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    top_users = (
        db.query(models.User)
        .order_by(models.User.balance.desc())
        .all()
    )

    ranked = [
        schemas.LeaderboardEntry(
            rank=idx + 1,
            user_id=u.id,
            telegram_id=u.telegram_id,
            first_name=u.first_name,
            last_name=u.last_name,
            username=u.username,
            photo_url=u.photo_url,
            balance=u.balance,
            is_current_user=(u.id == current_user.id),
        )
        for idx, u in enumerate(top_users)
    ]

    current_rank = next((e.rank for e in ranked if e.user_id == current_user.id), len(ranked) + 1)

    return schemas.LeaderboardResponse(entries=ranked, current_user_rank=current_rank)
