import pytest
import pytest_asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from src.models.user import User
from src.models.project import Project
from src.models.link import Link
from tests.helpers import (
    create_test_user,
    create_test_project,
    create_test_link,
    create_multiple_test_links,
    create_test_project_with_members,
    add_user_to_project,
)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя."""
    return await create_test_user(
        db=db_session,
        is_superuser=False,
        email="test_user@example.com",
        password="test_password",
        is_active=True,
        is_verified=False,
    )


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя-администратора."""
    return await create_test_user(
        db=db_session,
        is_superuser=True,
        email="admin@example.com",
        password="admin_password",
        is_active=True,
        is_verified=True,
    )


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """Создает тестовый проект."""
    return await create_test_project(
        db=db_session,
        name="Test Project",
        description="Test project description",
        owner=test_user,
    )


@pytest_asyncio.fixture
async def test_project_with_members(
    db_session: AsyncSession, test_user: User, test_admin_user: User
) -> Project:
    """Создает тестовый проект с несколькими участниками."""
    return await create_test_project(
        db=db_session,
        name="Test Project with Members",
        description="Project with multiple members",
        owner=test_user,
        members=[test_user, test_admin_user],
    )


@pytest_asyncio.fixture
async def test_link(
    db_session: AsyncSession, test_user: User, test_project: Project
) -> Link:
    """Создает тестовую ссылку."""
    return await create_test_link(
        db=db_session,
        original_url="https://example.com/test",
        short_code=f"test_{uuid4().hex[:8]}",
        owner=test_user,
        project=test_project,
    )


@pytest_asyncio.fixture
async def test_links(
    db_session: AsyncSession, test_user: User, test_project: Project
) -> List[Link]:
    """Создает набор тестовых ссылок."""
    return await create_multiple_test_links(
        db=db_session,
        count=5,
        owner=test_user,
        project=test_project,
    )
