import asyncio
import uuid
from typing import Dict, Any, AsyncIterator

from fastapi import Depends
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from auth.users import UserManager, get_user_manager
from core.database import get_async_session, engine
from models.user import User
from schemas.link import LinkCreate
from schemas.project import ProjectCreate
from services.project import ProjectService
from services.link import LinkService
from core.logger import logger


# Для совместимости с Python < 3.10
async def get_next(aiter: AsyncIterator):
    """Получение следующего элемента из асинхронного итератора."""
    return await aiter.__anext__()


async def create_demo_data() -> bool:
    """Создает демонстрационные данные: публичный проект, пользователя и два его проекта.
        === ДЕМОНСТРАЦИОННЫЕ ДАННЫЕ СОЗДАНЫ ===
        Пользователи:
        - admin@example.com / password123
        - user1@example.com / password123
        - user2@example.com / password123
        Проекты:
        - Public (ID: 1)
        - Личный проект user1 (ID: 2)
        - Рабочий проект user1 (ID: 3)
        - Рабочий проект user2 (ID: 4)
        Ссылки:
        - https://example.com/link1
        - https://example.com/link2
        - https://example.com/link3
        - https://example.com/link4
        - https://example.com/link5
        - https://example.com/link6

    Returns:
        True, если данные успешно созданы, иначе False
    """
    # Получаем сессию через стандартный метод
    session_generator = get_async_session()
    session = await get_next(session_generator)
    try:
        # Создаем экземпляр сервиса проектов
        project_service = ProjectService(session)
        link_service = LinkService(session)
        # Создаем публичный проект
        public_project = await project_service.create_public_project()

        # Создаем тестового пользователя
        password_helper = PasswordHelper()
        hashed_password = password_helper.hash("password123")

        # Создаем администратора
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        # Создаем обычного пользователя
        user1 = User(
            id=uuid.uuid4(),
            email="user1@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        session.add(user1)
        await session.commit()
        await session.refresh(user1)

        # Создаем еще одного пользователя
        user2 = User(
            id=uuid.uuid4(),
            email="user2@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        session.add(user2)
        await session.commit()
        await session.refresh(user2)

        # Создаем два проекта для пользователя user1
        project1 = await project_service.create_project(
            data=ProjectCreate(
                name="Личный проект user1",
                description="Проект для личных ссылок",
                default_link_lifetime_days=30,
            ),
            user_id=user1.id,
        )

        project2 = await project_service.create_project(
            data=ProjectCreate(
                name="Рабочий проект user1",
                description="Проект для рабочих ссылок",
                default_link_lifetime_days=90,
            ),
            user_id=user1.id,
        )

        # Создаем два проекта для пользователя user2
        project3 = await project_service.create_project(
            data=ProjectCreate(
                name="Рабочий проект user2",
                description="Проект для рабочих ссылок",
                default_link_lifetime_days=90,
            ),
            user_id=user2.id,
        )

        ############################################################
        #  Создаем ссылки
        ############################################################
        
        # Публичная, от анонимного пользователя
        link1 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link1",
                # short_code="link1",  # автогенерация короткого кода
                is_public=True,
            )
        )

        # Публичная, от пользователя user1 в проекте project1
        link2 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link2",
                short_code="link2",
                project_id=project1.id,
                is_public=True,
            ),
            user_id=user1.id,
            project_id=project1.id,
        )

        # Приватная, от пользователя user1 в проекте project1
        link3 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link3",
                # short_code="link3",  # автогенерация короткого кода
                project_id=project1.id,
                is_public=False,
            ),
            user_id=user1.id,
            project_id=project1.id,
        )

        # Приватная, от пользователя user1 в проекте project2
        link4 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link4",
                short_code="link4",
                project_id=project2.id,
                is_public=False,
            ),
            user_id=user1.id,
            project_id=project2.id,
        )

        # Публичная, от пользователя user2 в проекте project3
        link5 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link5",
                short_code="link5",
                project_id=project3.id,
                is_public=True,
            ),
            user_id=user2.id,
            project_id=project3.id,
        )

        # Приватная, от пользователя user2 в проекте project3
        link6 = await link_service.create_link(
            data=LinkCreate(
                original_url="https://example.com/link6",
                short_code="link6",
                project_id=project3.id,
                is_public=False,
            ),
            user_id=user2.id,
            project_id=project3.id,
        )
        link22 = await link_service.create_link(
            data=LinkCreate(
                original_url="http://team22.ykdns.net/",
                short_code="team22",
                is_public=True,
            ),
            user_id=user1.id,
            project_id=project1.id,
        )

        logger.debug(f"""\n
=============== ДЕМОНСТРАЦИОННЫЕ ДАННЫЕ СОЗДАНЫ ===============
Пользователи:
- admin@example.com / password123 / {admin_user.id}
- user1@example.com / password123 / {user1.id}
- user2@example.com / password123 / {user2.id}
Проекты:
- {public_project}
- {project1}
- {project2}
- {project3}
Ссылки:
- {link1}
- {link2}
- {link3}
- {link4}
- {link5}
- {link6}
- {link22}""")

        return True
    except Exception as e:
        logger.error(f"Ошибка при создании демонстрационных данных: {e}")
        raise e
        return False
    finally:
        # Завершаем транзакцию
        await session.commit()


if __name__ == "__main__":
    # Для запуска отдельно: python -m src.utils.demo_data
    asyncio.run(create_demo_data())
