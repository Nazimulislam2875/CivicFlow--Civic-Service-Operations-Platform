
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.service_category import ServiceCategory
from app.models.service_request import ServiceRequest
from app.models.service_request_status_history import ServiceRequestStatusHistory
from app.models.user import User
from app.schemas.service_request import (
    RequestStatusUpdate,
    ServiceRequestCreate,
    ServiceRequestUpdate,
)


class RequestNotFoundError(Exception):
    pass


class CategoryUnavailableError(Exception):
    pass


class RequestPermissionError(Exception):
    pass


class StaffUnavailableError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


STAFF_ROLES = {"STAFF", "SUPERVISOR", "ADMIN"}
ASSIGNMENT_ROLES = {"ADMIN", "SUPERVISOR"}
EDIT_ROLES = {"CITIZEN", "ADMIN"}
TERMINAL_STATUSES = {"RESOLVED", "REJECTED"}

ALLOWED_TRANSITIONS = {
    "SUBMITTED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"RESOLVED", "REJECTED"},
    "RESOLVED": set(),
    "REJECTED": set(),
}


def _request_scope(statement, user: User):
    if user.role == "CITIZEN":
        return statement.where(ServiceRequest.citizen_id == user.id)

    if user.role == "STAFF":
        return statement.where(ServiceRequest.assigned_staff_id == user.id)

    return statement


def _get_visible_request(
    db: Session,
    request_id: int,
    user: User,
) -> ServiceRequest:
    statement = select(ServiceRequest).where(
        ServiceRequest.id == request_id
    )
    request = db.scalar(_request_scope(statement, user))

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
        raise CategoryUnavailableError(
            "Service category is unavailable"
        )

    request = ServiceRequest(
        title=data.title.strip(),
        description=data.description.strip(),
        category_id=data.category_id,
        priority=data.priority,
        location=data.location.strip() if data.location else None,
        citizen_id=user.id,
    )

    try:
        db.add(request)
        db.flush()

        db.add(
            ServiceRequestStatusHistory(
                request_id=request.id,
                changed_by_id=user.id,
                old_status=None,
                new_status="SUBMITTED",
                note="Request submitted",
            )
        )

        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def list_requests(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    status_filter: str | None = None,
    priority_filter: str | None = None,
    category_id: int | None = None,
) -> tuple[list[ServiceRequest], int]:
    statement = _request_scope(select(ServiceRequest), user)

    count_statement = _request_scope(
        select(func.count()).select_from(ServiceRequest),
        user,
    )

    if status_filter:
        statement = statement.where(
            ServiceRequest.status == status_filter
        )
        count_statement = count_statement.where(
            ServiceRequest.status == status_filter
        )

    if priority_filter:
        statement = statement.where(
            ServiceRequest.priority == priority_filter
        )
        count_statement = count_statement.where(
            ServiceRequest.priority == priority_filter
        )

    if category_id is not None:
        statement = statement.where(
            ServiceRequest.category_id == category_id
        )
        count_statement = count_statement.where(
            ServiceRequest.category_id == category_id
        )

    total = db.scalar(count_statement) or 0

    statement = (
        statement.order_by(
            ServiceRequest.created_at.desc(),
            ServiceRequest.id.desc(),
        )
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
    if user.role not in EDIT_ROLES:
        raise RequestPermissionError(
            "You cannot update this request"
        )

    request = _get_visible_request(db, request_id, user)

    if (
        user.role == "CITIZEN"
        and request.status != "SUBMITTED"
    ):
        raise RequestPermissionError(
            "Only submitted requests can be edited by the citizen"
        )

    updates = data.model_dump(exclude_unset=True)

    if (
        "category_id" in updates
        and updates["category_id"] is not None
    ):
        category = db.get(
            ServiceCategory,
            updates["category_id"],
        )

        if category is None or not category.is_active:
            raise CategoryUnavailableError(
                "Service category is unavailable"
            )

    for field, value in updates.items():
        if isinstance(value, str) and field in {
            "title",
            "description",
            "location",
        }:
            value = value.strip()

        setattr(request, field, value)

    try:
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def assign_staff(
    db: Session,
    request_id: int,
    user: User,
    staff_id: int,
) -> ServiceRequest:
    if user.role not in ASSIGNMENT_ROLES:
        raise RequestPermissionError(
            "Only admins and supervisors can assign staff"
        )

    request = db.get(ServiceRequest, request_id)

    if request is None:
        raise RequestNotFoundError(
            "Service request not found"
        )

    if request.status in TERMINAL_STATUSES:
        raise InvalidStatusTransitionError(
            "Cannot assign staff to a closed request"
        )

    staff = db.get(User, staff_id)

    if (
        staff is None
        or staff.role != "STAFF"
        or not getattr(staff, "is_active", True)
    ):
        raise StaffUnavailableError(
            "Staff member is unavailable"
        )

    request.assigned_staff_id = staff.id

    try:
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def change_request_status(
    db: Session,
    request_id: int,
    user: User,
    data: RequestStatusUpdate,
) -> ServiceRequest:
    if user.role not in STAFF_ROLES:
        raise RequestPermissionError(
            "You do not have permission to change request status"
        )

    request = _get_visible_request(
        db,
        request_id,
        user,
    )

    old_status = request.status
    new_status = data.status

    allowed_statuses = ALLOWED_TRANSITIONS.get(
        old_status,
        set(),
    )

    if new_status not in allowed_statuses:
        raise InvalidStatusTransitionError(
            f"Cannot change status from {old_status} "
            f"to {new_status}"
        )

    try:
        request.status = new_status

        db.add(
            ServiceRequestStatusHistory(
                request_id=request.id,
                changed_by_id=user.id,
                old_status=old_status,
                new_status=new_status,
                note=data.note,
            )
        )

        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def get_request_status_history(
    db: Session,
    request_id: int,
    user: User,
) -> list[ServiceRequestStatusHistory]:
    _get_visible_request(db, request_id, user)

    statement = (
        select(ServiceRequestStatusHistory)
        .where(
            ServiceRequestStatusHistory.request_id == request_id
        )
        .order_by(
            ServiceRequestStatusHistory.created_at,
            ServiceRequestStatusHistory.id,
        )
    )

    return list(db.scalars(statement).all())
