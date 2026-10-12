from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "city_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    result_expires=3600,
    timezone="Asia/Dhaka",
    enable_utc=True,
)
