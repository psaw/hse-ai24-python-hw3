import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import uuid4

from src.models.link import Link, utcnow_with_tz
from src.models.project import Project
from src.models.user import User
from tests.helpers import (
    create_test_user,
    create_test_project,
    create_test_link,
)
from tests.fixtures import (
    test_user,
    test_project,
    test_link,
    test_links,
)


@pytest.mark.asyncio
class TestLinkModel:
    """Тесты для модели Link."""

    async def test_link_repr_method(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Тестирует метод __repr__ модели Link."""
        # Создаем экземпляр Link с помощью вспомогательной функции
        link = await create_test_link(
            db=db_session,
            original_url="https://example.com",
            owner=test_user,
            project=test_project,
        )

        # Проверяем, что __repr__ возвращает строку с нужными данными
        repr_result = repr(link)
        assert isinstance(repr_result, str)

        expected_repr = f"Link(id={link.id}, short={link.short_code}, orig={link.original_url}, prj={link.project_id}, exp={link.expires_at})"
        assert repr_result == expected_repr

    async def test_create_link(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Тест создания ссылки."""
        # Создаем ссылку с помощью вспомогательной функции
        link = await create_test_link(
            db=db_session,
            original_url="https://example.com",
            owner=test_user,
            project=test_project,
            short_code=f"test123_{uuid4().hex[:8]}",
        )

        await db_session.refresh(link)

        # Проверяем, что ссылка создана и имеет корректные поля
        assert link.id is not None
        assert isinstance(link.id, int)
        assert link.original_url == "https://example.com"
        assert link.short_code.startswith("test123_")
        assert link.project_id == test_project.id
        assert link.owner_id == test_user.id
        assert link.clicks_count == 0
        assert link.last_clicked_at is None
        assert link.created_at is not None
        assert isinstance(link.created_at, datetime)
        assert link.created_at.tzinfo == timezone.utc

    async def test_read_link(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Тест чтения ссылки."""
        # Создаем ссылку с помощью вспомогательной функции
        short_code = f"test123_{uuid4().hex[:8]}"
        link = await create_test_link(
            db=db_session,
            original_url="https://example.com",
            short_code=short_code,
            owner=test_user,
            project=test_project,
        )

        # Получаем ссылку из базы данных
        retrieved_link = await db_session.get(Link, link.id)

        # Проверяем, что ссылка получена корректно
        assert retrieved_link is not None
        assert retrieved_link.id == link.id
        assert retrieved_link.original_url == "https://example.com"
        assert retrieved_link.short_code == short_code
        assert retrieved_link.project_id == test_project.id
        assert retrieved_link.owner_id == test_user.id

    async def test_update_link(self, db_session: AsyncSession, test_link: Link):
        """Тест обновления ссылки."""
        # Обновляем ссылку из фикстуры
        test_link.original_url = "https://updated-example.com"
        test_link.is_public = True

        await db_session.commit()
        await db_session.refresh(test_link)

        # Проверяем, что ссылка обновлена
        assert test_link.original_url == "https://updated-example.com"
        assert test_link.is_public is True

    async def test_delete_link(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Тест удаления ссылки."""
        # Создаем ссылку с помощью вспомогательной функции
        short_code = f"test123_{uuid4().hex[:8]}"
        link = await create_test_link(
            db=db_session,
            original_url="https://example.com",
            short_code=short_code,
            owner=test_user,
            project=test_project,
        )

        # Сохраняем ID для проверки
        link_id = link.id

        # Удаляем ссылку
        await db_session.delete(link)
        await db_session.commit()

        # Проверяем, что ссылка удалена
        deleted_link = await db_session.get(Link, link_id)
        assert deleted_link is None

    def test_utcnow_with_tz(self):
        """Тест функции utcnow_with_tz."""
        # Получаем текущее время с помощью функции
        now = utcnow_with_tz()

        # Проверяем, что время имеет временную зону UTC
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    async def test_with_existing_fixtures(
        self, db_session: AsyncSession, test_links: list
    ):
        """Тест с использованием готовых фикстур."""
        # Проверяем, что фикстуры созданы корректно
        assert (
            len(test_links) == 5
        )  # В create_multiple_test_links по умолчанию создается 5 ссылок

        # Проверяем свойства ссылок
        for link in test_links:
            assert link.original_url.startswith("https://example.com/")
            assert link.short_code.startswith("test_")
            assert link.clicks_count == 0
