from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_admin_user
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryRead:
    category = Category(name=data.name.strip(), description=data.description)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name already exists") from None
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
def list_categories(db: Annotated[Session, Depends(get_db)]) -> list[CategoryRead]:
    return list(db.scalars(select(Category).order_by(Category.name)))


@router.get("/{category_id}", response_model=CategoryRead)
def read_category(category_id: int, db: Annotated[Session, Depends(get_db)]) -> CategoryRead:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryRead:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "name" and value is None:
            raise HTTPException(status_code=422, detail="name cannot be null")
        setattr(category, field, value.strip() if field == "name" and value else value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name already exists") from None
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.scalar(select(Product.id).where(Product.category_id == category_id).limit(1)):
        raise HTTPException(status_code=409, detail="Category still has products")
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)