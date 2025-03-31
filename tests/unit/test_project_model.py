import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, text

from src.models.project import Project


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
        # Создаем проект
        project = Project(
            name="Проект для чтения", description="Описание проекта для чтения"
        )

        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Получаем проект из базы данных
        retrieved_project = await db_session.get(Project, project.id)

        # Проверяем, что проект получен корректно
        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == "Проект для чтения"
        assert retrieved_project.description == "Описание проекта для чтения"

    async def test_update_project(self, db_session: AsyncSession):
        """Тест обновления проекта."""
        # Создаем проект
        project = Project(name="Проект до обновления", description="Старое описание")

        db_session.add(project)
        await db_session.commit()

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
        # Создаем проект
        project = Project(
            name="Проект для удаления", description="Описание проекта для удаления"
        )

        db_session.add(project)
        await db_session.commit()

        # Сохраняем ID для проверки
        project_id = project.id

        # Удаляем проект
        await db_session.delete(project)
        await db_session.commit()

        # Проверяем, что проект удален
        deleted_project = await db_session.get(Project, project_id)
        assert deleted_project is None

    async def test_project_links_relationship(self, db_session: AsyncSession):
        """Тест связи проекта и ссылок."""
        from src.models.link import Link
        from src.models.user import User

        # Создаем пользователя
        user = User(
            email=f"link_test_user_{uuid4().hex}@example.com",
            hashed_password="hashedpassword123",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Создаем проект
        project = Project(
            name="Проект со ссылками",
            description="Описание проекта со ссылками",
            owner_id=user.id,
        )

        # Создаем ссылки для проекта
        link1 = Link(
            original_url="https://example.com/1",
            short_code=f"test123_{uuid4().hex[:8]}",
            owner_id=user.id,
            project=project,
        )

        link2 = Link(
            original_url="https://example.com/2",
            short_code=f"test456_{uuid4().hex[:8]}",
            owner_id=user.id,
            project=project,
        )

        db_session.add_all([project, link1, link2])
        await db_session.commit()

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
        from src.models.user import User
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select, text

        # Создаем проект
        project = Project(
            name="Проект с участниками", description="Описание проекта с участниками"
        )

        # Создаем пользователей с уникальными email
        user1 = User(
            email=f"user1_{uuid4().hex}@example.com",
            hashed_password="somehashedpassword1",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )

        user2 = User(
            email=f"user2_{uuid4().hex}@example.com",
            hashed_password="somehashedpassword2",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )

        # Добавляем пользователей в сессию
        db_session.add_all([project, user1, user2])
        await db_session.commit()

        # Создаем соединение между проектом и пользователями через промежуточную таблицу
        stmt = text("""
        INSERT INTO project_members (project_id, user_id, is_admin) 
        VALUES (:project_id, :user_id, false)
        """)
        await db_session.execute(stmt, {"project_id": project.id, "user_id": user1.id})
        await db_session.execute(stmt, {"project_id": project.id, "user_id": user2.id})
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
