import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from src.models.project import Project
from src.models.user import User
from src.models.link import Link
from tests.helpers import (
    create_test_user,
    create_test_project,
    create_test_link,
    add_user_to_project,
)
from tests.fixtures import (
    test_user,
    test_project,
    test_project_with_members,
    test_links,
)


@pytest.mark.asyncio
class TestProjectModel:
    """Тесты для модели Project."""

    async def test_create_project(self, db_session: AsyncSession):
        """Тест создания проекта."""
        # Создаем проект
        project = Project(
            name="Тестовый проект",
            description="Описание тестового проекта",
            default_link_lifetime_days=30,
            created_at=datetime.now(timezone.utc),
            owner_id=None,
        )

        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Проверяем, что проект создан и имеет корректные поля
        assert project.id is not None
        assert isinstance(project.id, int)
        assert project.name == "Тестовый проект"
        assert project.description == "Описание тестового проекта"
        assert project.default_link_lifetime_days == 30
        assert project.created_at is not None
        assert isinstance(project.created_at, datetime)
        assert project.created_at.tzinfo == timezone.utc
        assert project.owner_id is None
        assert (
            repr(project)
            == f"Project(id={project.id}, name={project.name}, owner_id={project.owner_id})"
        )

    async def test_read_project(self, db_session: AsyncSession):
        """Тест чтения проекта."""
        # Создаем проект с помощью вспомогательной функции
        project = await create_test_project(
            db=db_session,
            name="Проект для чтения",
            description="Описание проекта для чтения",
        )

        # Получаем проект из базы данных
        retrieved_project = await db_session.get(Project, project.id)

        # Проверяем, что проект получен корректно
        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == "Проект для чтения"
        assert retrieved_project.description == "Описание проекта для чтения"

    async def test_update_project(self, db_session: AsyncSession):
        """Тест обновления проекта."""
        # Создаем проект с помощью вспомогательной функции
        project = await create_test_project(
            db=db_session, name="Проект до обновления", description="Старое описание"
        )

        # Обновляем проект
        project.name = "Проект после обновления"
        project.description = "Новое описание"

        await db_session.commit()
        await db_session.refresh(project)

        # Проверяем, что проект обновлен
        assert project.name == "Проект после обновления"
        assert project.description == "Новое описание"

    async def test_delete_project(self, db_session: AsyncSession):
        """Тест удаления проекта."""
        # Создаем проект с помощью вспомогательной функции
        project = await create_test_project(
            db=db_session,
            name="Проект для удаления",
            description="Описание проекта для удаления",
        )

        # Сохраняем ID для проверки
        project_id = project.id

        # Удаляем проект
        await db_session.delete(project)
        await db_session.commit()

        # Проверяем, что проект удален
        deleted_project = await db_session.get(Project, project_id)
        assert deleted_project is None

    async def test_project_links_relationship(
        self, db_session: AsyncSession, test_user: User
    ):
        """Тест связи проекта и ссылок."""
        # Создаем проект
        project = await create_test_project(
            db=db_session,
            name="Проект со ссылками",
            description="Описание проекта со ссылками",
            owner=test_user,
        )

        # Создаем ссылки для проекта
        link1 = await create_test_link(
            db=db_session,
            original_url="https://example.com/1",
            owner=test_user,
            project=project,
        )

        link2 = await create_test_link(
            db=db_session,
            original_url="https://example.com/2",
            owner=test_user,
            project=project,
        )

        # Используем selectinload для жадной загрузки связей
        stmt = (
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.links))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Проверяем связь с ссылками
        assert len(project.links) == 2
        assert any(
            link.original_url == "https://example.com/1" for link in project.links
        )
        assert any(
            link.original_url == "https://example.com/2" for link in project.links
        )

        # Получаем ссылки напрямую для проверки обратной связи
        stmt = (
            select(Link)
            .where(Link.id.in_([link1.id, link2.id]))
            .options(selectinload(Link.project))
        )
        result = await db_session.execute(stmt)
        links = result.scalars().all()

        # Проверяем связь в обратном направлении
        for link in links:
            assert link.project_id == project.id
            assert link.project.name == "Проект со ссылками"

    async def test_project_members_relationship(self, db_session: AsyncSession):
        """Тест связи проекта и пользователей (участников)."""
        # Создаем проект
        project = await create_test_project(
            db_session,
            name="Проект с участниками",
            description="Описание проекта с участниками",
        )

        # Создаем пользователей с помощью вспомогательной функции
        user1 = await create_test_user(db_session)
        user2 = await create_test_user(db_session)

        # Добавляем пользователей в проект через вспомогательную функцию
        await add_user_to_project(db_session, project.id, user1.id, is_admin=False)
        await add_user_to_project(db_session, project.id, user2.id, is_admin=False)
        await db_session.commit()

        # Загружаем проект с участниками
        stmt = (
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.members))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Загружаем пользователей с проектами
        stmt = (
            select(User)
            .where(User.id.in_([user1.id, user2.id]))
            .options(selectinload(User.projects))
        )
        result = await db_session.execute(stmt)
        users = result.scalars().all()

        # Проверяем связь с участниками
        assert len(project.members) == 2
        assert any(member.id == user1.id for member in project.members)
        assert any(member.id == user2.id for member in project.members)

        # Проверяем обратную связь
        for user in users:
            assert len(user.projects) == 1
            assert user.projects[0].id == project.id

    async def test_with_existing_fixtures(
        self, db_session: AsyncSession, test_project_with_members: Project
    ):
        """Тест с использованием готовых фикстур."""
        # Загружаем проект с участниками
        stmt = (
            select(Project)
            .where(Project.id == test_project_with_members.id)
            .options(selectinload(Project.members))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Проверяем, что проект имеет участников
        assert (
            len(project.members) >= 2
        )  # В фикстуре test_project_with_members добавляется 2 участника

        # Проверяем свойства проекта
        assert project.name == "Test Project with Members"

    async def test_project_with_links(
        self, db_session: AsyncSession, test_project: Project, test_links: list
    ):
        """Тест проекта с ссылками из фикстур."""
        # Загружаем проект со ссылками
        stmt = (
            select(Project)
            .where(Project.id == test_project.id)
            .options(selectinload(Project.links))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Проверяем, что у проекта есть ссылки
        assert len(project.links) >= 2
