from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemRead(BaseModel):
    id: int
    product_id: int
    name: str
    unit_price: Decimal
    quantity: int
    inventory: int
    available: bool
    line_total: Decimal


class CartRead(BaseModel):
    id: int
    items: list[CartItemRead]
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal