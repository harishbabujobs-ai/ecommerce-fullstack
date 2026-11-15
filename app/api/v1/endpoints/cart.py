from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartRead
from app.services.cart_service import (
    add_cart_item,
    clear_cart,
    get_cart_response,
    remove_cart_item,
    update_cart_item,
)

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartRead)
def get_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CartRead:
    return get_cart_response(db, current_user.id)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_200_OK)
def add_item(
    data: CartItemCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CartRead:
    return add_cart_item(db, current_user.id, data.product_id, data.quantity)


@router.patch("/items/{item_id}", response_model=CartRead)
def edit_item(
    item_id: int,
    data: CartItemUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CartRead:
    return update_cart_item(db, current_user.id, item_id, data.quantity)


@router.delete("/items/{item_id}", response_model=CartRead)
def delete_item(
    item_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CartRead:
    return remove_cart_item(db, current_user.id, item_id)


@router.delete("", response_model=CartRead)
def delete_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CartRead:
    return clear_cart(db, current_user.id)