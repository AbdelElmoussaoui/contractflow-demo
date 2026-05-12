from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Webhook called when all signers have signed
    agent_callback_url: str = "http://localhost:8001/webhooks/signature"
    log_level: str = "INFO"

    # Seconds before the first signer auto-signs (demo convenience)
    auto_sign_initial_delay: int = 5
    # Seconds between consecutive signers
    auto_sign_interval: int = 3

    # Public base URL used to build signing links
    public_base_url: str = "http://localhost:8002"


settings = Settings()
