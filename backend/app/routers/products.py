from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=List[schemas.ProductOut])
def list_products(
    featured_only: bool = False,
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Product).filter(
        or_(models.Product.is_active == True, models.Product.is_active.is_(None))
    )
    if featured_only:
        q = q.filter(models.Product.is_featured == True)
    return q.order_by(models.Product.is_featured.desc(), models.Product.id).all()


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(
    product_id: int,
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=schemas.ProductOut)
def create_product(
    data: schemas.ProductCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    data: schemas.ProductUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    return {"ok": True}
