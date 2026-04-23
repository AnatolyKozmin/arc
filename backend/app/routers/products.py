from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, update
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db

router = APIRouter(prefix="/products", tags=["products"])


def _product_in_shop(p: models.Product) -> bool:
    """Как в list_products: показываем активные и с is_active=NULL (старые строки)."""
    return p.is_active is not False


@router.post("/{product_id}/purchase", response_model=schemas.PurchaseResult)
def purchase_product(
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Списать аркоины, уменьшить остаток, записать покупку и транзакцию (атомарно, без гонок)."""
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not _product_in_shop(product):
        raise HTTPException(status_code=400, detail="Товар недоступен")
    if product.quantity <= 0:
        raise HTTPException(status_code=400, detail="Нет в наличии")

    price = product.price
    name = product.name
    tbl_p = models.Product.__table__
    r_stock = db.execute(
        update(tbl_p)
        .where(
            and_(
                tbl_p.c.id == product_id,
                tbl_p.c.quantity > 0,
                or_(tbl_p.c.is_active.is_(None), tbl_p.c.is_active == True),  # noqa: E712
            )
        )
        .values(quantity=tbl_p.c.quantity - 1)
    )
    if r_stock.rowcount != 1:
        raise HTTPException(status_code=400, detail="Нет в наличии")

    tbl_u = models.User.__table__
    r_bal = db.execute(
        update(tbl_u)
        .where(
            and_(
                tbl_u.c.id == current_user.id,
                tbl_u.c.balance >= price,
            )
        )
        .values(balance=tbl_u.c.balance - price)
    )
    if r_bal.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Недостаточно аркоинов")

    db.add(
        models.Transaction(
            user_id=current_user.id,
            operator_id=None,
            amount=-price,
            reason=f"Покупка: {name}",
            category="shop",
        )
    )
    db.add(
        models.ProductPurchase(
            user_id=current_user.id,
            product_id=product_id,
            price_paid=price,
            product_name=name,
        )
    )
    db.commit()
    db.refresh(current_user)
    db.refresh(product)
    return schemas.PurchaseResult(balance=current_user.balance, product=product)


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
    if not product or not _product_in_shop(product):
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
