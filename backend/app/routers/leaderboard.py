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
        .limit(100)
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

    top7 = [e for e in ranked[:7]]
    user_entry = next((e for e in ranked if e.user_id == current_user.id), None)

    if user_entry and user_entry.rank <= 7:
        entries = ranked[:8] if len(ranked) >= 8 else ranked
    else:
        entries = top7
        if user_entry:
            entries = entries + [user_entry]

    return schemas.LeaderboardResponse(entries=entries, current_user_rank=current_rank)
