import logging
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.attachment import Attachment
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.schemas.attachment import AttachmentDownload, AttachmentRead
from app.services.audit_logs import record_audit_event
from app.storage.object_storage import (
    ObjectStorageError,
    create_download_url,
    delete_object,
    ensure_bucket_exists,
    upload_object,
)
from app.storage.validation import InvalidAttachmentError, validate_attachment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service-requests", tags=["Attachments"])


def _role_name(user: User) -> str:
    role = user.role
    return str(getattr(role, "value", role)).upper()


def _can_access_request(user: User, service_request: ServiceRequest) -> bool:
    role = _role_name(user)

    if role in ("ADMIN", "SUPERVISOR"):
        return True
    if role == "CITIZEN":
        return service_request.citizen_id == user.id
    if role == "STAFF":
        return service_request.assigned_staff_id == user.id

    return False


def _get_request_or_404(db: Session, request_id: int) -> ServiceRequest:
    service_request = db.get(ServiceRequest, request_id)

    if service_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found",
        )

    return service_request


@router.post(
    "/{request_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    upload: UploadFile = File(...),
) -> Attachment:
    try:
        service_request = _get_request_or_404(db, request_id)

        if not _can_access_request(current_user, service_request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access this service request",
            )

        try:
            object_key, content_type = await validate_attachment(upload)
        except InvalidAttachmentError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        original_filename = PurePosixPath(
            (upload.filename or "").replace("\\", "/")
        ).name[:255]
        object_uploaded = False

        try:
            upload.file.seek(0)
            size_bytes = 0

            while chunk := upload.file.read(1024 * 1024):
                size_bytes += len(chunk)

            upload.file.seek(0)

            ensure_bucket_exists()
            upload_object(
                object_key=object_key,
                file_obj=upload.file,
                content_type=content_type,
            )
            object_uploaded = True

            attachment = Attachment(
                service_request_id=request_id,
                uploaded_by_id=current_user.id,
                original_filename=original_filename,
                object_key=object_key,
                content_type=content_type,
                size_bytes=size_bytes,
            )
            db.add(attachment)
            db.flush()

            record_audit_event(
                db,
                actor_id=current_user.id,
                action="attachment.uploaded",
                resource_type="attachment",
                resource_id=attachment.id,
                new_values={
                    "service_request_id": request_id,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                },
            )

            db.commit()
            db.refresh(attachment)
            return attachment

        except Exception as exc:
            db.rollback()

            if object_uploaded:
                try:
                    delete_object(object_key=object_key)
                except Exception:
                    logger.exception(
                        "Failed to clean up uploaded object after upload failure"
                    )

            if isinstance(exc, HTTPException):
                raise

            logger.exception("Attachment upload failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Attachment upload failed",
            ) from exc

    finally:
        await upload.close()


@router.get(
    "/{request_id}/attachments",
    response_model=list[AttachmentRead],
)
def list_attachments(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Attachment]:
    service_request = _get_request_or_404(db, request_id)

    if not _can_access_request(current_user, service_request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this service request",
        )

    return list(
        db.scalars(
            select(Attachment)
            .where(Attachment.service_request_id == request_id)
            .order_by(Attachment.created_at.desc(), Attachment.id.desc())
        ).all()
    )


@router.get(
    "/{request_id}/attachments/{attachment_id}/download",
    response_model=AttachmentDownload,
)
def get_attachment_download_url(
    request_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentDownload:
    service_request = _get_request_or_404(db, request_id)

    if not _can_access_request(current_user, service_request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this service request",
        )

    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.service_request_id == request_id,
        )
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    try:
        url = create_download_url(object_key=attachment.object_key)
    except ObjectStorageError as exc:
        logger.exception("Could not generate attachment download URL")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from exc

    return AttachmentDownload(attachment=attachment, download_url=url)


@router.delete(
    "/{request_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_attachment(
    request_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _get_request_or_404(db, request_id)

    if _role_name(current_user) != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete attachments",
        )

    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.service_request_id == request_id,
        )
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="attachment.deleted",
        resource_type="attachment",
        resource_id=attachment.id,
        old_values={
            "service_request_id": request_id,
            "content_type": attachment.content_type,
            "size_bytes": attachment.size_bytes,
        },
    )

    try:
        delete_object(object_key=attachment.object_key)
    except ObjectStorageError as exc:
        db.rollback()
        logger.exception("Could not delete attachment from object storage")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Attachment storage is unavailable",
        ) from exc

    try:
        db.delete(attachment)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Could not delete attachment metadata")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attachment deletion failed",
        ) from exc
