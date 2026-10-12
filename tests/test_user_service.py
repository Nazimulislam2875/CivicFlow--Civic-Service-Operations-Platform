from unittest.mock import Mock

import pytest

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    register_user,
)


def test_register_user_success(monkeypatch):
    db = Mock()
    db.scalar.return_value = None

    monkeypatch.setattr(
        "app.services.user_service.hash_password",
        lambda password: "fake_hashed_password",
    )

    user_data = UserCreate(
        full_name="Test Citizen",
        email="newcitizen@example.com",
        password="TestPassword123",
    )

    result = register_user(db, user_data)

    assert isinstance(result, User)
    assert result.email == "newcitizen@example.com"
    assert result.password_hash == "fake_hashed_password"
    db.add.assert_called_once_with(result)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)


def test_register_user_duplicate_email():
    db = Mock()
    db.scalar.return_value = User(
        full_name="Existing Citizen",
        email="existing@example.com",
        password_hash="existing_hash",
    )

    user_data = UserCreate(
        full_name="New Citizen",
        email="existing@example.com",
        password="TestPassword123",
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        register_user(db, user_data)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_register_user_rolls_back_on_commit_failure(monkeypatch):
    db = Mock()
    db.scalar.return_value = None
    db.commit.side_effect = RuntimeError("Database failure")

    monkeypatch.setattr(
        "app.services.user_service.hash_password",
        lambda password: "fake_hashed_password",
    )

    user_data = UserCreate(
        full_name="Test Citizen",
        email="failure@example.com",
        password="TestPassword123",
    )

    with pytest.raises(RuntimeError, match="Database failure"):
        register_user(db, user_data)

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()
