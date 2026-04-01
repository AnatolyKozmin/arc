from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/me", response_model=List[schemas.TransactionOut])
def my_transactions(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user.id)
        .order_by(models.Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("", response_model=List[schemas.TransactionOut])
def all_transactions(
    user_id: int = None,
    skip: int = 0,
    limit: int = 100,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if user_id:
        q = q.filter(models.Transaction.user_id == user_id)
    return q.order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()
