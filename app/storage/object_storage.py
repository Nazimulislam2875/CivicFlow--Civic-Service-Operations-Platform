
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


class ObjectStorageError(Exception):
    """Raised when an object-storage operation fails."""


@lru_cache(maxsize=1)
def _get_s3_client() -> BaseClient:
    try:
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
    except (BotoCoreError, ValueError) as exc:
        raise ObjectStorageError(
            "Could not initialize object storage client"
        ) from exc


def ensure_bucket_exists() -> None:
    client = _get_s3_client()
    bucket = settings.S3_BUCKET_NAME

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        error = exc.response.get("Error", {})
        code = str(error.get("Code", ""))
        status_code = exc.response.get(
            "ResponseMetadata", {}
        ).get("HTTPStatusCode")

        if code not in {"404", "NoSuchBucket", "NotFound"} and (
            status_code != 404
        ):
            raise ObjectStorageError(
                "Could not verify object-storage bucket"
            ) from exc

        try:
            client.create_bucket(Bucket=bucket)
        except (BotoCoreError, ClientError) as create_exc:
            raise ObjectStorageError(
                "Could not create object-storage bucket"
            ) from create_exc
    except BotoCoreError as exc:
        raise ObjectStorageError(
            "Could not connect to object storage"
        ) from exc


def upload_object(
    object_key: str,
    file_obj: BinaryIO,
    content_type: str,
) -> None:
    try:
        _get_s3_client().upload_fileobj(
            Fileobj=file_obj,
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )
    except (BotoCoreError, ClientError) as exc:
        raise ObjectStorageError(
            "Could not upload attachment"
        ) from exc


def create_download_url(object_key: str) -> str:
    try:
        return _get_s3_client().generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": object_key,
            },
            ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRES_SECONDS,
        )
    except (BotoCoreError, ClientError, ValueError) as exc:
        raise ObjectStorageError(
            "Could not generate attachment download URL"
        ) from exc


def delete_object(object_key: str) -> None:
    try:
        _get_s3_client().delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
        )
    except (BotoCoreError, ClientError) as exc:
        raise ObjectStorageError(
            "Could not delete attachment"
        ) from exc
