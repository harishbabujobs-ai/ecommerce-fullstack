import os

from app.core.database import SessionLocal
from app.repositories.user_repository import get_user_by_email
from app.schemas.user import UserCreate
from app.services.user_service import register_user


def main() -> None:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    full_name = os.getenv("ADMIN_FULL_NAME", "Store Admin").strip()
    if not email or len(password) < 8:
        raise SystemExit("Set ADMIN_EMAIL and an ADMIN_PASSWORD of at least 8 characters in .env")

    with SessionLocal() as db:
        user = get_user_by_email(db, email)
        if user is None:
            user = register_user(
                db,
                UserCreate(email=email, full_name=full_name, password=password),
            )
        user.role = "admin"
        db.commit()
    print(f"Admin account ready: {email}")


if __name__ == "__main__":
    main()