from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart


def get_cart_for_user(db: Session, user_id: int) -> Cart | None:
    return db.scalar(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
    )


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = get_cart_for_user(db, user_id)
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    return cart