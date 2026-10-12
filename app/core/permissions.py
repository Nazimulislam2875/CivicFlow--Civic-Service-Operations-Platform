from collections.abc import Callable

from fastapi import HTTPException, status

from app.api.deps import CurrentUser
from app.models.user import User

VALID_ROLES = {
    "CITIZEN",
    "STAFF",
    "SUPERVISOR",
    "ADMIN",
}


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    if not allowed_roles or not set(allowed_roles) <= VALID_ROLES:
        raise ValueError("Invalid or missing roles")

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )

        return current_user

    return role_checker
