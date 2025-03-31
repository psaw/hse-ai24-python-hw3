import uuid
from uuid import uuid4
from typing import Optional, List, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import random
import string

from src.models.user import User
from src.models.project import Project
from src.models.link import Link


def generate_random_string(length: int = 8) -> str:
    """Генерирует случайную строку заданной длины."""
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))


async def create_test_user(
    db: AsyncSession,
    is_admin: bool = False,
    email: Optional[str] = None,
    password: str = "test_password",
    is_active: bool = True,
    is_superuser: bool = False,
    is_verified: bool = False,
    auto_flush: bool = True,
) -> User:
    """
    Создает тестового пользователя с уникальными данными.

    Args:
        db: Асинхронная сессия БД
        is_admin: Флаг администратора (связан с is_superuser для совместимости)
        email: Опциональный email (будет сделан уникальным автоматически)
        password: Пароль для пользователя
        is_active: Флаг активности пользователя
        is_superuser: Флаг суперпользователя
        is_verified: Флаг верификации пользователя
        auto_flush: Автоматически вызывать db.flush() после создания

    Returns:
        Созданный экземпляр User
    """
    # Создаем уникальный email, даже если предоставлен конкретный email
    unique_suffix = f"_{uuid.uuid4().hex[:8]}"

    if email:
        # Если email указан, сделаем его уникальным, добавив суффикс перед @
        at_position = email.find("@")
        if at_position != -1:
            email = f"{email[:at_position]}{unique_suffix}{email[at_position:]}"
        else:
            # Если @ нет, просто добавим суффикс
            email = f"{email}{unique_suffix}@example.com"
    else:
        # Если email не указан, генерируем полностью
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_string = generate_random_string(5)
        email = f"test_user_{timestamp}_{random_string}@example.com"

    # В моделе используется is_superuser вместо is_admin
    if is_admin:
        is_superuser = True

    # Создаем пользователя с правильными полями
    user = User(
        email=email,
        hashed_password=password,  # в модели поле называется hashed_password
        is_active=is_active,
        is_superuser=is_superuser,
        is_verified=is_verified,
    )

    # Добавляем в сессию
    db.add(user)

    # Если auto_flush=True, делаем flush чтобы получить id
    if auto_flush:
        try:
            await db.flush()
        except IntegrityError as e:
            await db.rollback()
            # Если проблема с уникальностью, пробуем еще раз с новым email
            if "duplicate key" in str(e) and "email" in str(e):
                print(f"Email {email} conflict, retrying with new random values")
                return await create_test_user(
                    db=db,
                    is_admin=is_admin,
                    # Не передаем email, чтобы сгенерировать полностью новый
                    password=password,
                    is_active=is_active,
                    is_superuser=is_superuser,
                    is_verified=is_verified,
                    auto_flush=auto_flush,
                )
            else:
                # Если какая-то другая ошибка, просто пробрасываем её выше
                raise

    return user


async def create_test_project(
    db: AsyncSession,
    name: Optional[str] = None,
    description: Optional[str] = None,
    owner: Optional[User] = None,
    members: Optional[List[User]] = None,
    auto_flush: bool = True,
) -> Project:
    """
    Создает тестовый проект. Если owner не указан, создает нового пользователя как владельца.

    Args:
        db: Асинхронная сессия БД
        name: Название проекта
        description: Описание проекта
        owner: Пользователь-владелец проекта
        members: Список пользователей-участников проекта
        auto_flush: Автоматически вызывать db.flush() после создания

    Returns:
        Созданный экземпляр Project
    """
    # Создаем владельца, если не указан
    if not owner:
        owner = await create_test_user(db, auto_flush=True)

    # Генерируем название проекта, если не указано
    if not name:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_string = generate_random_string(5)
        name = f"Test Project {timestamp} {random_string}"

    # Генерируем описание, если не указано
    if not description:
        description = f"Description for {name}"

    # Создаем проект
    project = Project(
        name=name,
        description=description,
        owner_id=owner.id,
    )

    # Добавляем участников
    if members:
        for member in members:
            project.members.append(member)

    # Добавляем в сессию
    db.add(project)

    # Если auto_flush=True, делаем flush чтобы получить id
    if auto_flush:
        await db.flush()

    return project


async def add_user_to_project(
    db: AsyncSession, project_id: int, user_id: uuid.UUID, is_admin: bool = False
) -> None:
    """
    Добавляет пользователя в проект через промежуточную таблицу.

    Args:
        db: Асинхронная сессия БД
        project_id: ID проекта
        user_id: ID пользователя
        is_admin: Флаг администратора проекта
    """
    stmt = text("""
    INSERT INTO project_members (project_id, user_id, is_admin) 
    VALUES (:project_id, :user_id, :is_admin)
    """)
    await db.execute(
        stmt, {"project_id": project_id, "user_id": user_id, "is_admin": is_admin}
    )
    await db.flush()


async def create_test_link(
    db: AsyncSession,
    original_url: Optional[str] = None,
    short_code: Optional[str] = None,
    owner: Optional[User] = None,
    project: Optional[Project] = None,
    auto_flush: bool = True,
) -> Link:
    """
    Создает тестовую ссылку. Если owner не указан, создает нового пользователя.

    Args:
        db: Асинхронная сессия БД
        original_url: URL ссылки
        short_code: Короткий код для ссылки
        owner: Пользователь-владелец ссылки
        project: Проект, к которому относится ссылка
        auto_flush: Автоматически вызывать db.flush() после создания

    Returns:
        Созданный экземпляр Link
    """
    # Создаем владельца, если не указан
    if not owner:
        owner = await create_test_user(db, auto_flush=True)

    # Создаем проект, если не указан
    if not project:
        project = await create_test_project(db, owner=owner, auto_flush=True)

    # Генерируем URL, если не указан
    if not original_url:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_string = generate_random_string(5)
        original_url = f"https://example.com/{timestamp}/{random_string}"

    # Генерируем короткий код, если не указан
    if not short_code:
        timestamp = datetime.now().strftime("%H%M%S")
        random_string = generate_random_string(5)
        short_code = f"test_{timestamp}_{random_string}"

    # Создаем ссылку
    link = Link(
        original_url=original_url,
        short_code=short_code,
        owner_id=owner.id,
        project_id=project.id,
    )

    # Добавляем в сессию
    db.add(link)

    # Если auto_flush=True, делаем flush чтобы получить id
    if auto_flush:
        await db.flush()

    return link


async def create_test_project_with_members(
    db: AsyncSession,
    owner: Optional[User] = None,
    members: Optional[List[User]] = None,
    project_name: Optional[str] = None,
) -> Project:
    """
    Создает тестовый проект с владельцем и участниками.

    Args:
        db: Асинхронная сессия БД
        owner: Пользователь-владелец проекта
        members: Список пользователей-участников проекта
        project_name: Название проекта

    Returns:
        Созданный экземпляр Project
    """
    # Создаем владельца, если не передан
    if owner is None:
        owner = await create_test_user(db)

    # Создаем проект
    project = await create_test_project(db, name=project_name, owner=owner)

    # Добавляем владельца как участника-администратора
    await add_user_to_project(db, project.id, owner.id, is_admin=True)

    # Добавляем других участников, если переданы
    if members:
        for member in members:
            await add_user_to_project(db, project.id, member.id)

    await db.flush()
    return project


async def create_multiple_test_links(
    db: AsyncSession,
    count: int = 5,
    owner: Optional[User] = None,
    project: Optional[Project] = None,
) -> List[Link]:
    """
    Создает несколько тестовых ссылок.

    Args:
        db: Асинхронная сессия БД
        count: Количество создаваемых ссылок
        owner: Пользователь-владелец ссылок
        project: Проект, к которому относятся ссылки

    Returns:
        Список созданных ссылок
    """
    if not owner:
        owner = await create_test_user(db, auto_flush=True)

    if not project:
        project = await create_test_project(db, owner=owner, auto_flush=True)

    links = []
    for i in range(count):
        link = await create_test_link(
            db=db,
            original_url=f"https://example.com/link_{i}",
            short_code=f"test_{i}_{generate_random_string(5)}",
            owner=owner,
            project=project,
            auto_flush=True,
        )
        links.append(link)

    return links


async def get_user_with_links(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Получает пользователя с загруженными ссылками.

    Args:
        db: Асинхронная сессия БД
        user_id: ID пользователя

    Returns:
        User или None, если пользователь не найден
    """
    query = select(User).where(User.id == user_id).options(selectinload(User.links))
    result = await db.execute(query)
    return result.scalars().first()


async def get_project_with_members(
    db: AsyncSession, project_id: int
) -> Optional[Project]:
    """
    Получает проект с загруженными участниками.

    Args:
        db: Асинхронная сессия БД
        project_id: ID проекта

    Returns:
        Project или None, если проект не найден
    """
    query = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.members))
    )
    result = await db.execute(query)
    return result.scalars().first()
