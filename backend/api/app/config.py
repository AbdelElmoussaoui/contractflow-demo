from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin_secret"
    minio_secure: bool = False
    agent_service_url: str = "http://localhost:8001"
    log_level: str = "INFO"

    # Buckets MinIO
    bucket_contracts: str = "contracts"
    bucket_archives: str = "archives"
    bucket_signed: str = "signed-docs"

    # Taille max upload (50 Mo)
    max_upload_mb: int = 50


settings = Settings()
