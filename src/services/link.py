from datetime import datetime, timedelta, timezone
import random
import string
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.utils import ensure_timezone
from src.core.logger import logger
from src.models.link import Link
from src.models.project import Project, project_members
from src.models.user import User
from src.schemas.link import (
    LinkCreate,
    LinkUpdate,
    LinkStats,
    LinkCache,
    LinkCacheStatic,
    LinkClickStats,
)
from src.utils.cache import cache_manager


class LinkService:
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса ссылок.

        Args:
            session: Сессия базы данных
        """
        self.session = session
        self.cache_prefix = "link:"
        self.cache_ttl = 3600  # 1 час

    async def create_link(
        self,
        data: LinkCreate,
        user_id: Optional[UUID] = None,
        project_id: Optional[int] = None,
    ) -> Link:
        """Создание новой короткой ссылки.

        Args:
            data: Данные для создания ссылки
            user_id: ID пользователя (None для анонимных пользователей)
            project_id: ID проекта (опционально)

        Returns:
            Созданная ссылка

        Raises:
            HTTPException: Если проект не найден, пользователь не имеет доступа к проекту,
                          или кастомный алиас уже занят, или время истечения слишком мало
        """
        # Импортируем ProjectService здесь, чтобы избежать циклических зависимостей
        from src.services.project import ProjectService

        project_service = ProjectService(self.session)
        # Получаем публичный проект
        public_project = await project_service.create_public_project()

        # Если пользователь не авторизован, используем публичный проект
        if user_id is None:
            # Проверяем наличие владельца у публичного проекта
            if not public_project.owner_id:
                logger.error(
                    f" > > Public project has no owner:\n > > {public_project}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось получить владельца публичного проекта",
                )

            max_lifetime = timedelta(public_project.default_link_lifetime_days)

            # Всегда устанавливаем срок истечения для ссылок, созданных анонимно
            current_time = datetime.now(timezone.utc)
            if not data.expires_at or (
                ensure_timezone(data.expires_at) - current_time > max_lifetime
            ):
                data.expires_at = current_time + max_lifetime

            # Всегда устанавливаем флаг публичности для анонимных ссылок
            data.is_public = True

            # Используем владельца публичного проекта и ID проекта
            user_id = public_project.owner_id
            data.project_id = public_project.id
        elif project_id:
            # Если проект указан явно, используем его
            data.project_id = project_id
        elif data.project_id is None:
            # Если project_id не указан ни в параметрах, ни в данных, используем публичный проект
            data.project_id = public_project.id

        # Проверяем уникальность короткого кода
        if data.short_code:
            existing_link = await self._get_link_by_short_code(data.short_code)
            if existing_link:
                logger.debug(
                    f" > > Short code '{data.short_code}' already exists:\n > > {existing_link}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Короткий код '{data.short_code}' уже занят",
                )
        else:
            logger.debug(" > > Short code not provided, generating new one")
            # Генерируем короткий код или используем предоставленный кастомный алиас
            data.short_code = await self._generate_short_code()

        # Определяем срок жизни ссылки на основе проекта
        project = await self._get_project_by_id(data.project_id)

        # Проверяем, имеет ли пользователь доступ к проекту (если это не анонимный доступ)
        if user_id is not None and data.project_id != public_project.id:
            await self._check_user_in_project(data.project_id, user_id)

        # Если срок жизни не указан, используем значение по умолчанию из проекта
        current_time = datetime.now(timezone.utc)
        min_expiration_time = current_time + timedelta(minutes=5)

        if not data.expires_at:
            days = project.default_link_lifetime_days
            data.expires_at = current_time + timedelta(days=days)
        else:
            # Приводим expires_at к UTC, если указан
            data.expires_at = ensure_timezone(data.expires_at)

            # Проверяем, что время экспирации не менее чем через 5 минут
            if data.expires_at < min_expiration_time:
                logger.warning(
                    f" > > Expires in less than 5 minutes: {data.expires_at} < {min_expiration_time}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Срок действия ссылки должен быть не менее 5 минут от текущего времени",
                )

        # Создаем ссылку
        new_link = Link(
            original_url=str(data.original_url),
            short_code=data.short_code,
            expires_at=data.expires_at,
            owner_id=user_id,
            project_id=data.project_id,
            is_public=data.is_public,
        )

        self.session.add(new_link)
        await self.session.commit()
        await self.session.refresh(new_link)
        logger.debug(f"Created link:\n{new_link}")

        return new_link

    async def get_link_by_short_code(
        self, short_code: str, user: Optional[User] = None
    ) -> Link:
        """Получение ссылки по короткому коду.

        Args:
            short_code: Короткий код ссылки
            user: Пользователь, если он авторизован
        Returns:
            Ссылка, если она найдена и не истекла

        Raises:
            HTTPException: Если ссылка не найдена или истекла
        """
        link = None  # Initialize link to None

        CAN_READ, CAN_MODIFY = await self._check_link_permissions(
            short_code, user.id if user else None
        )
        logger.debug(f" > > CAN_READ: {CAN_READ}, CAN_MODIFY: {CAN_MODIFY}")

        if not CAN_READ:
            logger.warning(f" > > Link {short_code}: not found or no access")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ссылка не найдена или у вас нет доступа к ней",
            )

        # Пробуем получить статические данные ссылки из кэша
        logger.debug(f" > > Getting link from cache: {short_code}")

        # Ключи для разных типов кэша
        static_cache_key = f"{self.cache_prefix}{short_code}:static"
        stats_cache_key = f"{self.cache_prefix}{short_code}:stats"

        # Получаем статические данные из кэша
        cached_static = await cache_manager.get(static_cache_key)
        current_time = datetime.now(timezone.utc)

        if cached_static:
            logger.debug(f" > > Link found in static cache: {short_code}")
            link_static = LinkCacheStatic(**cached_static)

            # Проверяем, не истекла ли ссылка
            if link_static.expires_at:
                expires_at = ensure_timezone(
                    datetime.fromisoformat(link_static.expires_at)
                )
                if expires_at < current_time:
                    logger.debug(
                        f" > > Cached link expired: {expires_at} < {current_time}"
                    )
                    # Удаляем истекшую ссылку из кэша
                    await cache_manager.delete(static_cache_key)
                    await cache_manager.delete(stats_cache_key)
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail="Срок действия ссылки истек",
                    )

            # Пробуем получить статистику из кэша или из БД
            stats = await self._get_link_stats(short_code)

            # Собираем полную информацию о ссылке
            return link_static.to_link(
                clicks_count=stats.clicks_count, last_clicked_at=stats.to_datetime()
            )

        # Если нет в кэше, получаем из БД
        logger.debug(f" > > Getting link from database: {short_code}")
        link = await self._get_link_by_short_code(short_code)

        if not link:
            logger.warning(f" > > Link not found: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ссылка '{short_code}' не найдена",
            )

        # Проверяем, не истекла ли ссылка
        logger.debug(
            f" > > Checking expiration: current_time={current_time}, expires_at={link.expires_at}"
        )
        if link.expires_at and link.expires_at < current_time:
            logger.warning(f" > > Link expired: {link.expires_at} < {current_time}")
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Срок действия ссылки истек"
            )

        # Кэшируем статические данные
        logger.debug(f" > > Caching static link data: {link}")
        link_static = LinkCacheStatic.from_link(link)
        logger.debug(f" > > LinkCacheStatic.model_dump: {link_static}")
        await cache_manager.set(
            static_cache_key, link_static.model_dump(), expire=self.cache_ttl
        )

        # Кэшируем статистику
        logger.debug(f" > > Caching link stats: {short_code}")
        link_stats = LinkClickStats.from_link(link)
        await cache_manager.set(
            stats_cache_key, link_stats.model_dump(), expire=self.cache_ttl
        )

        return link

    async def update_link_stats(self, link_id: int) -> None:
        """Обновление статистики использования ссылки.

        Args:
            link_id: ID ссылки
        """
        # Обновляем статистику в БД
        stmt = (
            update(Link)
            .where(Link.id == link_id)
            .values(
                clicks_count=Link.clicks_count + 1,
                last_clicked_at=datetime.now(timezone.utc),
            )
            .returning(Link.short_code, Link.clicks_count, Link.last_clicked_at)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        await self.session.commit()

        if row:
            short_code = row[0]
            clicks_count = row[1]
            last_clicked_at = row[2]

            # Обновляем только статистику в кэше, не трогая статические данные
            logger.debug(f" > > Updating only stats cache for: {short_code}")
            stats_cache_key = f"{self.cache_prefix}{short_code}:stats"

            # Создаем объект статистики
            link_stats = LinkClickStats(
                clicks_count=clicks_count,
                last_clicked_at=ensure_timezone(
                    last_clicked_at
                ).isoformat(),  # Convert to ISO string
            )

            # Обновляем кэш статистики
            await cache_manager.set(
                stats_cache_key, link_stats.model_dump(), expire=self.cache_ttl
            )

    async def _get_link_stats(
        self, short_code: str, cache_key: str = ""
    ) -> LinkClickStats:
        """Получение статистики ссылки из кэша или базы данных.

        Args:
            short_code: Короткий код ссылки

        Returns:
            Статистика ссылки
        """
        if cache_key == "":
            cache_key = f"{self.cache_prefix}{short_code}:stats"

        # Пробуем получить из кэша
        cached_stats = await cache_manager.get(cache_key)
        if cached_stats:
            return LinkClickStats(**cached_stats)

        # Если нет в кэше, получаем из БД
        link = await self._get_link_by_short_code(short_code)
        if link:
            stats = LinkClickStats.from_link(link)

            # Кэшируем результат
            await cache_manager.set(
                cache_key, stats.model_dump(), expire=self.cache_ttl
            )
            return stats

        # Если ссылка не найдена, возвращаем пустую статистику
        return LinkClickStats()

    async def update_link(
        self, short_code: str, data: LinkUpdate, user_id: UUID
    ) -> Link:
        """Обновление ссылки.

        Args:
            short_code: Короткий код ссылки
            data: Данные для обновления
            user_id: ID пользователя

        Returns:
            Обновленная ссылка

        Raises:
            HTTPException: Если ссылка не найдена или пользователь не является владельцем
        """
        link = await self._get_link_by_short_code(short_code)

        if not link:
            logger.warning(f" > > Link not found: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ссылка с кодом '{short_code}' не найдена",
            )

        # Проверяем, является ли пользователь владельцем ссылки
        if link.owner_id != user_id:
            # Проверяем, имеет ли пользователь доступ к ссылке через проект
            has_access = await self._check_link_project_access(link.id, user_id)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет прав на редактирование этой ссылки",
                )

        # Обновляем только предоставленные поля
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return link

        # Преобразуем HttpUrl в строку для хранения в БД
        if "original_url" in update_data:
            update_data["original_url"] = str(update_data["original_url"])

        # Приводим expires_at к UTC, если указан
        if "expires_at" in update_data:
            if isinstance(update_data["expires_at"], str):
                update_data["expires_at"] = ensure_timezone(
                    datetime.fromisoformat(update_data["expires_at"])
                )
            elif isinstance(update_data["expires_at"], datetime):
                # Если уже datetime, просто добавляем часовой пояс если его нет
                update_data["expires_at"] = ensure_timezone(update_data["expires_at"])

        stmt = update(Link).where(Link.id == link.id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()

        # Получаем обновленную ссылку
        return await self._get_link_by_short_code(short_code)

    async def delete_link(self, short_code: str, user_id: UUID) -> Dict[str, Any]:
        """Удаление ссылки.

        Args:
            short_code: Короткий код ссылки
            user_id: ID пользователя

        Returns:
            Сообщение об успешном удалении

        Raises:
            HTTPException: Если ссылка не найдена или пользователь не имеет прав
        """
        link = await self._get_link_by_short_code(short_code)

        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ссылка с кодом '{short_code}' не найдена",
            )

        # Проверяем, является ли пользователь владельцем ссылки
        if link.owner_id != user_id:
            # Проверяем, имеет ли пользователь доступ к ссылке через проект
            has_access = await self._check_link_project_admin(link.id, user_id)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет прав на удаление этой ссылки",
                )

        # Удаляем саму ссылку
        stmt = delete(Link).where(Link.id == link.id)
        await self.session.execute(stmt)
        await self.session.commit()

        return {"message": f"Ссылка с кодом '{short_code}' успешно удалена"}

    async def get_link_stats(self, short_code: str, user_id: UUID) -> LinkStats:
        """Получение статистики по ссылке.

        Args:
            short_code: Короткий код ссылки
            user_id: ID пользователя

        Returns:
            Статистика по ссылке

        Raises:
            HTTPException: Если ссылка не найдена или пользователь не имеет доступа
        """
        # Получаем базовую информацию о ссылке из БД (нет смысла кешировать всю статистику отдельно)
        link = await self._get_link_by_short_code(short_code)

        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ссылка с кодом '{short_code}' не найдена",
            )

        # Проверяем доступ пользователя к ссылке
        if not link.is_public and link.owner_id != user_id:
            has_access = await self._check_link_project_access(link.id, user_id)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет доступа к статистике этой ссылки",
                )

        # Получаем статистику кликов из кеша или БД
        stats = await self._get_link_stats(short_code)

        # Формируем полный объект статистики
        # Преобразуем last_clicked_at из строки ISO в datetime, если есть
        last_clicked_at = stats.to_datetime()

        # Создаем объект LinkStats с данными из link и данными статистики из кеша
        stats_data = {
            "id": link.id,
            "short_code": link.short_code,
            "original_url": link.original_url,
            "expires_at": link.expires_at,
            "is_public": link.is_public,
            "created_at": link.created_at,
            "clicks_count": stats.clicks_count,
            "last_clicked_at": last_clicked_at,
        }

        return LinkStats(**stats_data)

    async def search_links(
        self, original_url: str, user_id: UUID, limit: int = 10
    ) -> List[Link]:
        """Поиск ссылок по оригинальному URL.

        Args:
            original_url: Часть оригинального URL
            user_id: ID пользователя
            limit: Максимальное количество результатов

        Returns:
            Список найденных ссылок
        """

        # select

        # Ищем ссылки, принадлежащие пользователю
        query = (
            select(Link)
            .where(
                Link.original_url.like("%" + original_url + "%"),
                Link.owner_id == user_id,
            )
            .limit(limit)
        )

        result = await self.session.execute(query)
        links = result.scalars().all()

        # Ищем публичные ссылки
        query = (
            select(Link)
            .where(
                Link.original_url.like("%" + original_url + "%"),
                Link.is_public == True,
                Link.owner_id != user_id,
            )
            .limit(limit)
        )

        result = await self.session.execute(query)
        public_links = result.scalars().all()

        # Ищем ссылки из проектов пользователя
        query = (
            select(Link)
            .join(project_members, Link.project_id == project_members.c.project_id)
            .where(
                Link.original_url.like("%" + original_url + "%"),
                project_members.c.user_id == user_id,
                Link.owner_id != user_id,
            )
            .limit(limit)
        )

        result = await self.session.execute(query)
        project_links = result.scalars().all()

        # Объединяем результаты
        all_links = links + public_links + project_links
        # Удаляем дубликаты и ограничиваем количество результатов
        return list(set(all_links))[:limit]

    async def get_user_links(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[Link]:
        """Получение всех ссылок пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество результатов
            offset: Смещение для пагинации

        Returns:
            Список ссылок пользователя
        """
        query = (
            select(Link)
            .where(Link.owner_id == user_id)
            .order_by(Link.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_project_links(
        self, project_id: int, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[Link]:
        """Получение всех ссылок проекта.

        Args:
            project_id: ID проекта
            user_id: ID пользователя
            limit: Максимальное количество результатов
            offset: Смещение для пагинации

        Returns:
            Список ссылок проекта

        Raises:
            HTTPException: Если проект не найден или пользователь не имеет доступа
        """
        # Проверяем доступ пользователя к проекту
        await self._check_user_in_project(project_id, user_id)

        # Получаем ссылки проекта
        query = (
            select(Link)
            .where(Link.project_id == project_id)
            .order_by(Link.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_popular_links(self, limit: int = 10) -> List[Link]:
        """Получение популярных ссылок.

        Args:
            limit: Максимальное количество ссылок

        Returns:
            Список популярных ссылок
        """
        # Пробуем получить из кэша
        cache_key = f"{self.cache_prefix}popular:{limit}"
        cached_links = await cache_manager.get(cache_key)
        if cached_links:
            logger.debug(
                f" > > Getting popular links from cache. Count: {len(cached_links)}"
            )
            links = []
            for link_data in cached_links:
                # Используем LinkCache для десериализации данных из кэша
                link_cache = LinkCache(**link_data)
                link = link_cache.to_link()
                links.append(link)
            return links

        # Если нет в кэше, получаем из БД
        logger.debug(f" > > Getting popular links from database")
        query = (
            select(Link)
            .where(Link.expires_at > datetime.now(timezone.utc))
            .order_by(Link.clicks_count.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        links = result.scalars().all()

        logger.debug(f" > > Found {len(links)} popular links in database")

        # Кэшируем результат на меньшее время, так как это часто меняющиеся данные
        await cache_manager.set(
            cache_key,
            [LinkCache.from_link(link).model_dump() for link in links],
            expire=600,  # 10 минут
        )

        return links

    async def cleanup_expired_links(self) -> int:
        """Очистка истекших ссылок.

        Returns:
            Количество удаленных ссылок
        """
        # Удаляем истекшие ссылки
        current_time = datetime.now(timezone.utc)
        logger.debug(f" > > Cleanup: current_time={current_time}")

        # Сначала получаем список истекших ссылок для логирования
        query = select(Link).where(
            (Link.expires_at.isnot(None)) & (Link.expires_at < current_time)
        )
        result = await self.session.execute(query)
        expired_links = result.scalars().all()
        logger.debug(f" > > Found {len(expired_links)} expired links")
        for link in expired_links:
            logger.debug(
                f" > > Invalidate cache for {link}: expired at {link.expires_at} < {current_time}"
            )
            # Удаляем истекшую ссылку из кэша
            await cache_manager.delete(f"{self.cache_prefix}{link.short_code}")

        # Удаляем истекшие ссылки
        stmt = delete(Link).where(
            (Link.expires_at.isnot(None)) & (Link.expires_at < current_time)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        logger.debug(" > > Invalidate cache for popular links")
        # Очищаем кэш популярных ссылок
        await cache_manager.delete(f"{self.cache_prefix}popular:*")

        deleted_count = result.rowcount
        logger.debug(f" > > Cleaned up {deleted_count} expired links")
        return deleted_count

    async def _generate_short_code(self, length: int = 7) -> str:
        """Генерация уникального короткого кода.

        Args:
            length: Длина короткого кода

        Returns:
            Уникальный короткий код
        """
        while True:
            # Генерируем случайный код из букв и цифр
            chars = string.ascii_letters + string.digits
            short_code = "".join(random.choice(chars) for _ in range(length))

            # Проверяем уникальность кода
            existing = await self._get_link_by_short_code(short_code)
            if not existing:
                return short_code

    async def _get_link_by_short_code(self, short_code: str) -> Optional[Link]:
        """Получение ссылки по короткому коду без проверок.

        Args:
            short_code: Короткий код ссылки

        Returns:
            Ссылка или None, если не найдена
        """
        query = select(Link).where(Link.short_code == short_code)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def _get_project_by_id(self, project_id: int) -> Project:
        """Получение проекта по ID без проверок.

        Args:
            project_id: ID проекта

        Returns:
            Проект, если найден

        Raises:
            HTTPException: Если проект не найден
        """
        query = select(Project).where(Project.id == project_id)
        result = await self.session.execute(query)
        project = result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Проект с ID {project_id} не найден",
            )

        return project

    async def _check_user_in_project(self, project_id: int, user_id: UUID) -> bool:
        """Проверка, является ли пользователь членом проекта.

        Args:
            project_id: ID проекта
            user_id: ID пользователя

        Returns:
            True, если пользователь имеет доступ к проекту

        Raises:
            HTTPException: Если пользователь не имеет доступа к проекту
        """
        # Получаем проект
        project = await self._get_project_by_id(project_id)

        # Проверяем, является ли пользователь владельцем
        if project.owner_id == user_id:
            return True

        # Проверяем, является ли пользователь членом проекта
        query = select(project_members).where(
            project_members.c.project_id == project_id,
            project_members.c.user_id == user_id,
        )
        result = await self.session.execute(query)

        if not result.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к этому проекту",
            )

        return True

    async def _check_link_project_access(self, link_id: int, user_id: UUID) -> bool:
        """Проверка, имеет ли пользователь доступ к ссылке через проект.

        Args:
            link_id: ID ссылки
            user_id: ID пользователя

        Returns:
            True, если пользователь имеет доступ к ссылке через проект
        """
        # Получаем ссылку вместе с проектом
        query = select(Link).where(Link.id == link_id)
        result = await self.session.execute(query)
        link = result.scalars().first()

        if not link:
            return False

        # Проверяем, является ли пользователь участником проекта
        query = select(project_members).where(
            (project_members.c.project_id == link.project_id)
            & (project_members.c.user_id == user_id)
        )
        result = await self.session.execute(query)
        member = result.first()

        return member is not None

    async def _check_link_project_admin(self, link_id: int, user_id: UUID) -> bool:
        """Проверка, является ли пользователь администратором проекта, к которому привязана ссылка.

        Args:
            link_id: ID ссылки
            user_id: ID пользователя

        Returns:
            True, если пользователь является администратором проекта
        """
        # Получаем ссылку вместе с проектом
        query = select(Link).where(Link.id == link_id)
        result = await self.session.execute(query)
        link = result.scalars().first()

        if not link:
            return False

        # Проверяем, является ли пользователь администратором проекта
        query = select(project_members).where(
            (project_members.c.project_id == link.project_id)
            & (project_members.c.user_id == user_id)
            & (project_members.c.is_admin == True)
        )
        result = await self.session.execute(query)
        admin = result.first()

        return admin is not None

    async def _get_link_by_id(self, link_id: int) -> Optional[Link]:
        """Получение ссылки по ID.

        Args:
            link_id: ID ссылки

        Returns:
            Ссылка или None, если не найдена
        """
        query = select(Link).where(Link.id == link_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def _check_link_permissions(
        self, short_code: str, user_id: UUID
    ) -> Tuple[bool, bool]:
        """Проверка прав доступа к ссылке.

        Args:
            short_code: Короткий код ссылки
            user_id: ID пользователя

        Returns:
            Кортеж из двух булевых значений:
            - Первый элемент: True, если пользователь может читать ссылку
            - Второй элемент: True, если пользователь может изменять ссылку
        """
        link = None  # Initialize link to None
        # Проверяем, есть ли результат в кэше
        cache_key = f"{self.cache_prefix}{short_code}:acl:{user_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        # Получаем права доступа к ссылке вот таким запросом:
        # SELECT
        #     l.id,
        #     l.short_code,
        #     l.original_url,
        #     l.expires_at,
        #     l.project_id,
        #     l.owner_id,
        #     l.is_public,
        #     -- Флаги доступа (возвращают булевы значения)
        #     l.is_public AS can_read_public,
        #     (l.owner_id = :user_id) AS is_owner,
        #     (pm.user_id IS NOT NULL) AS is_project_member,
        #     (pm.is_admin IS TRUE) AS is_project_admin,
        #     -- Итоговые разрешения на основе флагов
        #     (l.is_public OR l.owner_id = :user_id OR pm.user_id IS NOT NULL) AS can_read,
        #     (l.owner_id = :user_id OR pm.is_admin IS TRUE) AS can_modify
        # FROM
        #     links l
        # LEFT JOIN
        #     project_members pm ON l.project_id = pm.project_id AND pm.user_id = :user_id
        # WHERE
        #     l.short_code = :short_code
        query = (
            select(
                Link,
                Link.is_public.label("can_read_public"),
                (Link.owner_id == user_id).label("is_owner"),
                (project_members.c.user_id.isnot(None)).label("is_project_member"),
                (project_members.c.is_admin.is_(True)).label("is_project_admin"),
                or_(
                    Link.is_public,
                    Link.owner_id == user_id,
                    project_members.c.user_id.isnot(None),
                ).label("can_read"),
                or_(
                    Link.owner_id == user_id, project_members.c.is_admin.is_(True)
                ).label("can_modify"),
            )
            .select_from(Link)
            .outerjoin(
                project_members,
                and_(
                    Link.project_id == project_members.c.project_id,
                    project_members.c.user_id == user_id,
                ),
            )
            .where(Link.short_code == short_code)
        )

        result = await self.session.execute(query)
        row = result.first()  # Получаем всю строку, а не только первый объект

        if not row:
            can_read, can_modify = False, False
            logger.debug(f" > > Link not found: {short_code}")
        else:
            # Распаковываем все колонки из результата
            (link, _, _, _, _, can_read, can_modify) = row
            # Move logging inside the else block
            logger.debug(f" > > Link: {link}")
            logger.debug(
                f" > > Permissions: can_read={can_read}, can_modify={can_modify}"
            )

        # Кешируем результат на 10 минут
        await cache_manager.set(cache_key, (can_read, can_modify), expire=300)

        return can_read, can_modify
