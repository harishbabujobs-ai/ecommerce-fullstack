from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import get_user_by_email
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_profile(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return current_user


@router.put("/me", response_model=UserRead)
def update_profile(
    data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserRead:
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes:
        email = str(changes["email"]).lower()
        existing = get_user_by_email(db, email)
        if existing is not None and existing.id != current_user.id:
            raise HTTPException(status_code=409, detail="Email is already registered")
        current_user.email = email
    if changes.get("full_name") is not None:
        current_user.full_name = changes["full_name"].strip()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    current_user.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)