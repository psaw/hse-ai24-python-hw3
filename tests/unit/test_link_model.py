import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import uuid4

from src.models.link import Link, utcnow_with_tz
from src.models.project import Project
from src.models.user import User


@pytest.mark.asyncio
async def test_link_repr_method(db_session: AsyncSession):
    """
    Тестирует метод __repr__ модели Link.
    """
    # Создаем пользователя
    user = User(
        email=f"link_repr_test_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Создаем проект для ссылки
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем экземпляр Link с минимально необходимыми данными
    link = Link(
        original_url="https://example.com",
        short_code=f"test123_{uuid4().hex[:8]}",
        owner_id=user.id,
        project_id=project.id,
    )

    #########################################################
    # original_url = Column(String, nullable=False)
    # short_code = Column(String, unique=True, nullable=False, index=True)
    # created_at = Column(DateTime(timezone=True), default=utcnow_with_tz)
    # expires_at = Column(DateTime(timezone=True), nullable=True)
    # owner_id = Column(UUID, ForeignKey("users.id"), nullable=False)  # UUID as string
    # project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    # clicks_count = Column(BigInteger, default=0)
    # last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    # is_public = Column(Boolean, default=False)
    #########################################################

    # Проверяем, что __repr__ возвращает строку с нужными данными
    repr_result = repr(link)
    assert isinstance(repr_result, str)

    expected_repr = f"Link(id={link.id}, short={link.short_code}, orig={link.original_url}, prj={link.project_id}, exp={link.expires_at})"
    assert repr_result == expected_repr


@pytest.mark.asyncio
async def test_create_link(db_session: AsyncSession):
    """Тест создания ссылки."""
    # Создаем пользователя
    user = User(
        email=f"link_create_test_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Создаем проект для ссылки
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем ссылку
    link = Link(
        original_url="https://example.com",
        short_code=f"test123_{uuid4().hex[:8]}",
        owner_id=user.id,
        project_id=project.id,
        is_public=True,
    )

    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    # Проверяем, что ссылка создана и имеет корректные поля
    assert link.id is not None
    assert isinstance(link.id, int)
    assert link.original_url == "https://example.com"
    assert link.short_code.startswith("test123_")
    assert link.project_id == project.id
    assert link.owner_id == user.id
    assert link.is_public is True
    assert link.clicks_count == 0
    assert link.last_clicked_at is None
    assert link.created_at is not None
    assert isinstance(link.created_at, datetime)
    assert link.created_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_read_link(db_session: AsyncSession):
    """Тест чтения ссылки."""
    # Создаем пользователя
    user = User(
        email=f"link_read_test_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Создаем проект для ссылки
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем ссылку
    short_code = f"test123_{uuid4().hex[:8]}"
    link = Link(
        original_url="https://example.com",
        short_code=short_code,
        owner_id=user.id,
        project_id=project.id,
    )

    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    # Получаем ссылку из базы данных
    retrieved_link = await db_session.get(Link, link.id)

    # Проверяем, что ссылка получена корректно
    assert retrieved_link is not None
    assert retrieved_link.id == link.id
    assert retrieved_link.original_url == "https://example.com"
    assert retrieved_link.short_code == short_code
    assert retrieved_link.project_id == project.id
    assert retrieved_link.owner_id == user.id


@pytest.mark.asyncio
async def test_update_link(db_session: AsyncSession):
    """Тест обновления ссылки."""
    # Создаем пользователя
    user = User(
        email=f"link_update_test_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Создаем проект для ссылки
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем ссылку
    short_code = f"test123_{uuid4().hex[:8]}"
    link = Link(
        original_url="https://example.com",
        short_code=short_code,
        owner_id=user.id,
        project_id=project.id,
    )

    db_session.add(link)
    await db_session.commit()

    # Обновляем ссылку
    link.original_url = "https://updated-example.com"
    link.is_public = True

    await db_session.commit()
    await db_session.refresh(link)

    # Проверяем, что ссылка обновлена
    assert link.original_url == "https://updated-example.com"
    assert link.is_public is True


@pytest.mark.asyncio
async def test_delete_link(db_session: AsyncSession):
    """Тест удаления ссылки."""
    # Создаем пользователя
    user = User(
        email=f"link_delete_test_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Создаем проект для ссылки
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем ссылку
    short_code = f"test123_{uuid4().hex[:8]}"
    link = Link(
        original_url="https://example.com",
        short_code=short_code,
        owner_id=user.id,
        project_id=project.id,
    )

    db_session.add(link)
    await db_session.commit()

    # Сохраняем ID для проверки
    link_id = link.id

    # Удаляем ссылку
    await db_session.delete(link)
    await db_session.commit()

    # Проверяем, что ссылка удалена
    deleted_link = await db_session.get(Link, link_id)
    assert deleted_link is None


def test_utcnow_with_tz():
    """
    Тест проверяет, что функция utcnow_with_tz:
    1. Возвращает объект datetime
    2. Возвращает время с UTC timezone
    3. Возвращает текущее время (с погрешностью в несколько секунд)
    """
    # Получаем результат функции
    result = utcnow_with_tz()

    # Проверяем, что результат это datetime
    assert isinstance(result, datetime)

    # Проверяем, что timezone установлен в UTC
    assert result.tzinfo == timezone.utc

    # Проверяем, что время примерно текущее
    # (разница с текущим временем не более 2 секунд)
    now = datetime.now(timezone.utc)
    time_difference = abs((now - result).total_seconds())
    assert time_difference < 2
