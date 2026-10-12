from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.permissions import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category_service import (
    CategoryAlreadyExistsError,
    CategoryNotFoundError,
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter()


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryResponse]:
    return list_categories(db)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_category(
    data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ADMIN"))],
) -> CategoryResponse:
    try:
        return create_category(db, data)
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch("/{category_id}", response_model=CategoryResponse)
def patch_category(
    category_id: int,
    data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ADMIN"))],
) -> CategoryResponse:
    try:
        return update_category(db, category_id, data)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ADMIN"))],
) -> None:
    try:
        delete_category(db, category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
