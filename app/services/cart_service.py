from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import FREE_SHIPPING_THRESHOLD, SHIPPING_FEE, TAX_RATE
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.repositories.cart_repository import get_or_create_cart
from app.schemas.cart import CartItemRead, CartRead

CENT = Decimal("0.01")


def money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def get_cart_response(db: Session, user_id: int) -> CartRead:
    cart = get_or_create_cart(db, user_id)
    db.flush()
    db.commit()
    subtotal = Decimal("0.00")
    response_items = []
    for item in cart.items:
        product = item.product
        available = product.is_active and product.inventory >= item.quantity
        line_total = money(product.price * item.quantity) if available else Decimal("0.00")
        subtotal += line_total
        response_items.append(
            CartItemRead(
                id=item.id,
                product_id=product.id,
                name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                inventory=product.inventory,
                available=available,
                line_total=line_total,
            )
        )
    subtotal = money(subtotal)
    tax = money(subtotal * TAX_RATE)
    shipping = Decimal("0.00") if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE
    return CartRead(
        id=cart.id,
        items=response_items,
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        total=money(subtotal + tax + shipping),
    )


def add_cart_item(db: Session, user_id: int, product_id: int, quantity: int) -> CartRead:
    cart = get_or_create_cart(db, user_id)
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Product is not available")
    existing = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    )
    new_quantity = quantity + (existing.quantity if existing else 0)
    if new_quantity > product.inventory:
        raise HTTPException(status_code=409, detail="Requested quantity exceeds available inventory")
    if existing:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))
    db.commit()
    return get_cart_response(db, user_id)


def update_cart_item(db: Session, user_id: int, item_id: int, quantity: int) -> CartRead:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items))
        .where(Cart.user_id == user_id)
    )
    item = next((entry for entry in cart.items if entry.id == item_id), None) if cart else None
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if not item.product.is_active:
        raise HTTPException(status_code=409, detail="Product is no longer available")
    if quantity > item.product.inventory:
        raise HTTPException(status_code=409, detail="Requested quantity exceeds available inventory")
    item.quantity = quantity
    db.commit()
    return get_cart_response(db, user_id)


def remove_cart_item(db: Session, user_id: int, item_id: int) -> CartRead:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items))
        .where(Cart.user_id == user_id)
    )
    item = next((entry for entry in cart.items if entry.id == item_id), None) if cart else None
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return get_cart_response(db, user_id)


def clear_cart(db: Session, user_id: int) -> CartRead:
    cart = db.scalar(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
    )
    if cart is not None:
        cart.items.clear()
        db.commit()
    return get_cart_response(db, user_id)