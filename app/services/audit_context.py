from fastapi import Request
from sqlalchemy.orm import Session

from app.services.audit_logs import record_audit_event


def record_request_audit(
    db: Session,
    request: Request,
    *,
    actor_id: int,
    action: str,
    resource_type: str,
    resource_id: int,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    forwarded_for = request.headers.get("x-forwarded-for")
    client_host = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.client.host
        if request.client
        else None
    )

    record_audit_event(
        db,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=client_host,
        user_agent=request.headers.get("user-agent"),
    )
