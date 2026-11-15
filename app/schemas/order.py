from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class OrderItemRead(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderRead(BaseModel):
    id: int
    status: str
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal
    created_at: datetime
    items: list[OrderItemRead]


class OrderStatusUpdate(BaseModel):
    status: Literal["processing", "shipped", "delivered", "cancelled"]