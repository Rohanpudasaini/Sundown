from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    app_name: str = "LM-CRM Documentation Service"
    version: str = "1.0.0"
    debug: bool

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


class SettingConfig(BaseConfig):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "legalconnect"

    # Secrets
    SECRET_KEY: str  # For JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    log_exceptions: bool = True
    log_exclude_exception_codes: list[str] = []
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT: str

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


settings = SettingConfig()  # type: ignore
