from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.repositories.product_repository import get_product
from app.schemas.product import ProductCreate, ProductUpdate


def require_product(db: Session, product_id: int, *, include_inactive: bool = False) -> Product:
    product = get_product(db, product_id)
    if product is None or (not include_inactive and not product.is_active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def require_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def create_product(db: Session, data: ProductCreate) -> Product:
    require_category(db, data.category_id)
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = require_product(db, product_id, include_inactive=True)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "price", "inventory", "category_id"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    if changes.get("category_id") is not None:
        require_category(db, changes["category_id"])
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def set_inventory(db: Session, product_id: int, quantity: int) -> Product:
    product = require_product(db, product_id, include_inactive=True)
    product.inventory = quantity
    db.commit()
    db.refresh(product)
    return product


def deactivate_product(db: Session, product_id: int) -> None:
    product = require_product(db, product_id, include_inactive=True)
    product.is_active = False
    db.commit()