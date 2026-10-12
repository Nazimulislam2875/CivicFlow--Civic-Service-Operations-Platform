
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
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
    fastapi_app.state.testing_session = testing_session

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
        del fastapi_app.state.testing_session
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def deactivate_user(email: str) -> None:
    testing_session = fastapi_app.state.testing_session

    with testing_session() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None, f"User not found: {email}"

        user.is_active = False
        db.commit()


def register_user(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Citizen",
            "email": "citizen@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def login_user(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "citizen@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200, response.text
    return response.json()


def test_register_and_login(client: TestClient):
    registered = register_user(client)

    assert registered["email"] == "citizen@example.com"
    assert "password_hash" not in registered

    tokens = login_user(client)

    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["access_token"] != tokens["refresh_token"]


def test_duplicate_registration_returns_409(client: TestClient):
    register_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Another Citizen",
            "email": "citizen@example.com",
            "password": "AnotherPassword123",
        },
    )

    assert response.status_code == 409


def test_invalid_password_returns_401(client: TestClient):
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "citizen@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_inactive_user_cannot_login(client: TestClient):
    register_user(client)
    deactivate_user("citizen@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "citizen@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 403, response.text


def test_refresh_rotates_token_and_rejects_old_token(
    client: TestClient,
):
    register_user(client)
    tokens = login_user(client)
    old_refresh_token = tokens["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == 200, response.text
    new_tokens = response.json()

    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    assert new_tokens["refresh_token"] != old_refresh_token

    old_token_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert old_token_response.status_code == 401


def test_inactive_user_cannot_refresh_token(client: TestClient):
    register_user(client)
    tokens = login_user(client)
    deactivate_user("citizen@example.com")

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401, response.text


def test_invalid_refresh_token_returns_401(client: TestClient):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.value"},
    )

    assert response.status_code == 401


def test_profile_requires_access_token(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_profile_with_valid_access_token(client: TestClient):
    register_user(client)
    tokens = login_user(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["email"] == "citizen@example.com"
    assert data["role"] == "CITIZEN"
    assert "password_hash" not in data


def test_profile_rejects_refresh_token(client: TestClient):
    register_user(client)
    tokens = login_user(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )

    assert response.status_code == 401


def test_admin_endpoint_rejects_citizen(client: TestClient):
    register_user(client)
    tokens = login_user(client)

    response = client.get(
        "/api/v1/auth/admin-check",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 403


def test_admin_endpoint_requires_authentication(client: TestClient):
    response = client.get("/api/v1/auth/admin-check")

    assert response.status_code == 401


def test_registration_cannot_assign_admin_role(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Citizen",
            "email": "role-test@example.com",
            "password": "TestPassword123",
            "role": "ADMIN",
            "is_active": True,
            "department_id": 1,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "CITIZEN"
    assert response.json()["department_id"] is None
