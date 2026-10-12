import pytest
from fastapi import HTTPException

from app.core.permissions import require_roles
from app.models.user import User


@pytest.fixture
def citizen() -> User:
    return User(
        id=1,
        full_name="Test Citizen",
        email="citizen@example.com",
        password_hash="hashed-password",
        role="CITIZEN",
        is_active=True,
    )


def test_allowed_role_is_accepted(citizen: User):
    checker = require_roles("CITIZEN")
    assert checker(current_user=citizen) is citizen


def test_disallowed_role_is_rejected(citizen: User):
    checker = require_roles("ADMIN")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=citizen)

    assert exc_info.value.status_code == 403


def test_multiple_roles_are_supported(citizen: User):
    checker = require_roles("STAFF", "CITIZEN")
    assert checker(current_user=citizen) is citizen


def test_invalid_role_configuration_is_rejected():
    with pytest.raises(ValueError):
        require_roles("SUPER_ADMIN")


def test_empty_role_configuration_is_rejected():
    with pytest.raises(ValueError):
        require_roles()
