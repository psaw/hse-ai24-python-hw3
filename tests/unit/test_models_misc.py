import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models.user import User
from src.models.project import Project
from src.models.link import Link
from tests.helpers import (
    create_test_user,
    create_test_project,
    create_test_link,
    add_user_to_project,
)
from tests.fixtures import (
    test_user,
    test_admin_user,
    test_project,
    test_project_with_members,
    test_link,
    test_links,
)


@pytest.mark.asyncio
class TestModelsRelationships:
    """Тесты для проверки связей между моделями."""

    async def test_user_project_relationship(self, db_session: AsyncSession):
        """Проверка связи между пользователем и проектом."""
        # Создаем проект с владельцем и участниками
        owner = await create_test_user(db=db_session)
        member1 = await create_test_user(db=db_session)
        member2 = await create_test_user(db=db_session)

        project = await create_test_project(
            db=db_session, name="Test Project", owner=owner
        )

        # Добавляем пользователей в проект
        await add_user_to_project(db_session, project.id, owner.id, is_admin=True)
        await add_user_to_project(db_session, project.id, member1.id)
        await add_user_to_project(db_session, project.id, member2.id)

        await db_session.commit()

        # Загружаем проект с участниками
        stmt = (
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.members))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Проверяем, что есть участники
        assert len(project.members) == 3  # Владелец + 2 участника

        # Загружаем пользователя с проектами
        stmt = (
            select(User)
            .where(User.id == member1.id)
            .options(selectinload(User.projects))
        )
        result = await db_session.execute(stmt)
        user = result.scalar_one()

        # Проверяем, что у пользователя есть связь с проектом
        assert len(user.projects) == 1
        assert user.projects[0].id == project.id

    async def test_project_links_relationship(self, db_session: AsyncSession):
        """Проверка связи между проектом и ссылками."""
        # Создаем все необходимые данные
        user = await create_test_user(db=db_session)

        project = await create_test_project(
            db=db_session, name="Project with links", owner=user
        )

        # Создаем ссылки
        link1 = await create_test_link(
            db=db_session,
            original_url="https://example.com/1",
            owner=user,
            project=project,
        )

        link2 = await create_test_link(
            db=db_session,
            original_url="https://example.com/2",
            owner=user,
            project=project,
        )

        await db_session.commit()

        # Загружаем проект со ссылками
        stmt = (
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.links))
        )
        result = await db_session.execute(stmt)
        project = result.scalar_one()

        # Проверяем, что у проекта есть ссылки
        assert len(project.links) == 2
        assert all(link.project_id == project.id for link in project.links)

    async def test_user_links_relationship(self, db_session: AsyncSession):
        """Проверка связи между пользователем и его ссылками."""
        # Создаем все необходимые данные
        user = await create_test_user(db=db_session)

        project = await create_test_project(
            db=db_session, name="Project for links", owner=user
        )

        # Создаем ссылки
        link1 = await create_test_link(
            db=db_session,
            original_url="https://example.com/1",
            owner=user,
            project=project,
        )

        link2 = await create_test_link(
            db=db_session,
            original_url="https://example.com/2",
            owner=user,
            project=project,
        )

        await db_session.commit()

        # Загружаем пользователя со ссылками
        stmt = select(User).where(User.id == user.id).options(selectinload(User.links))
        result = await db_session.execute(stmt)
        user = result.scalar_one()

        # Проверяем, что у пользователя есть ссылки
        assert len(user.links) == 2
        assert all(link.owner_id == user.id for link in user.links)

    async def test_admin_access_to_all_projects(self, db_session: AsyncSession):
        """Проверка доступа админа ко всем проектам."""
        # Создаем администратора и проект
        admin = await create_test_user(
            db=db_session, is_superuser=True, email="test_admin@example.com"
        )

        owner = await create_test_user(db=db_session)

        project = await create_test_project(
            db=db_session, name="Admin access project", owner=owner
        )

        # Добавляем админа в проект
        await add_user_to_project(
            db_session, project_id=project.id, user_id=admin.id, is_admin=True
        )

        await db_session.commit()

        # Загружаем админа с проектами
        stmt = (
            select(User).where(User.id == admin.id).options(selectinload(User.projects))
        )
        result = await db_session.execute(stmt)
        admin_user = result.scalar_one()

        # Проверяем доступ к проекту
        assert len(admin_user.projects) == 1
        assert admin_user.projects[0].id == project.id

    async def test_multi_project_ownership(self, db_session: AsyncSession):
        """Проверка владения пользователем несколькими проектами."""
        # Создаем пользователя
        user = await create_test_user(db=db_session)

        # Создаем дополнительные проекты для пользователя
        project1 = await create_test_project(
            db=db_session, name="User Project 1", owner=user
        )

        project2 = await create_test_project(
            db=db_session, name="User Project 2", owner=user
        )

        # Добавляем пользователя как участника проектов
        await add_user_to_project(db_session, project1.id, user.id, is_admin=True)
        await add_user_to_project(db_session, project2.id, user.id, is_admin=True)

        await db_session.commit()

        # Загружаем пользователя с проектами
        stmt = (
            select(User).where(User.id == user.id).options(selectinload(User.projects))
        )
        result = await db_session.execute(stmt)
        user = result.scalar_one()

        # Проверяем, что пользователь связан с обоими проектами
        assert len(user.projects) == 2

        # Проверяем, что в обоих проектах пользователь указан как владелец
        projects_owned = [p for p in user.projects if p.owner_id == user.id]
        assert len(projects_owned) == 2
