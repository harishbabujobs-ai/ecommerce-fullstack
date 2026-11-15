from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import LoginRequest, TokenRead, UserCreate, UserRead
from app.services.security_service import create_access_token
from app.services.user_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> UserRead:
    return register_user(db, data)


@router.post("/login", response_model=TokenRead)
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenRead:
    user = authenticate_user(db, str(data.email), data.password)
    return TokenRead(access_token=create_access_token(user.id))