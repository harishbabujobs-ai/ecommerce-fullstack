from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_admin_user, get_current_user
from app.models.user import User
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.services.order_service import (
    checkout,
    get_user_order,
    get_user_orders,
    update_order_status,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/checkout", response_model=OrderRead, status_code=201)
def create_order(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrderRead:
    return checkout(db, current_user.id)


@router.get("", response_model=list[OrderRead])
def list_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrderRead]:
    return get_user_orders(db, current_user.id)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrderRead:
    return get_user_order(db, order_id, current_user.id)


@router.patch("/{order_id}/status", response_model=OrderRead)
def change_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrderRead:
    return update_order_status(db, order_id, data.status)