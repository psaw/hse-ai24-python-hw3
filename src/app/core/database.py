from typing import Generator
from redis import Redis
from sqlmodel import SQLModel, create_engine, Session

from app.core.config import settings


# SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Enable connection pool "pre-ping" feature
)

# Redis connection
redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    ssl=settings.REDIS_SSL,
    db=settings.REDIS_DB,
    decode_responses=True,
)


def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()


def init_db() -> None:
    """Initialize database"""
    SQLModel.metadata.create_all(engine)


def get_redis() -> Redis:
    """Get Redis connection"""
    return redis
