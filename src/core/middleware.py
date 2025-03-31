import time
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.logger import logger, request_id_var
from src.core.config import settings
import uuid


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Генерируем уникальный Request ID
        req_id = str(uuid.uuid4())
        # Устанавливаем его в ContextVar
        token = request_id_var.set(req_id)

        start_time = time.time()

        # Логируем входящий запрос (теперь с RID)
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)

            # Логируем ответ (теперь с RID)
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} "
                f"for {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )

            return response

        except Exception as e:
            # Логируем ошибки (теперь с RID)
            process_time = time.time() - start_time
            logger.exception(
                f"Error processing {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )
            raise
        finally:
            # Важно: сбрасываем ContextVar после обработки запроса
            request_id_var.reset(token)


def setup_cors_middleware(app):
    """Настройка CORS middleware.

    Args:
        app: FastAPI приложение
    """

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    logger.info("CORS middleware configured")
