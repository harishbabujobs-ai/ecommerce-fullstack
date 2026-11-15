from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    inventory: int = Field(ge=0)
    category_id: int = Field(gt=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    inventory: int | None = Field(default=None, ge=0)
    category_id: int | None = Field(default=None, gt=0)


class InventoryUpdate(BaseModel):
    inventory: int = Field(ge=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    inventory: int
    is_active: bool
    category_id: int
    created_at: datetime


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int