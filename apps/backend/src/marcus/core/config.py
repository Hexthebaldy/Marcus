from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARCUS_", env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "mysql+asyncmy://marcus:marcus@localhost:3306/marcus?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-change-before-deployment-123456789"
    encryption_key: str = ""
    web_origins: str = "http://localhost:5173,http://localhost:8081"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    mail_from: str = "Marcus <login@marcus.local>"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "marcus"
    s3_region: str = "us-east-1"
    auto_approve_notes: bool = False
    worker_poll_seconds: float = 1.0
    lease_seconds: int = 120
    rate_limit_enabled: bool = True

    @property
    def origins(self):
        return [x.strip() for x in self.web_origins.split(",") if x.strip()]

    @model_validator(mode="after")
    def production_secrets(self):
        if self.environment == "production":
            if (
                self.secret_key.startswith(("development", "replace-"))
                or len(self.secret_key) < 32
                or not self.encryption_key
            ):
                raise ValueError("Production requires independent strong signing and encryption keys")
            if any(not x.startswith("https://") for x in self.origins):
                raise ValueError("Production web origins must use HTTPS")
        return self


settings = Settings()
