from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import FREE_SHIPPING_THRESHOLD, SHIPPING_FEE, TAX_RATE
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.repositories.order_repository import get_order_for_user, list_orders_for_user
from app.services.cart_service import money
from app.services.payment_service import process_mock_payment


def checkout(db: Session, user_id: int) -> Order:
    try:
        cart = db.scalar(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.user_id == user_id)
        )
        if cart is None or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        for item in cart.items:
            if not item.product.is_active:
                raise HTTPException(status_code=409, detail=f"{item.product.name} is unavailable")
            if item.quantity > item.product.inventory:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient inventory for {item.product.name}",
                )

        subtotal = money(sum((item.product.price * item.quantity for item in cart.items), Decimal("0.00")))
        tax = money(subtotal * TAX_RATE)
        shipping = Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE
        total = money(subtotal + tax + shipping)
        process_mock_payment(total)
        order = Order(
            user_id=user_id,
            status="paid",
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=total,
        )
        db.add(order)
        db.flush()

        for item in cart.items:
            result = db.execute(
                update(Product)
                .where(
                    Product.id == item.product_id,
                    Product.is_active.is_(True),
                    Product.inventory >= item.quantity,
                )
                .values(inventory=Product.inventory - item.quantity)
            )
            if result.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail=f"Inventory changed during checkout for {item.product.name}",
                )
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name=item.product.name,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    line_total=money(item.product.price * item.quantity),
                )
            )
        cart.items.clear()
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def get_user_order(db: Session, order_id: int, user_id: int) -> Order:
    order = get_order_for_user(db, order_id, user_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def get_user_orders(db: Session, user_id: int) -> list[Order]:
    return list_orders_for_user(db, user_id)


def update_order_status(db: Session, order_id: int, new_status: str) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=409, detail="This order can no longer be changed")
    if new_status == "cancelled":
        for item in order.items:
            if item.product_id is not None:
                db.execute(
                    update(Product)
                    .where(Product.id == item.product_id)
                    .values(inventory=Product.inventory + item.quantity)
                )
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order