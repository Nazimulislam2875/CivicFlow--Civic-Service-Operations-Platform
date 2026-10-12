import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="notifications.request_created",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def notify_request_created(
    request_id: int,
    citizen_id: int,
    title: str,
) -> dict[str, int | str]:
    logger.info(
        "Service request created: request_id=%s citizen_id=%s title=%s",
        request_id,
        citizen_id,
        title,
    )

    return {
        "status": "processed",
        "request_id": request_id,
    }
