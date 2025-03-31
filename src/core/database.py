from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings
from src.core.logger import logger


# базовый класс для всех моделей
class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_dsn_async, echo=settings.DB_ECHO)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def drop_all_tables():
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")


async def create_db_and_tables(drop_first=False):
    # Импорт здесь для избежания циклических зависимостей
    # Также исправляем импорты моделей, чтобы они работали при вызове из main.py
    # Но лучше вынести эти импорты на уровень модуля, если они нужны всегда
    from src.models.user import User
    from src.models.project import Project
    from src.models.link import Link

    async with engine.begin() as conn:
        try:
            if drop_first:
                logger.debug("Dropping tables...")
                await conn.run_sync(Base.metadata.drop_all)

            logger.debug("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
