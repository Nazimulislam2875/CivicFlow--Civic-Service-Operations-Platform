from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate


class DepartmentAlreadyExistsError(Exception):
    pass


def create_department(
    db: Session,
    data: DepartmentCreate,
) -> Department:
    name = data.name.strip()

    existing = db.scalar(select(Department).where(Department.name == name))

    if existing:
        raise DepartmentAlreadyExistsError("Department already exists")

    department = Department(
        name=name,
        description=data.description,
    )

    try:
        db.add(department)
        db.commit()
        db.refresh(department)
        return department
    except IntegrityError as exc:
        db.rollback()
        raise DepartmentAlreadyExistsError("Department already exists") from exc
    except Exception:
        db.rollback()
        raise


def list_departments(db: Session) -> list[Department]:
    return list(
        db.scalars(
            select(Department)
            .where(Department.is_active.is_(True))
            .order_by(Department.name)
        ).all()
    )
