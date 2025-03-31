import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from src.models.user import User
from src.models.project import Project
from src.models.link import Link
from tests.helpers import (
    create_test_user,
    create_test_project,
    create_test_link,
    get_user_with_links,
    get_project_with_members,
)
from tests.fixtures import (
    test_user,
    test_admin_user,
    test_project,
    test_project_with_members,
    test_links,
)


@pytest.mark.asyncio
class TestUserModel:
    """Тесты для модели User."""

    async def test_user_creation(self, db_session: AsyncSession):
        """Тестирует успешное создание экземпляра модели User."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "hashedpassword123",
            "is_active": True,
            "is_superuser": False,
            "is_verified": False,
        }

        # Создаем экземпляр User
        user = User(**user_data)

        # Проверяем атрибуты
        assert user.email == user_data["email"]
        assert user.hashed_password == user_data["hashed_password"]
        assert user.is_active == user_data["is_active"]
        assert user.is_superuser == user_data["is_superuser"]
        assert user.is_verified == user_data["is_verified"]

        # Проверим, что можно добавить в сессию (без коммита)
        db_session.add(user)

    async def test_user_email_unique_constraint(self, db_session: AsyncSession):
        """Тестирует ограничение уникальности email пользователя."""
        # Создаем базовый email, который будет сделан уникальным внутри create_test_user
        base_email = f"unique_test_{uuid4().hex}@example.com"

        # Используем вспомогательную функцию для создания первого пользователя
        user1 = await create_test_user(
            db=db_session, email=base_email, password="password1"
        )

        # Получаем actual_email, который был сохранен для пользователя
        # Он может отличаться от базового из-за добавления суффикса для уникальности
        stmt = select(User).where(User.id == user1.id)
        result = await db_session.execute(stmt)
        saved_user = result.scalar_one()
        actual_email = saved_user.email

        # Пытаемся создать второго пользователя с тем же email
        user2 = User(
            email=actual_email,  # Тот же email, что был сохранен
            hashed_password="password2",
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.flush()  # Должна быть ошибка из-за нарушения уникальности

    async def test_get_user_db(self, db_session):
        """Тестирует корректность работы асинхронного генератора get_user_db."""
        # Импортируем здесь, чтобы сделать тест более изолированным
        from src.models.user import get_user_db, SQLAlchemyUserDatabase

        # Получаем генератор
        user_db_generator = get_user_db(db_session)

        # Получаем значение из генератора
        user_db = await user_db_generator.__anext__()

        # Проверяем, что возвращенный объект правильного типа
        assert isinstance(user_db, SQLAlchemyUserDatabase)

        # Проверяем, что объект был создан с правильными параметрами
        assert user_db.session == db_session
        assert user_db.user_table == User

        # Проверка на исключения при полном исчерпании генератора
        with pytest.raises(StopAsyncIteration):
            await user_db_generator.__anext__()

    async def test_user_projects_relationship(self, db_session: AsyncSession):
        """Тестирует связь пользователя с проектами."""
        # Используем вспомогательные функции для создания тестовых данных
        user = await create_test_user(db=db_session)

        # Создаем проекты для пользователя
        project1 = await create_test_project(
            db=db_session,
            name="Проект 1",
            description="Описание проекта 1",
            owner=user,
        )

        project2 = await create_test_project(
            db=db_session,
            name="Проект 2",
            description="Описание проекта 2",
            owner=user,
            members=[user],  # Добавляем пользователя как участника
        )

        # Commit чтобы зафиксировать изменения
        await db_session.commit()

        # Загружаем проект с участниками
        project_with_members = await get_project_with_members(db_session, project2.id)

        # Загружаем пользователя с проектами
        stmt = (
            select(User).where(User.id == user.id).options(selectinload(User.projects))
        )
        result = await db_session.execute(stmt)
        loaded_user = result.scalar_one()

        # Проверяем связь
        assert len(loaded_user.projects) >= 1  # Как минимум один проект должен быть
        assert any(project.id == project2.id for project in loaded_user.projects)

        # Проверяем, что пользователь в списке участников проекта
        assert any(member.id == user.id for member in project_with_members.members)

    async def test_user_links_relationship(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Тестирует связь пользователя со ссылками."""
        # Создаем ссылки для тестового пользователя
        link1 = await create_test_link(
            db=db_session,
            original_url="https://example.com/1",
            short_code=f"test_link_1_{uuid4().hex[:8]}",
            owner=test_user,
            project=test_project,
        )

        link2 = await create_test_link(
            db=db_session,
            original_url="https://example.com/2",
            short_code=f"test_link_2_{uuid4().hex[:8]}",
            owner=test_user,
            project=test_project,
        )

        await db_session.commit()

        # Получаем пользователя с загруженными ссылками
        user_with_links = await get_user_with_links(db_session, test_user.id)

        # Проверяем связь
        assert user_with_links is not None
        assert len(user_with_links.links) >= 2
        assert any(
            link.original_url == "https://example.com/1"
            for link in user_with_links.links
        )
        assert any(
            link.original_url == "https://example.com/2"
            for link in user_with_links.links
        )

    async def test_user_with_existing_fixtures(
        self, db_session: AsyncSession, test_user: User, test_links: list
    ):
        """Тестирует работу с существующими фикстурами."""
        # Загружаем пользователя со ссылками
        user_with_links = await get_user_with_links(db_session, test_user.id)

        # Проверяем, что у пользователя есть ссылки
        assert user_with_links is not None
        assert len(user_with_links.links) >= len(test_links)

        # Проверяем, что все ссылки из фикстуры принадлежат пользователю
        user_link_ids = {link.id for link in user_with_links.links}
        for link in test_links:
            assert link.id in user_link_ids
