from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.service_category import ServiceCategory
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryAlreadyExistsError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


def create_category(db: Session, data: CategoryCreate) -> ServiceCategory:
    name = data.name.strip()

    existing = db.scalar(select(ServiceCategory).where(ServiceCategory.name == name))
    if existing:
        raise CategoryAlreadyExistsError("Category already exists")

    category = ServiceCategory(
        name=name,
        description=data.description,
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as exc:
        db.rollback()
        raise CategoryAlreadyExistsError("Category already exists") from exc
    except Exception:
        db.rollback()
        raise


def list_categories(db: Session) -> list[ServiceCategory]:
    statement = (
        select(ServiceCategory)
        .where(ServiceCategory.is_active.is_(True))
        .order_by(ServiceCategory.name)
    )
    return list(db.scalars(statement).all())


def update_category(
    db: Session,
    category_id: int,
    data: CategoryUpdate,
) -> ServiceCategory:
    category = db.get(ServiceCategory, category_id)

    if category is None:
        raise CategoryNotFoundError("Category not found")

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] is not None:
        updates["name"] = updates["name"].strip()

        existing = db.scalar(
            select(ServiceCategory).where(
                ServiceCategory.name == updates["name"],
                ServiceCategory.id != category_id,
            )
        )
        if existing:
            raise CategoryAlreadyExistsError("Category already exists")

    for field, value in updates.items():
        setattr(category, field, value)

    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as exc:
        db.rollback()
        raise CategoryAlreadyExistsError("Category already exists") from exc
    except Exception:
        db.rollback()
        raise


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(ServiceCategory, category_id)

    if category is None:
        raise CategoryNotFoundError("Category not found")

    category.is_active = False

    db.commit()
