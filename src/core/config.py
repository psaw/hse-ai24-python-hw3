from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from typing import List, Any
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database settings
    DB_USER: str
    DB_PASS: SecretStr
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_INIT: bool = False
    DB_ECHO: bool = False

    # Calculated database DSN (async for application)
    @property
    def database_dsn_async(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.DB_USER,
                password=self.DB_PASS.get_secret_value(),
                host=self.DB_HOST,
                port=self.DB_PORT,
                path=self.DB_NAME,
            )
        )

    # Calculated database DSN (sync for Alembic)
    @property
    def database_dsn_sync(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=self.DB_USER,
                password=self.DB_PASS.get_secret_value(),
                host=self.DB_HOST,
                port=self.DB_PORT,
                path=self.DB_NAME,
            )
        )

    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: SecretStr | None = None
    REDIS_DB: int = 0
    REDIS_SSL: bool = False

    # Calculated Redis DSN
    @property
    def redis_dsn(self) -> str:
        # Note: Pydantic v2 RedisDsn doesn't directly support password in the URL easily yet
        # Building manually is more reliable for now.
        password_part = (
            f":{self.REDIS_PASSWORD.get_secret_value()}" if self.REDIS_PASSWORD else ""
        )
        user_pass_part = f"{password_part}@" if password_part else ""
        scheme = "rediss" if self.REDIS_SSL else "redis"
        # Format: redis[s]://[[username]:[password]]@[hostname]:[port]/[db-number]
        # Username is often not used with Redis password auth
        return f"{scheme}://{user_pass_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Security settings
    SECRET: SecretStr

    # CORS settings
    CORS_ORIGINS: List[str] = []
    CORS_HEADERS: List[str] = ["*"]  # Allow all headers by default
    CORS_METHODS: List[str] = ["*"]  # Allow all methods by default
    CORS_CREDENTIALS: bool = True

    # Scheduler settings
    SCHEDULER_CLEANUP_INTERVAL: int = Field(
        default=1, description="Cleanup interval in minutes"
    )

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # Validator for list fields read from environment variables
    # Handles comma-separated strings and JSON string lists
    @field_validator("CORS_ORIGINS", "CORS_HEADERS", "CORS_METHODS", mode="before")
    @classmethod
    def parse_string_list(cls, value: Any) -> Any:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails for some reason
                    pass
            # Assume comma-separated string, filter empty strings after split
            return [item.strip() for item in value.split(",") if item.strip()]
        # Return as-is if already a list or other type
        return value


# Create a single, reusable settings instance
settings = Settings()

# Example usage block (optional, can be removed)
if __name__ == "__main__":
    print("--- Loaded Configuration ---")
    # Use model_dump() for a cleaner representation, excluding secrets by default
    print(
        settings.model_dump(
            exclude={"DB_PASS", "SMTP_PASSWORD", "REDIS_PASSWORD", "SECRET"}
        )
    )
    print("\n--- Calculated DSNs ---")
    print(f"Async Database DSN: {settings.database_dsn_async}")
    print(f"Sync Database DSN: {settings.database_dsn_sync}")
    print(f"Redis DSN: {settings.redis_dsn}")
    print("\n--- Secret Values (Masked) ---")
    print(f"DB Password: {settings.DB_PASS}")  # Will show as '**********'
    print(f"Redis Password: {settings.REDIS_PASSWORD}")
    print(f"Secret Key: {settings.SECRET}")
