from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.service_category import ServiceCategory
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestUpdate,
)


class RequestNotFoundError(Exception):
    pass


class CategoryUnavailableError(Exception):
    pass


class RequestPermissionError(Exception):
    pass


STAFF_ROLES = {"STAFF", "SUPERVISOR", "ADMIN"}


def _request_scope(statement, user: User):
    if user.role == "CITIZEN":
        return statement.where(ServiceRequest.citizen_id == user.id)
    return statement


def _get_visible_request(
    db: Session,
    request_id: int,
    user: User,
) -> ServiceRequest:
    statement = select(ServiceRequest).where(ServiceRequest.id == request_id)
    statement = _request_scope(statement, user)
    request = db.scalar(statement)

    if request is None:
        raise RequestNotFoundError("Service request not found")

    return request


def create_request(
    db: Session,
    user: User,
    data: ServiceRequestCreate,
) -> ServiceRequest:
    category = db.get(ServiceCategory, data.category_id)

    if category is None or not category.is_active:
        raise CategoryUnavailableError("Service category is unavailable")

    request = ServiceRequest(
        title=data.title.strip(),
        description=data.description.strip(),
        category_id=data.category_id,
        priority=data.priority,
        location=data.location.strip() if data.location else None,
        citizen_id=user.id,
    )

    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_requests(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    priority_filter: str | None = None,
    category_id: int | None = None,
) -> tuple[list[ServiceRequest], int]:
    statement = select(ServiceRequest)
    count_statement = select(func.count()).select_from(ServiceRequest)

    statement = _request_scope(statement, user)
    count_statement = _request_scope(count_statement, user)

    if status_filter:
        statement = statement.where(ServiceRequest.status == status_filter)
        count_statement = count_statement.where(ServiceRequest.status == status_filter)

    if priority_filter:
        statement = statement.where(ServiceRequest.priority == priority_filter)
        count_statement = count_statement.where(
            ServiceRequest.priority == priority_filter
        )

    if category_id is not None:
        statement = statement.where(ServiceRequest.category_id == category_id)
        count_statement = count_statement.where(
            ServiceRequest.category_id == category_id
        )

    total = db.scalar(count_statement) or 0
    statement = (
        statement.order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return list(db.scalars(statement).all()), total


def get_request(
    db: Session,
    request_id: int,
    user: User,
) -> ServiceRequest:
    return _get_visible_request(db, request_id, user)


def update_request(
    db: Session,
    request_id: int,
    user: User,
    data: ServiceRequestUpdate,
) -> ServiceRequest:
    request = _get_visible_request(db, request_id, user)

    if user.role not in {"CITIZEN", "ADMIN"}:
        raise RequestPermissionError("You cannot update this request")

    if user.role == "CITIZEN" and request.status != "SUBMITTED":
        raise RequestPermissionError(
            "Only submitted requests can be edited by the citizen"
        )

    updates = data.model_dump(exclude_unset=True)

    if "category_id" in updates and updates["category_id"] is not None:
        category = db.get(ServiceCategory, updates["category_id"])
        if category is None or not category.is_active:
            raise CategoryUnavailableError("Service category is unavailable")

    for field, value in updates.items():
        if isinstance(value, str) and field in {"title", "description", "location"}:
            value = value.strip()
        setattr(request, field, value)

    try:
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise
