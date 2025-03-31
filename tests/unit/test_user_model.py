# tests/unit/test_user_model.py

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError  # Импортируем IntegrityError

from src.models.user import User

# Убираем модульный маркер
# pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio  # Добавляем маркер к асинхронному тесту
async def test_user_creation(
    db_session: AsyncSession,
):  # Используем фикстуру сессии из conftest
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
    # assert user in db_session # Эта проверка может быть не всегда надежной

    # Проверка __repr__ (если он определен)
    # assert repr(user) == f"<User(id={user.id}, email='{user.email}')>"

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
    email = "unique@example.com"
    user1 = User(
        email=email,
        hashed_password="password1",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    user2 = User(
        email=email,  # Тот же email
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
