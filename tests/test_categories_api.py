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
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
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


def test_category_list_requires_authentication(client: TestClient):
    response = client.get("/api/v1/categories")

    assert response.status_code == 401


def test_admin_can_create_category(client: TestClient):
    set_user_role("ADMIN")

    response = client.post(
        "/api/v1/categories",
        json={
            "name": "Road Maintenance",
            "description": "Road repair and maintenance services",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Road Maintenance"
    assert response.json()["is_active"] is True


def test_citizen_cannot_create_category(client: TestClient):
    set_user_role("CITIZEN")

    response = client.post(
        "/api/v1/categories",
        json={"name": "Water Supply"},
    )

    assert response.status_code == 403


def test_duplicate_category_returns_409(client: TestClient):
    set_user_role("ADMIN")
    payload = {"name": "Electricity"}

    first = client.post("/api/v1/categories", json=payload)
    second = client.post("/api/v1/categories", json=payload)

    assert first.status_code == 201, first.text
    assert second.status_code == 409


def test_admin_can_update_category(client: TestClient):
    set_user_role("ADMIN")

    created = client.post(
        "/api/v1/categories",
        json={"name": "Water Supply"},
    )
    assert created.status_code == 201, created.text

    category_id = created.json()["id"]
    response = client.patch(
        f"/api/v1/categories/{category_id}",
        json={"name": "Water Services"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Water Services"


def test_update_missing_category_returns_404(client: TestClient):
    set_user_role("ADMIN")

    response = client.patch(
        "/api/v1/categories/999",
        json={"name": "Water Services"},
    )

    assert response.status_code == 404


def test_admin_can_soft_delete_category(client: TestClient):
    set_user_role("ADMIN")

    created = client.post(
        "/api/v1/categories",
        json={"name": "Street Lighting"},
    )
    assert created.status_code == 201, created.text

    category_id = created.json()["id"]
    deleted = client.delete(f"/api/v1/categories/{category_id}")

    assert deleted.status_code == 204

    set_user_role("CITIZEN")
    listed = client.get("/api/v1/categories")

    assert listed.status_code == 200, listed.text
    assert all(category["id"] != category_id for category in listed.json())


def test_delete_missing_category_returns_404(client: TestClient):
    set_user_role("ADMIN")

    response = client.delete("/api/v1/categories/999")

    assert response.status_code == 404
