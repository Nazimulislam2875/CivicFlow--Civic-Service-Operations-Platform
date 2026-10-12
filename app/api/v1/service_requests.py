
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.service_request import (
    RequestPriority,
    RequestStatus,
    RequestStatusHistoryResponse,
    RequestStatusUpdate,
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
    StaffAssignment,
)
from app.services.service_request_service import (
    CategoryUnavailableError,
    InvalidStatusTransitionError,
    RequestNotFoundError,
    RequestPermissionError,
    StaffUnavailableError,
    assign_staff,
    change_request_status,
    create_request,
    get_request,
    get_request_status_history,
    list_requests,
    update_request,
)

router = APIRouter()


def raise_service_error(exc: Exception) -> None:
    if isinstance(exc, RequestNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, RequestPermissionError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, CategoryUnavailableError | StaffUnavailableError):
        code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, InvalidStatusTransitionError):
        code = status.HTTP_409_CONFLICT
    else:
        raise exc

    raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post(
    "",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_request(
    data: ServiceRequestCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return create_request(db, current_user, data)
    except CategoryUnavailableError as exc:
        raise_service_error(exc)


@router.get("", response_model=ServiceRequestListResponse)
def get_requests(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    request_status: Annotated[
        RequestStatus | None, Query(alias="status")
    ] = None,
    priority: RequestPriority | None = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
) -> ServiceRequestListResponse:
    items, total = list_requests(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        status_filter=request_status,
        priority_filter=priority,
        category_id=category_id,
    )
    return ServiceRequestListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{request_id}/assign",
    response_model=ServiceRequestResponse,
)
def post_assignment(
    request_id: int,
    data: StaffAssignment,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return assign_staff(db, request_id, current_user, data.staff_id)
    except (
        RequestNotFoundError,
        RequestPermissionError,
        StaffUnavailableError,
        InvalidStatusTransitionError,
    ) as exc:
        raise_service_error(exc)


@router.patch(
    "/{request_id}/status",
    response_model=ServiceRequestResponse,
)
def patch_request_status(
    request_id: int,
    data: RequestStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return change_request_status(db, request_id, current_user, data)
    except (
        RequestNotFoundError,
        RequestPermissionError,
        InvalidStatusTransitionError,
    ) as exc:
        raise_service_error(exc)


@router.get(
    "/{request_id}/history",
    response_model=list[RequestStatusHistoryResponse],
)
def get_request_history(
    request_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[RequestStatusHistoryResponse]:
    try:
        return get_request_status_history(db, request_id, current_user)
    except (RequestNotFoundError, RequestPermissionError) as exc:
        raise_service_error(exc)


@router.get("/{request_id}", response_model=ServiceRequestResponse)
def get_request_detail(
    request_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return get_request(db, request_id, current_user)
    except RequestNotFoundError as exc:
        raise_service_error(exc)


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
def patch_request(
    request_id: int,
    data: ServiceRequestUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return update_request(db, request_id, current_user, data)
    except (
        RequestNotFoundError,
        RequestPermissionError,
        CategoryUnavailableError,
    ) as exc:
        raise_service_error(exc)
