import uuid
from pathlib import PurePath

from fastapi import UploadFile

from app.core.config import settings


class InvalidAttachmentError(ValueError):
    pass


# Extension -> (MIME type, signature validator)
def _is_jpeg(data: bytes) -> bool:
    return data.startswith(b"\xff\xd8\xff")


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _is_webp(data: bytes) -> bool:
    return (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    )


def _is_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-")


ALLOWED_TYPES = {
    ".jpg": ("image/jpeg", _is_jpeg),
    ".jpeg": ("image/jpeg", _is_jpeg),
    ".png": ("image/png", _is_png),
    ".webp": ("image/webp", _is_webp),
    ".pdf": ("application/pdf", _is_pdf),
}


async def validate_attachment(
    upload: UploadFile,
) -> tuple[str, str]:
    filename = upload.filename or ""
    safe_name = PurePath(filename.replace("\\", "/")).name

    if not safe_name or safe_name in {".", ".."}:
        raise InvalidAttachmentError("A valid filename is required.")

    extension = PurePath(safe_name).suffix.lower()
    allowed = ALLOWED_TYPES.get(extension)

    if allowed is None:
        raise InvalidAttachmentError("Unsupported file extension.")

    expected_type, signature_check = allowed

    if upload.content_type != expected_type:
        raise InvalidAttachmentError(
            "File extension and content type do not match."
        )

    max_size = settings.MAX_ATTACHMENT_SIZE_BYTES
    total_size = 0
    header = b""

    await upload.seek(0)

    while True:
        chunk = await upload.read(64 * 1024)

        if not chunk:
            break

        total_size += len(chunk)

        if total_size > max_size:
            await upload.seek(0)
            raise InvalidAttachmentError("File exceeds the size limit.")

        if len(header) < 16:
            header += chunk[: 16 - len(header)]

    await upload.seek(0)

    if total_size == 0:
        raise InvalidAttachmentError("Empty files are not allowed.")

    if not signature_check(header):
        raise InvalidAttachmentError(
            "The file content does not match its declared type."
        )

    object_key = f"{uuid.uuid4().hex}{extension}"
    return object_key, expected_type