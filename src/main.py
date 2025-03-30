import uvicorn
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from src.core.config import DB_INIT
from src.core.logger import logger
from src.core.database import create_db_and_tables
from src.core.middleware import LoggingMiddleware, setup_cors_middleware
from src.core.scheduler import Scheduler
from src.utils.cache import cache_manager
from src.auth.router import router as auth_router
from src.api.v1.router import router as api_v1_router
from src.api.v1.routers.redirect import router as redirect_router
from src.utils.demo_data import create_demo_data
import os


# Создаем экземпляр планировщика
scheduler = Scheduler()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup
    await cache_manager.init()

    # Запускаем планировщик
    scheduler.start()

    if DB_INIT:
        logger.info("Initializing database...")
        try:
            # Очищаем кеш Redis перед пересозданием БД
            logger.debug("Clearing Redis cache...")
            # await cache_manager.clear()
            await cache_manager.redis.flushdb()
            logger.debug("Redis cache cleared successfully")

            # Пересоздаем таблицы
            await create_db_and_tables(drop_first=True)
            # Создаем демонстрационные данные
            logger.info("Creating demo data...")
            await create_demo_data()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    yield

    # Shutdown
    logger.info("Flushing Redis cache before shutdown...")
    try:
        await (
            cache_manager.redis.flushdb()
        )  # Используем flushdb для полной очистки Redis
        logger.info("Redis cache flushed successfully.")
    except Exception as e:
        logger.error(f"Error flushing Redis cache: {e}")
    scheduler.shutdown()
    await cache_manager.close()


app = FastAPI(lifespan=lifespan)

# Настраиваем CORS
setup_cors_middleware(app)

# Добавляем middleware для логирования
app.add_middleware(LoggingMiddleware)

# Добавляем роутеры
app.include_router(redirect_router)  # Роутер для перенаправлений должен быть первым
app.include_router(auth_router)
app.include_router(api_v1_router)

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        reload=True,
        host="0.0.0.0",
        log_level="debug",
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30,
    )
