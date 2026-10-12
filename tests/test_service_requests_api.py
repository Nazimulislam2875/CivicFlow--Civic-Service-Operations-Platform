
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
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

    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def set_user_role(role: str, user_id: int = 1):
    fastapi_app.dependency_overrides[get_current_user] = lambda: User(
        id=user_id,
        full_name=f"Test {role}",
        email=f"{role.lower()}{user_id}@example.com",
        password_hash="not-a-real-password-hash",
        role=role,
        is_active=True,
    )


def create_category(client: TestClient) -> int:
    set_user_role("ADMIN")
    response = client.post(
        "/api/v1/categories",
        json={"name": "Road Maintenance"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_request(client: TestClient, category_id: int) -> dict:
    set_user_role("CITIZEN")
    response = client.post(
        "/api/v1/service-requests",
        json={
            "title": "Repair damaged road",
            "description": "There is a large pothole on the main road.",
            "category_id": category_id,
            "priority": "HIGH",
            "location": "Main Road",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_service_request_list_requires_authentication(client: TestClient):
    response = client.get("/api/v1/service-requests")
    assert response.status_code == 401


def test_citizen_can_create_service_request(client: TestClient):
    category_id = create_category(client)
    request = create_request(client, category_id)

    assert request["title"] == "Repair damaged road"
    assert request["status"] == "SUBMITTED"
    assert request["priority"] == "HIGH"
    assert request["citizen_id"] == 1


def test_inactive_or_missing_category_is_rejected(client: TestClient):
    set_user_role("CITIZEN")

    response = client.post(
        "/api/v1/service-requests",
        json={
            "title": "Repair damaged road",
            "description": "There is a large pothole on the main road.",
            "category_id": 999,
        },
    )

    assert response.status_code == 422


def test_citizen_can_list_own_requests(client: TestClient):
    category_id = create_category(client)
    create_request(client, category_id)

    set_user_role("CITIZEN")
    response = client.get("/api/v1/service-requests")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["citizen_id"] == 1


def test_citizen_cannot_view_another_citizens_request(client: TestClient):
    category_id = create_category(client)
    request = create_request(client, category_id)

    set_user_role("CITIZEN", user_id=2)
    response = client.get(
        f"/api/v1/service-requests/{request['id']}"
    )

    assert response.status_code == 404


def test_citizen_can_filter_requests_by_status(client: TestClient):
    category_id = create_category(client)
    create_request(client, category_id)

    set_user_role("CITIZEN")
    response = client.get(
        "/api/v1/service-requests",
        params={"status": "RESOLVED"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_citizen_can_update_own_submitted_request(client: TestClient):
    category_id = create_category(client)
    request = create_request(client, category_id)

    set_user_role("CITIZEN")
    response = client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Repair the main road"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Repair the main road"


def test_citizen_cannot_update_another_citizens_request(client: TestClient):
    category_id = create_category(client)
    request = create_request(client, category_id)

    set_user_role("CITIZEN", user_id=2)
    response = client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Unauthorized update"},
    )

    assert response.status_code == 404


def test_staff_cannot_update_request_yet(client: TestClient):
    category_id = create_category(client)
    request = create_request(client, category_id)

    set_user_role("STAFF", user_id=3)
    response = client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Staff update"},
    )

    assert response.status_code == 403
