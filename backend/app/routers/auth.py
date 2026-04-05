import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app import models, schemas
from app.auth import verify_telegram_init_data, create_access_token
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=schemas.TokenResponse)
def telegram_auth(payload: schemas.TelegramAuthRequest, db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(payload.init_data)
    if tg_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        )

    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Missing user id in initData")

    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        user = models.User(
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
            photo_url=tg_user.get("photo_url"),
            qr_token=str(uuid.uuid4()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Backfill qr_token for existing users that don't have one
        if not user.qr_token:
            user.qr_token = str(uuid.uuid4())
            db.commit()
            db.refresh(user)

    token = create_access_token(telegram_id)
    return schemas.TokenResponse(access_token=token, user=user)


class DevAuthRequest(BaseModel):
    telegram_id: int
    first_name: str = "Dev"
    last_name: Optional[str] = "User"
    username: Optional[str] = "devuser"
    role: str = "user"  # user | organizer | admin


@router.post("/dev", response_model=schemas.TokenResponse)
def dev_auth(payload: DevAuthRequest, db: Session = Depends(get_db)):
    """Dev-only endpoint — works only when DEV_MODE=true."""
    if not settings.dev_mode:
        raise HTTPException(status_code=403, detail="Dev mode is disabled")

    # Honor role override: inject telegram_id into admin/organizer lists at runtime
    if payload.role == "admin" and payload.telegram_id not in settings.admin_telegram_ids:
        settings.admin_telegram_ids.append(payload.telegram_id)
        if payload.telegram_id in settings.organizer_telegram_ids:
            settings.organizer_telegram_ids.remove(payload.telegram_id)
    elif payload.role == "organizer" and payload.telegram_id not in settings.organizer_telegram_ids:
        settings.organizer_telegram_ids.append(payload.telegram_id)
        if payload.telegram_id in settings.admin_telegram_ids:
            settings.admin_telegram_ids.remove(payload.telegram_id)
    else:
        # plain user — remove from elevated lists if was there
        settings.admin_telegram_ids = [i for i in settings.admin_telegram_ids if i != payload.telegram_id]
        settings.organizer_telegram_ids = [i for i in settings.organizer_telegram_ids if i != payload.telegram_id]

    user = db.query(models.User).filter(models.User.telegram_id == payload.telegram_id).first()
    if not user:
        user = models.User(
            telegram_id=payload.telegram_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            username=payload.username,
            qr_token=str(uuid.uuid4()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.first_name = payload.first_name
        user.last_name = payload.last_name
        user.username = payload.username
        if not user.qr_token:
            user.qr_token = str(uuid.uuid4())
        db.commit()
        db.refresh(user)

    token = create_access_token(payload.telegram_id)
    return schemas.TokenResponse(access_token=token, user=user)
