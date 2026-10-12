
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.service_request import (
    RequestPriority,
    RequestStatus,
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
)
from app.services.service_request_service import (
    CategoryUnavailableError,
    RequestNotFoundError,
    RequestPermissionError,
    create_request,
    get_request,
    list_requests,
    update_request,
)

router = APIRouter()


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


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


@router.get("/{request_id}", response_model=ServiceRequestResponse)
def get_request_detail(
    request_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return get_request(db, request_id, current_user)
    except RequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
def patch_request(
    request_id: int,
    data: ServiceRequestUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceRequestResponse:
    try:
        return update_request(db, request_id, current_user, data)
    except RequestNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RequestPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except CategoryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
