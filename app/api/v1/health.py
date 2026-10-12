from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc



@router.get("/health/redis")
def redis_health_check():
    from redis.exceptions import RedisError

    from app.core.redis_client import check_redis_connection

    try:
        check_redis_connection()
        return {"status": "ok", "redis": "connected"}
    except (RedisError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Redis unavailable",
        ) from exc