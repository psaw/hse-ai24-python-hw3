import sys
import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient  # Используем AsyncClient т.к. приложение асинхронное
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from pydantic_settings import SettingsConfigDict

# Добавляем корневую директорию проекта (где находится папка src) в PYTHONPATH
# Это позволит pytest находить модули из src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added project root to sys.path: {project_root}")

from src.models.user import User
from src.models.project import Project
from src.models.link import Link

# Импортируем наши фикстуры для тестовых данных
from tests.fixtures import (
    test_user,
    test_admin_user,
    test_project,
    test_project_with_members,
    test_link,
    test_links,
)


# Убедитесь, что модели импортируются только один раз
@pytest.fixture(scope="session")
def models():
    """Возвращает словарь с моделями для использования в тестах."""
    return {"User": User, "Link": Link, "Project": Project}


@pytest.fixture(scope="session")
def event_loop():
    """
    Создает цикл событий для всей тестовой сессии.
    Переопределяет встроенную фикстуру pytest_asyncio, которая создает отдельный цикл событий для каждого теста.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Явно закрываем все незавершенные задачи
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()

    # Запускаем цикл, чтобы задачи отменились
    if pending and not loop.is_closed():
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

    # Закрываем цикл
    if not loop.is_closed():
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Настраивает Pydantic Settings на использование .env.test для всей сессии.
    Загружает переменные окружения из .env.test ДО импорта settings.
    """
    # Самый простой способ, если Pydantic Settings > 2.0:
    # Загрузить тестовые переменные и затем импортировать settings
    from dotenv import load_dotenv

    print("Loading .env.test for Pydantic Settings...")
    loaded = load_dotenv(dotenv_path=".env.test", override=True)
    if not loaded:
        print("Warning: .env.test not found or empty.")
        pytest.fail(".env.test not found, cannot run tests.")

    # Теперь импортируем settings ПОСЛЕ загрузки .env.test
    # Это требует, чтобы config.py не импортировался где-либо еще до этой фикстуры
    from src.core.config import settings

    # Проверка ключевой переменной (теперь из settings)
    if not settings.database_dsn_async:
        pytest.fail("settings.DATABASE_URL не найдена после загрузки .env.test")
    db_url = str(settings.database_dsn_async)
    print(f"Test DATABASE_URL loaded via Pydantic: {db_url[: db_url.find('@')]}...")


# --- Фикстуры для управления тестовой базой данных ---


@pytest_asyncio.fixture(scope="session")
async def test_async_engine(event_loop) -> AsyncGenerator[AsyncEngine, None]:
    """
    Создает и предоставляет асинхронный движок SQLAlchemy для тестовой БД.
    Использует NullPool для предотвращения зависания соединений в тестах.
    Использует DATABASE_URL из настроек Pydantic.
    """
    # Импортируем здесь, чтобы убедиться, что .env.test загружен
    from src.core.config import settings

    # Используем правильное свойство для асинхронного DSN
    test_db_url = settings.database_dsn_async
    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=settings.DB_ECHO)
    print("Test engine created.")
    yield engine
    print("Disposing test engine...")
    await engine.dispose()
    print("Test engine disposed.")


@pytest.fixture(scope="session", autouse=True)
def apply_migrations_to_test_db(test_async_engine: AsyncEngine, event_loop):
    """
    Применяет миграции Alembic к тестовой БД перед началом тестовой сессии.
    Запускается автоматически благодаря autouse=True.
    """
    print("Applying migrations...")
    alembic_cfg = Config("alembic.ini")
    # Alembic должен использовать DATABASE_URL из окружения,
    # которое было установлено через load_dotenv в `set_test_environment`.
    # Убедитесь, что ваш alembic/env.py читает DATABASE_URL из os.environ.
    command.upgrade(alembic_cfg, "head")
    print("Migrations applied.")
    yield
    # Опционально: откат миграций после тестов или очистка таблиц
    # print("Downgrading migrations...")
    # command.downgrade(alembic_cfg, "base")
    # print("Migrations downgraded.")


@pytest_asyncio.fixture(scope="session")
async def TestDBSessionFactory(
    test_async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """
    Создает фабрику сессий, привязанную к тестовому движку БД.
    Область видимости "session", так как фабрика не меняется между тестами.
    """
    return async_sessionmaker(
        bind=test_async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def db_session(
    TestDBSessionFactory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Предоставляет транзакционную сессию БД для каждого теста.
    Создает новую сессию и транзакцию для каждого теста.
    После теста всегда выполняет rollback для изоляции тестов.
    """
    # Создаем новую сессию для каждого теста
    async with TestDBSessionFactory() as session:
        # Начинаем транзакцию
        await session.begin()
        try:
            yield session
        finally:
            # Всегда откатываем транзакцию, даже если тест завершился с ошибкой
            await session.rollback()
            # Закрываем сессию
            await session.close()


# --- Фикстуры для тестового клиента FastAPI ---


@pytest.fixture
def test_app(TestDBSessionFactory: async_sessionmaker[AsyncSession]) -> FastAPI:
    """
    Создает экземпляр FastAPI приложения для теста, переопределяя зависимость get_async_session,
    чтобы использовать тестовую фабрику сессий.
    Область видимости "function" для изоляции переопределений между тестами.
    """
    # Импортируем здесь, чтобы избежать загрузки конфига до фикстуры окружения
    from src.main import app as fastapi_app
    from src.core.database import get_async_session
    from src.core.config import settings  # Импортируем settings

    # Функция для переопределения зависимости
    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        # Импорт get_async_session здесь больше не нужен
        async with TestDBSessionFactory() as session:
            yield session
            # Явный rollback здесь не нужен, т.к. db_session его уже делает

    # Применяем переопределение
    fastapi_app.dependency_overrides[get_async_session] = override_get_async_session
    print("Dependency get_async_session overridden for test.")

    yield fastapi_app  # Предоставляем приложение тесту

    # Убираем переопределение после завершения теста
    del fastapi_app.dependency_overrides[get_async_session]
    print("Dependency override cleaned up.")


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Предоставляет асинхронный HTTP клиент (httpx) для взаимодействия с тестовым приложением FastAPI.
    """
    async with AsyncClient(app=test_app, base_url="http://testserver") as async_client:
        print("Async test client created.")
        yield async_client
