
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def record_audit_event(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> AuditLog:
    """Add an audit event to the current database transaction."""
    event = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
    )

    db.add(event)

    if commit:
        try:
            db.commit()
            db.refresh(event)
        except Exception:
            db.rollback()
            logger.exception("Failed to persist audit event")
            raise
    else:
        db.flush()

    return event


def list_audit_events(
    db: Session,
    *,
    actor_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    filters = []

    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)

    if action:
        filters.append(AuditLog.action == action)

    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    if resource_id is not None:
        filters.append(AuditLog.resource_id == resource_id)

    total = db.scalar(
        select(func.count()).select_from(AuditLog).where(*filters)
    ) or 0

    statement = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )

    items = list(db.scalars(statement).all())
    return items, total
