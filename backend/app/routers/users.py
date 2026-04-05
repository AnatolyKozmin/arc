from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me/register", response_model=schemas.UserOut)
def register_user(
    data: schemas.UserRegisterRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = data.full_name
    current_user.university = data.university
    current_user.course = data.course
    current_user.group = data.group
    current_user.is_registered = True
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/character", response_model=schemas.UserOut)
def update_character(
    data: schemas.UserCharacterUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.character_id not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Invalid character id (1-4)")
    current_user.character_id = data.character_id
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=List[schemas.UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).offset(skip).limit(limit).all()


@router.get("/scan/{identifier}", response_model=schemas.UserOut)
def scan_user_qr(
    identifier: str,
    operator: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mini-app scan endpoint: look up user by telegram_id from QR code.
    Requires organizer or admin role."""
    if operator.role not in ("organizer", "admin"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = None
    if identifier.isdigit():
        user = db.query(models.User).filter(
            models.User.telegram_id == int(identifier)
        ).first()
    if not user:
        user = db.query(models.User).filter(models.User.qr_token == identifier).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/balance", response_model=schemas.UserOut)
def adjust_balance(
    user_id: int,
    data: schemas.AdminBalanceUpdate,
    operator: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if operator.role not in ("organizer", "admin"):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.balance + data.amount < 0:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance += data.amount
    transaction = models.Transaction(
        user_id=user.id,
        operator_id=operator.id,
        amount=data.amount,
        reason=data.reason,
        category="manual",
    )
    db.add(transaction)
    db.commit()
    db.refresh(user)
    return user
