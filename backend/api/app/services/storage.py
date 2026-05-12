import io
import mimetypes
from datetime import timedelta
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from app.config import settings


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def upload_file(file_bytes: bytes, filename: str, contract_id: UUID) -> str:
    client = _client()
    key = f"{contract_id}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    client.put_object(
        settings.bucket_contracts,
        key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    return key


def get_presigned_url(bucket: str, key: str, expires_seconds: int = 3600) -> str:
    client = _client()
    return client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_seconds))


def delete_file(bucket: str, key: str) -> None:
    client = _client()
    try:
        client.remove_object(bucket, key)
    except S3Error:
        pass
