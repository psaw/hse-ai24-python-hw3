from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from core.database import get_async_session
from auth.users import optional_current_user
from models.user import User
from services.link import LinkService


router = APIRouter()


async def get_link_service(session: AsyncSession = Depends(get_async_session)):
    """Получение сервиса для работы с ссылками."""
    return LinkService(session)


@router.get("/{short_code}", response_class=RedirectResponse, tags=["Links"])
async def redirect_to_original_url(
    short_code: str,
    link_service: LinkService = Depends(get_link_service),
    user: Optional[User] = Depends(optional_current_user),
):
    """Перенаправление на оригинальный URL по короткому коду.

    Увеличивает счетчик переходов и обновляет дату последнего использования.
    Не требует аутентификации.
    """
    try:
        # Получаем ссылку по короткому коду
        logger.info(f"Redirecting to: {short_code}")
        link = await link_service.get_link_by_short_code(short_code, user)
        logger.info(f"Found link: {link.original_url}")

        # Обновляем статистику
        await link_service.update_link_stats(link.id)

        # Перенаправляем на оригинальный URL
        return RedirectResponse(url=link.original_url)
    except HTTPException as e:
        # Перехватываем ошибки из сервиса
        logger.warning(
            f"Error redirecting {short_code}: {e.detail} (status: {e.status_code})"
        )
        # Возвращаем корректный статус код и сообщение об ошибке
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        # Логируем любые другие ошибки
        logger.error(f"Unexpected error redirecting {short_code}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Произошла внутренняя ошибка сервера"},
        )
