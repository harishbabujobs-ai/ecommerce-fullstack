from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, enable_sqlite_foreign_keys, get_db
from app.main import app as fastapi_app
import app.models as models

_ = models.__all__

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
event.listen(test_engine, "connect", enable_sqlite_foreign_keys)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session() -> Iterator[Session]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


def register_user(client: TestClient, email: str = "customer@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Customer", "password": "correct-horse-42"},
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str = "customer@example.com") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-42"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def make_admin(db_session: Session, email: str = "customer@example.com") -> None:
    from app.models.user import User

    user = db_session.query(User).filter_by(email=email).one()
    user.role = "admin"
    db_session.commit()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}