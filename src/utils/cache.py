from typing import Optional, Any
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from src.core.config import settings
from src.core.logger import logger
import json
from pydantic import HttpUrl
from datetime import datetime, timezone


class PydanticJSONEncoder(json.JSONEncoder):
    """JSON кодировщик для Pydantic моделей и специальных типов."""

    def default(self, obj):
        if isinstance(obj, HttpUrl):
            return str(obj)
        if isinstance(obj, datetime):
            # Добавляем явный часовой пояс UTC, если он отсутствует
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return super().default(obj)


class CacheManager:
    """Менеджер кэширования для работы с Redis."""

    def __init__(self):
        self.redis: Optional[Redis] = None
        self.backend: Optional[RedisBackend] = None

    async def init(self):
        """Инициализация подключения к Redis."""
        try:
            # Get password string if it exists
            redis_password = (
                settings.REDIS_PASSWORD.get_secret_value()
                if settings.REDIS_PASSWORD
                else None
            )

            self.redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=redis_password,
                db=settings.REDIS_DB,
                decode_responses=True,
                ssl=settings.REDIS_SSL,
            )
            self.backend = RedisBackend(self.redis)
            FastAPICache.init(self.backend, prefix="fastapi-cache")
            logger.info("Cache manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Значение из кэша или None, если не найдено
        """
        try:
            value = await self.backend.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache value for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Установка значения в кэш.

        Args:
            key: Ключ кэша
            value: Значение для кэширования
            expire: Время жизни кэша в секундах

        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            # Сериализуем значение в JSON с использованием специального кодировщика
            serialized_value = json.dumps(value, cls=PydanticJSONEncoder)
            await self.backend.set(key, serialized_value, expire)
            return True
        except Exception as e:
            logger.error(f"Error setting cache value for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Удаление значения из кэша.

        Args:
            key: Ключ кэша

        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            # Если ключ содержит wildcard (*), используем scan для поиска всех подходящих ключей
            if "*" in key:
                pattern = key.replace("*", "*")
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break
            else:
                await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cache value for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Очистка всего кэша.

        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            await self.backend.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def close(self):
        """Закрытие соединения с Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Cache connection closed")


# Создаем глобальный экземпляр менеджера кэша
cache_manager = CacheManager()
