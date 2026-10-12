from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    original = exc.orig
    diagnostic = getattr(original, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return constraint_name in {
        "ix_users_email",
        "users_email_key",
    }


def register_user(db: Session, user_data: UserCreate) -> User:
    email = str(user_data.email).strip().lower()

    existing_user = db.scalar(select(User).where(User.email == email))

    if existing_user:
        raise EmailAlreadyRegisteredError("Email is already registered")

    user = User(
        full_name=user_data.full_name.strip(),
        email=email,
        password_hash=hash_password(user_data.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()

        if _is_email_unique_violation(exc):
            raise EmailAlreadyRegisteredError("Email is already registered") from exc

        raise
    except Exception:
        db.rollback()
        raise

    return user
