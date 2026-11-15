from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_admin_user
from app.models.user import User
from app.repositories.product_repository import list_products
from app.schemas.product import (
    InventoryUpdate,
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)
from app.services.product_service import (
    create_product,
    deactivate_product,
    require_product,
    set_inventory,
    update_product,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def add_product(
    data: ProductCreate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return create_product(db, data)


@router.get("", response_model=ProductPage)
def get_products(
    db: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    category_id: int | None = Query(default=None, gt=0),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductPage:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price")
    items, total = list_products(
        db,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset,
    )
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Annotated[Session, Depends(get_db)]) -> ProductRead:
    return require_product(db, product_id)


@router.put("/{product_id}", response_model=ProductRead)
def edit_product(
    product_id: int,
    data: ProductUpdate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return update_product(db, product_id, data)


@router.patch("/{product_id}/inventory", response_model=ProductRead)
def edit_inventory(
    product_id: int,
    data: InventoryUpdate,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProductRead:
    return set_inventory(db, product_id, data.inventory)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    deactivate_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)