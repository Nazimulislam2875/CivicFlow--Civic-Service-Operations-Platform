from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)
    JWT_ALGORITHM: str = "HS256"
    REDIS_URL: str = "redis://localhost:6379/0"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = Field(default=587, gt=0)
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_BUCKET_NAME: str = "city-service-attachments"
    S3_ACCESS_KEY_ID: str = "cityservice-dev"
    S3_SECRET_ACCESS_KEY: str = "cityservice-dev-secret"
    S3_REGION: str = "us-east-1"
    S3_PRESIGNED_URL_EXPIRES_SECONDS: int = Field(
        default=300,
        gt=0,
    )


    MAX_ATTACHMENT_SIZE_BYTES: int = Field(default=10 * 1024 * 1024, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
