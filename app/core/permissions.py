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
    normalized_roles = {role.upper() for role in allowed_roles}

    if not normalized_roles or not normalized_roles <= VALID_ROLES:
        raise ValueError("Invalid or missing roles")

    def role_checker(current_user: CurrentUser) -> User:
        user_role = getattr(current_user.role, "value", current_user.role)

        if str(user_role).upper() not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )

        return current_user

    return role_checker
