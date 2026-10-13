import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
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
    recipient_email: str,
) -> dict[str, int | str]:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning(
            "Email not sent: SMTP is not configured for request_id=%s",
            request_id,
        )
        return {"status": "skipped", "request_id": request_id}

    message = EmailMessage()
    message["Subject"] = f"Service request received: #{request_id}"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient_email
    message.set_content(
        f"Your service request has been created successfully.\n\n"
        f"Request ID: {request_id}\n"
        f"Title: {title}\n\n"
        "We will keep you updated on its progress."
    )

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=15,
    ) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)

    logger.info(
        "Email sent: request_id=%s citizen_id=%s",
        request_id,
        citizen_id,
    )
    return {"status": "sent", "request_id": request_id}
