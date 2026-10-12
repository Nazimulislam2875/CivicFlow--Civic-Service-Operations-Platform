from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class InactiveUserError(Exception):
    pass


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)

    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=expires_at,
        )
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def login_user(
    db: Session,
    email: str,
    password: str,
) -> TokenResponse:
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None or not verify_password(
        password,
        user.password_hash,
    ):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InactiveUserError("User account is inactive")

    try:
        tokens = _issue_tokens(db, user)
        db.commit()
        return tokens
    except Exception:
        db.rollback()
        raise


def refresh_user_tokens(
    db: Session,
    refresh_token: str,
) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise InvalidRefreshTokenError("Invalid refresh token")

        user_id = int(payload["sub"])
        jti = payload["jti"]

    except (
        jwt.InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise InvalidRefreshTokenError("Invalid or expired refresh token") from exc

    try:
        stored_token = db.scalar(
            select(RefreshToken).where(RefreshToken.jti == jti).with_for_update()
        )

        if stored_token is None:
            raise InvalidRefreshTokenError(
                "Refresh token has been revoked or is invalid"
            )

        now = datetime.now(UTC)
        stored_expiry = stored_token.expires_at

        if stored_expiry.tzinfo is None:
            stored_expiry = stored_expiry.replace(tzinfo=UTC)

        if (
            stored_token.user_id != user_id
            or stored_token.revoked_at is not None
            or stored_expiry <= now
        ):
            raise InvalidRefreshTokenError("Refresh token has been revoked or expired")

        user = db.get(User, user_id)

        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("User account is unavailable")

        stored_token.revoked_at = now
        tokens = _issue_tokens(db, user)
        db.commit()

        return tokens

    except InvalidRefreshTokenError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
