from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # PostgreSQL settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "url_shortener"
    POSTGRES_SSL_MODE: str = "prefer"

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_SSL: bool = False
    REDIS_DB: int = 0

    # JWT settings
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application settings
    PUBLIC_PROJECT_LINK_EXPIRY_DAYS: int = 5

    # Testing mode
    TESTING: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """Get database URL based on environment"""
        if self.TESTING:
            return "sqlite:///./app.db"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode={self.POSTGRES_SSL_MODE}"

    class Config:
        env_file = ".env"


# Create global settings instance
settings = Settings()
