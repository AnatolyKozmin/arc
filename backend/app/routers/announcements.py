from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=List[schemas.AnnouncementOut])
def list_announcements(
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # NULL в старых SQLite-строках: == False / == True их не matche'ит, список получался пустой.
    return (
        db.query(models.Announcement)
        .filter(
            or_(models.Announcement.is_active == True, models.Announcement.is_active.is_(None)),
            or_(models.Announcement.is_draft == False, models.Announcement.is_draft.is_(None)),
        )
        .order_by(models.Announcement.sort_order, models.Announcement.created_at.desc())
        .all()
    )


@router.get("/all", response_model=List[schemas.AnnouncementOut])
def list_all_announcements(
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Announcement)
        .order_by(models.Announcement.sort_order, models.Announcement.created_at.desc())
        .all()
    )


@router.post("", response_model=schemas.AnnouncementOut)
def create_announcement(
    data: schemas.AnnouncementCreate,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    a = models.Announcement(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.put("/{ann_id}", response_model=schemas.AnnouncementOut)
def update_announcement(
    ann_id: int,
    data: schemas.AnnouncementUpdate,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ann = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ann, field, value)
    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/{ann_id}")
def delete_announcement(
    ann_id: int,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ann = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    ann.is_active = False
    db.commit()
    return {"ok": True}
