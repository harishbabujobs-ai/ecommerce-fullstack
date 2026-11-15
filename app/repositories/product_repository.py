from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def list_products(
    db: Session,
    *,
    search: str | None,
    category_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    limit: int,
    offset: int,
) -> tuple[list[Product], int]:
    filters = [Product.is_active.is_(True)]
    if search:
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(Product.name.ilike(search_pattern), Product.description.ilike(search_pattern))
        )
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)

    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    products = list(
        db.scalars(
            select(Product)
            .where(*filters)
            .order_by(Product.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return products, total