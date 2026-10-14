
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Adjust this import only if the existing project uses a different
# module path for its current-user dependency.
from app.api.deps import get_current_user
from app.db.database import get_db
from app.schemas.audit_log import AuditLogList, AuditLogRead
from app.services.audit_logs import list_audit_events

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


def require_admin(current_user) -> None:
    role = getattr(current_user, "role", None)
    role_value = getattr(role, "value", role)

    if str(role_value).upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/", response_model=AuditLogList)
def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
    actor_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, min_length=1, max_length=100),
    resource_type: str | None = Query(
        default=None, min_length=1, max_length=100
    ),
    resource_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AuditLogList:
    require_admin(current_user)

    items, total = list_audit_events(
        db,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )

    return AuditLogList(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
