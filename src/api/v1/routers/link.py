from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.users import current_active_user, optional_current_user
from src.core.database import get_async_session
from src.models.user import User
from src.schemas.link import Link, LinkCreate, LinkUpdate, LinkStats, LinkResponse
from src.services.link import LinkService
from src.core.logger import logger


router = APIRouter(prefix="/links", tags=["Links"])


async def get_link_service(session: AsyncSession = Depends(get_async_session)):
    """Получение сервиса для работы с ссылками."""
    return LinkService(session)


@router.post("/shorten", response_model=Link, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    data: LinkCreate,
    user: Optional[User] = Depends(optional_current_user),
    link_service: LinkService = Depends(get_link_service),
):
    """Создание новой короткой ссылки.

    - `original_url`: Оригинальный URL для сокращения
    - `expires_at`: Опциональное время истечения ссылки
    - `short_code`: Опциональный кастомный алиас (если не указан, генерируется автоматически)
    - `project_id`: Опциональный ID проекта для добавления ссылки
    - `is_public`: Флаг публичности ссылки

    Доступно для неавторизованных пользователей. В этом случае ссылка сохраняется в публичный проект.
    """
    # Передаем user_id, если пользователь авторизован, иначе None
    user_id = user.id if user else None
    return await link_service.create_link(data, user_id, data.project_id)


@router.get("/search", response_model=List[Link])
async def search_links(
    original_url: str,
    user: User = Depends(current_active_user),
    link_service: LinkService = Depends(get_link_service),
    limit: int = 10,
):
    """Поиск ссылок по части оригинального URL.

    Возвращает список ссылок, оригинальный URL которых содержит указанную подстроку.
    Ищет среди:
    - ссылок пользователя
    - публичных ссылок
    - ссылок из проектов пользователя
    """
    return await link_service.search_links(original_url, user.id, limit)


@router.get("/popular", response_model=List[LinkResponse])
async def get_popular_links(
    limit: int = 10,
    link_service: LinkService = Depends(get_link_service),
):
    """Получение популярных ссылок.

    Args:
        limit: Максимальное количество ссылок
        link_service: Сервис для работы со ссылками

    Returns:
        Список популярных ссылок
    """
    links = await link_service.get_popular_links(limit)
    return [
        LinkResponse(
            original_url=link.original_url,
            short_code=link.short_code,
            expires_at=link.expires_at,
            clicks_count=link.clicks_count,
        )
        for link in links
    ]


@router.put("/{short_code}", response_model=Link)
async def update_link(
    short_code: str,
    data: LinkUpdate,
    user: User = Depends(current_active_user),
    link_service: LinkService = Depends(get_link_service),
):
    """Обновление ссылки.

    Может обновлять оригинальный URL, время истечения и флаг публичности.
    Только владелец ссылки или участник проекта с правами администратора может обновлять ссылку.
    """
    return await link_service.update_link(short_code, data, user.id)


@router.delete("/{short_code}", response_model=Dict[str, Any])
async def delete_link(
    short_code: str,
    user: User = Depends(current_active_user),
    link_service: LinkService = Depends(get_link_service),
):
    """Удаление ссылки.

    Только владелец ссылки или администратор проекта может удалить ссылку.
    """
    return await link_service.delete_link(short_code, user.id)


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(
    short_code: str,
    user: Optional[User] = Depends(optional_current_user),
    link_service: LinkService = Depends(get_link_service),
):
    """Получение статистики использования ссылки.

    Возвращает информацию о ссылке, включая:
    - оригинальный URL
    - дату создания
    - количество переходов
    - дату последнего использования
    - время истечения

    Для публичных ссылок не требует аутентификации.
    Для приватных ссылок требуется быть владельцем или участником проекта.
    """
    # Если пользователь не авторизован, можно получить статистику только для публичных ссылок
    user_id = user.id if user else None
    return await link_service.get_link_stats(short_code, user_id)
