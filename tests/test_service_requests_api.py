
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
            yield test_client, testing_session
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


def create_staff_record(testing_session, staff_id: int = 3) -> None:
    with testing_session() as db:
        db.add(
            User(
                id=staff_id,
                full_name="Test Staff",
                email=f"staff{staff_id}@example.com",
                password_hash="not-a-real-password-hash",
                role="STAFF",
                is_active=True,
            )
        )
        db.commit()


def assign_staff(
    client: TestClient,
    request_id: int,
    staff_id: int = 3,
):
    set_user_role("ADMIN")
    return client.post(
        f"/api/v1/service-requests/{request_id}/assign",
        json={"staff_id": staff_id},
    )


def test_service_request_list_requires_authentication(client):
    test_client, _ = client
    response = test_client.get("/api/v1/service-requests")
    assert response.status_code == 401


def test_citizen_can_create_service_request(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    assert request["title"] == "Repair damaged road"
    assert request["status"] == "SUBMITTED"
    assert request["priority"] == "HIGH"
    assert request["citizen_id"] == 1


def test_inactive_or_missing_category_is_rejected(client):
    test_client, _ = client
    set_user_role("CITIZEN")

    response = test_client.post(
        "/api/v1/service-requests",
        json={
            "title": "Repair damaged road",
            "description": "There is a large pothole on the main road.",
            "category_id": 999,
        },
    )

    assert response.status_code == 422


def test_citizen_can_list_own_requests(client):
    test_client, _ = client
    category_id = create_category(test_client)
    create_request(test_client, category_id)

    set_user_role("CITIZEN")
    response = test_client.get("/api/v1/service-requests")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["citizen_id"] == 1


def test_citizen_cannot_view_another_citizens_request(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    set_user_role("CITIZEN", user_id=2)
    response = test_client.get(
        f"/api/v1/service-requests/{request['id']}"
    )

    assert response.status_code == 404


def test_citizen_can_filter_requests_by_status(client):
    test_client, _ = client
    category_id = create_category(test_client)
    create_request(test_client, category_id)

    set_user_role("CITIZEN")
    response = test_client.get(
        "/api/v1/service-requests",
        params={"status": "RESOLVED"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_citizen_can_update_own_submitted_request(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    set_user_role("CITIZEN")
    response = test_client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Repair the main road"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Repair the main road"


def test_citizen_cannot_update_another_citizens_request(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    set_user_role("CITIZEN", user_id=2)
    response = test_client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Unauthorized update"},
    )

    assert response.status_code == 404


def test_staff_cannot_update_request_yet(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    set_user_role("STAFF", user_id=3)
    response = test_client.patch(
        f"/api/v1/service-requests/{request['id']}",
        json={"title": "Staff update"},
    )

    assert response.status_code == 403


def test_admin_can_assign_staff(client):
    test_client, testing_session = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)
    create_staff_record(testing_session)

    response = assign_staff(test_client, request["id"])

    assert response.status_code == 200, response.text
    assert response.json()["assigned_staff_id"] == 3


def test_missing_staff_cannot_be_assigned(client):
    test_client, _ = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)

    response = assign_staff(test_client, request["id"], staff_id=999)

    assert response.status_code == 422


def test_assigned_staff_can_change_request_status(client):
    test_client, testing_session = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)
    create_staff_record(testing_session)

    assignment = assign_staff(test_client, request["id"])
    assert assignment.status_code == 200, assignment.text

    set_user_role("STAFF", user_id=3)
    response = test_client.patch(
        f"/api/v1/service-requests/{request['id']}/status",
        json={
            "status": "IN_PROGRESS",
            "note": "Work has started",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "IN_PROGRESS"


def test_invalid_status_transition_is_rejected(client):
    test_client, testing_session = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)
    create_staff_record(testing_session)

    assignment = assign_staff(test_client, request["id"])
    assert assignment.status_code == 200, assignment.text

    set_user_role("STAFF", user_id=3)
    response = test_client.patch(
        f"/api/v1/service-requests/{request['id']}/status",
        json={"status": "RESOLVED"},
    )

    assert response.status_code == 409


def test_request_status_history_is_recorded(client):
    test_client, testing_session = client
    category_id = create_category(test_client)
    request = create_request(test_client, category_id)
    create_staff_record(testing_session)

    assignment = assign_staff(test_client, request["id"])
    assert assignment.status_code == 200, assignment.text

    set_user_role("STAFF", user_id=3)
    update = test_client.patch(
        f"/api/v1/service-requests/{request['id']}/status",
        json={
            "status": "IN_PROGRESS",
            "note": "Work started",
        },
    )
    assert update.status_code == 200, update.text

    history = test_client.get(
        f"/api/v1/service-requests/{request['id']}/history"
    )

    assert history.status_code == 200, history.text
    entries = history.json()
    assert len(entries) == 2
    assert entries[0]["old_status"] is None
    assert entries[0]["new_status"] == "SUBMITTED"
    assert entries[1]["old_status"] == "SUBMITTED"
    assert entries[1]["new_status"] == "IN_PROGRESS"
    assert entries[1]["note"] == "Work started"
