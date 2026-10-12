from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.permissions import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.services.department_service import (
    DepartmentAlreadyExistsError,
    create_department,
    list_departments,
)

router = APIRouter()


@router.get("", response_model=list[DepartmentResponse])
def get_departments(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DepartmentResponse]:
    return list_departments(db)


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_department(
    data: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ADMIN"))],
) -> DepartmentResponse:
    try:
        return create_department(db, data)
    except DepartmentAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
