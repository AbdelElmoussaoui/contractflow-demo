import io
from datetime import timedelta

from minio import Minio

from app.config import settings


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def download_file(bucket: str, key: str) -> bytes:
    client = _client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    client = _client()
    client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)


def get_presigned_url(bucket: str, key: str, expires_seconds: int = 86400) -> str:
    client = _client()
    return client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_seconds))
