from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from core.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, DB_ECHO
from core.logger import logger

# базовый класс для всех моделей
class Base(DeclarativeBase):
    pass


DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=DB_ECHO)
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
    import models.user
    import models.project
    import models.link

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
