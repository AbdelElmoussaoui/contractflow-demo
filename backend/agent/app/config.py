from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # psycopg3 format — required by LangGraph PostgresSaver
    database_url_sync: str

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin_secret"
    minio_secure: bool = False

    anthropic_api_key: str
    signature_mock_url: str = "http://localhost:8002"
    api_service_url: str = "http://localhost:8000"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3002"

    llm_model_fast: str = "claude-haiku-4-5-20251001"
    llm_model_smart: str = "claude-sonnet-4-6"

    log_level: str = "INFO"

    bucket_contracts: str = "contracts"
    bucket_archives: str = "archives"
    bucket_signed: str = "signed-docs"


settings = Settings()
