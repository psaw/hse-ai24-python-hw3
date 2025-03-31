import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from uuid import uuid4

from src.models.user import User
from src.models.project import Project
from src.models.link import Link


@pytest.mark.asyncio  # Добавляем маркер к асинхронному тесту
async def test_user_creation(
    db_session: AsyncSession,
):  # Используем фикстуру сессии из conftest.py
    """
    Тестирует успешное создание экземпляра модели User.
    """
    user_data = {
        "email": "test@example.com",
        "hashed_password": "hashedpassword123",
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
        # id генерируется автоматически UUID
    }

    # Создаем экземпляр User
    # В реальном тесте мы бы не создавали его напрямую,
    # а использовали бы, например, UserManager или CRUD операции,
    # но для теста самой модели это допустимо.
    user = User(**user_data)

    # Проверяем атрибуты
    assert user.email == user_data["email"]
    assert user.hashed_password == user_data["hashed_password"]
    assert user.is_active == user_data["is_active"]
    assert user.is_superuser == user_data["is_superuser"]
    assert user.is_verified == user_data["is_verified"]

    # Убираем проверку id, т.к. он генерируется при flush/commit
    # assert isinstance(user.id, uuid.UUID) # Проверяем, что id - это UUID

    # Проверим, что можно добавить в сессию (без коммита)
    db_session.add(user)
    # Не делаем flush или commit, так как сессия откатится после теста

    print(f"\nUser created in test: {user}")


# Убираем asyncio маркер и db_session
# @pytest.mark.asyncio
# async def test_user_default_values(
#     db_session: AsyncSession,
# ):
def test_user_default_values():
    """
    Тестирует значения по умолчанию для столбцов User,
    проверяя определение модели, а не экземпляр.
    Это модульный тест.
    """
    # Проверяем значения по умолчанию, указанные в определении столбцов SQLAlchemy
    # Это не требует создания экземпляра или сессии БД
    assert User.__table__.columns.is_active.default.arg is True
    assert User.__table__.columns.is_superuser.default.arg is False
    assert User.__table__.columns.is_verified.default.arg is False

    # Проверку id убираем, т.к. она зависит от экземпляра/БД
    # assert isinstance(user.id, uuid.UUID)


@pytest.mark.asyncio  # Добавляем маркер к асинхронному тесту
async def test_user_email_unique_constraint(db_session: AsyncSession):
    """
    Тестирует ограничение уникальности email пользователя.
    """
    test_email = f"unique_test_{uuid4().hex}@example.com"
    user1 = User(
        email=test_email,
        hashed_password="password1",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    user2 = User(
        email=test_email,  # Тот же email
        hashed_password="password2",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )

    db_session.add(user1)
    await db_session.flush()  # Сохраняем первого пользователя, чтобы id сгенерировался

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await (
            db_session.flush()
        )  # Попытка сохранить второго пользователя с тем же email должна вызвать ошибку


@pytest.mark.asyncio
async def test_get_user_db(db_session):
    """
    Тестирует корректность работы асинхронного генератора get_user_db.
    """
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


@pytest.mark.asyncio
async def test_user_projects_relationship(db_session: AsyncSession):
    """
    Тестирует связь пользователя с проектами.
    """
    # Создаем пользователя
    user = User(
        email=f"test_project_rel_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()

    # Создаем проекты
    project1 = Project(
        name="Проект 1",
        description="Описание проекта 1",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    project2 = Project(
        name="Проект 2",
        description="Описание проекта 2",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )

    db_session.add_all([project1, project2])
    await db_session.commit()

    # Создаем соединение между пользователем и проектами через промежуточную таблицу
    stmt = text("""
    INSERT INTO project_members (project_id, user_id, is_admin) 
    VALUES (:project_id, :user_id, false)
    """)
    await db_session.execute(stmt, {"project_id": project1.id, "user_id": user.id})
    await db_session.execute(stmt, {"project_id": project2.id, "user_id": user.id})
    await db_session.commit()

    # Загружаем пользователя с проектами
    stmt = select(User).where(User.id == user.id).options(selectinload(User.projects))
    result = await db_session.execute(stmt)
    user = result.scalar_one()

    # Загружаем проекты с информацией о владельце
    stmt = select(Project).where(Project.id.in_([project1.id, project2.id]))
    result = await db_session.execute(stmt)
    projects = result.scalars().all()

    # Проверяем связь
    assert len(user.projects) == 2
    assert any(project.id == project1.id for project in user.projects)
    assert any(project.id == project2.id for project in user.projects)

    # Проверяем поле owner_id
    for project in projects:
        assert project.owner_id == user.id


@pytest.mark.asyncio
async def test_user_links_relationship(db_session: AsyncSession):
    """
    Тестирует связь пользователя со ссылками.
    """
    from sqlalchemy import select

    # Создаем пользователя
    user = User(
        email=f"test_link_rel_{uuid4().hex}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()

    # Создаем проект
    project = Project(
        name="Тестовый проект",
        description="Описание тестового проекта",
        default_link_lifetime_days=30,
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.commit()

    # Создаем ссылки с уникальными short_code
    link1 = Link(
        original_url="https://example.com/1",
        short_code=f"test123_{uuid4().hex[:8]}",
        owner_id=user.id,
        project_id=project.id,
    )
    link2 = Link(
        original_url="https://example.com/2",
        short_code=f"test456_{uuid4().hex[:8]}",
        owner_id=user.id,
        project_id=project.id,
    )

    db_session.add_all([link1, link2])
    await db_session.commit()

    # Получаем ссылки напрямую из базы данных
    stmt = select(Link).where(Link.owner_id == user.id)
    result = await db_session.execute(stmt)
    links = result.scalars().all()

    # Проверяем связь
    assert len(links) == 2
    for link in links:
        assert link.owner_id == user.id
        assert link.project_id == project.id
