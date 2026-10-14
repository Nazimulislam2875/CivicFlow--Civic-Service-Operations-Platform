import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.v1.attachments as attachment_api
import app.models  # noqa: F401
from app.api.deps import get_current_user
from app.db.database import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.models.service_request import ServiceRequest
from app.models.user import User


@pytest.fixture
def attachment_client(monkeypatch):
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
    stored_objects: dict[str, tuple[bytes, str]] = {}

    def fake_ensure_bucket_exists():
        return None

    def fake_upload_object(*, object_key, file_obj, content_type):
        try:
            stored_objects[object_key] = (file_obj.read(), content_type)
        finally:
            # Simulate a storage adapter that closes the supplied file handle.
            file_obj.close()

    def fake_create_download_url(*, object_key):
        assert object_key in stored_objects
        return f"https://storage.example.test/{object_key}?signature=test"

    def fake_delete_object(*, object_key):
        assert object_key in stored_objects
        del stored_objects[object_key]

    monkeypatch.setattr(
        attachment_api, "ensure_bucket_exists", fake_ensure_bucket_exists
    )
    monkeypatch.setattr(
        attachment_api, "upload_object", fake_upload_object
    )
    monkeypatch.setattr(
        attachment_api, "create_download_url", fake_create_download_url
    )
    monkeypatch.setattr(
        attachment_api, "delete_object", fake_delete_object
    )

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client, testing_session, stored_objects
    finally:
        fastapi_app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def set_role(role: str, user_id: int = 1):
    fastapi_app.dependency_overrides[get_current_user] = lambda: User(
        id=user_id,
        full_name=f"Test {role}",
        email=f"{role.lower()}{user_id}@example.com",
        password_hash="not-a-real-password-hash",
        role=role,
        is_active=True,
    )


def create_service_request(client: TestClient) -> dict:
    set_role("ADMIN")
    category_response = client.post(
        "/api/v1/categories",
        json={"name": "Attachment Test Category"},
    )
    assert category_response.status_code == 201, category_response.text
    category_id = category_response.json()["id"]

    set_role("CITIZEN")
    response = client.post(
        "/api/v1/service-requests",
        json={
            "title": "Attachment integration test",
            "description": "Test request for attachment API validation.",
            "category_id": category_id,
            "priority": "HIGH",
            "location": "Integration test location",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_attachment_upload_list_download_and_admin_delete(attachment_client):
    client, _, stored_objects = attachment_client
    request = create_service_request(client)
    request_id = request["id"]
    pdf = b"%PDF-1.7\nAttachment API integration test\n"

    upload_response = client.post(
        f"/api/v1/service-requests/{request_id}/attachments",
        files={"upload": ("../../evidence.pdf", pdf, "application/pdf")},
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment = upload_response.json()
    assert attachment["original_filename"] == "evidence.pdf"
    assert attachment["size_bytes"] == len(pdf)
    assert len(stored_objects) == 1

    list_response = client.get(
        f"/api/v1/service-requests/{request_id}/attachments"
    )
    assert list_response.status_code == 200, list_response.text
    assert [item["id"] for item in list_response.json()] == [attachment["id"]]

    download_response = client.get(
        f"/api/v1/service-requests/{request_id}/attachments/"
        f"{attachment['id']}/download"
    )
    assert download_response.status_code == 200, download_response.text
    assert download_response.json()["download_url"].startswith(
        "https://storage.example.test/"
    )

    citizen_delete = client.delete(
        f"/api/v1/service-requests/{request_id}/attachments/{attachment['id']}"
    )
    assert citizen_delete.status_code == 403

    set_role("ADMIN")
    admin_delete = client.delete(
        f"/api/v1/service-requests/{request_id}/attachments/{attachment['id']}"
    )
    assert admin_delete.status_code == 204, admin_delete.text
    assert stored_objects == {}

    list_after_delete = client.get(
        f"/api/v1/service-requests/{request_id}/attachments"
    )
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_assigned_staff_can_access_request_attachments(attachment_client):
    client, testing_session, _ = attachment_client
    request = create_service_request(client)
    request_id = request["id"]

    with testing_session() as db:
        db.add(
            User(
                id=3,
                full_name="Assigned Test Staff",
                email="assigned-staff@example.com",
                password_hash="not-a-real-password-hash",
                role="STAFF",
                is_active=True,
            )
        )
        service_request = db.get(ServiceRequest, request_id)
        service_request.assigned_staff_id = 3
        db.commit()

    set_role("STAFF", user_id=3)
    pdf = b"%PDF-1.7\nStaff attachment test\n"
    upload_response = client.post(
        f"/api/v1/service-requests/{request_id}/attachments",
        files={"upload": ("staff-evidence.pdf", pdf, "application/pdf")},
    )
    assert upload_response.status_code == 201, upload_response.text

    set_role("STAFF", user_id=4)
    denied_response = client.get(
        f"/api/v1/service-requests/{request_id}/attachments"
    )
    assert denied_response.status_code == 403, denied_response.text


def test_attachment_rejects_unsupported_extension(attachment_client):
    client, _, stored_objects = attachment_client
    request = create_service_request(client)

    response = client.post(
        f"/api/v1/service-requests/{request['id']}/attachments",
        files={"upload": ("notes.txt", b"not an allowed attachment", "text/plain")},
    )
    assert response.status_code == 422, response.text
    assert stored_objects == {}
