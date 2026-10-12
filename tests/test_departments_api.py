import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.database import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.models.user import User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def set_user_role(role: str):
    fastapi_app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password-hash",
        role=role,
        is_active=True,
    )


def test_department_list_requires_authentication(client: TestClient):
    response = client.get("/api/v1/departments")
    assert response.status_code == 401


def test_admin_can_create_department(client: TestClient):
    set_user_role("ADMIN")

    response = client.post(
        "/api/v1/departments",
        json={
            "name": "Water Supply",
            "description": "Water service requests",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Water Supply"


def test_citizen_cannot_create_department(client: TestClient):
    set_user_role("CITIZEN")

    response = client.post(
        "/api/v1/departments",
        json={"name": "Road Maintenance"},
    )

    assert response.status_code == 403


def test_duplicate_department_returns_409(client: TestClient):
    set_user_role("ADMIN")

    payload = {"name": "Electricity"}

    first = client.post("/api/v1/departments", json=payload)
    second = client.post("/api/v1/departments", json=payload)

    assert first.status_code == 201, first.text
    assert second.status_code == 409
