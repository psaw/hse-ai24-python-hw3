from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.project import Project, project_members
from models.link import Link
from models.user import User
from schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate


class ProjectService:
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса проектов.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def create_project(self, data: ProjectCreate, user_id: UUID) -> Project:
        """Создание нового проекта.

        Args:
            data: Данные нового проекта
            user_id: ID пользователя-создателя

        Returns:
            Созданный проект
        """
        new_project = Project(
            name=data.name,
            description=data.description,
            default_link_lifetime_days=data.default_link_lifetime_days,
            owner_id=user_id,
        )

        self.session.add(new_project)
        await self.session.commit()
        await self.session.refresh(new_project)

        # Создатель проекта автоматически становится его администратором
        stmt = project_members.insert().values(
            project_id=new_project.id,
            user_id=user_id,
            is_admin=True,
            joined_at=datetime.now(timezone.utc),
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Вместо обновления объекта со связями, просто возвращаем текущий объект
        # Это избежит попыток загрузить members асинхронно
        return new_project

    async def get_project_by_id(
        self, project_id: int, user_id: UUID, is_superuser: bool = False
    ) -> Project:
        """Получение проекта по ID с проверкой прав доступа.

        Args:
            project_id: ID проекта
            user_id: ID пользователя
            is_superuser: Флаг суперпользователя

        Returns:
            Проект, если он существует и пользователь имеет к нему доступ

        Raises:
            HTTPException: Если проект не найден или пользователь не имеет доступа
        """
        # Сначала проверяем права доступа, используя запрос с загрузкой связей
        query = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members))
        )
        result = await self.session.execute(query)
        project = result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Проект с ID {project_id} не найден",
            )

        # Суперпользователь имеет доступ ко всем проектам
        if is_superuser:
            self.session.expunge(project)
            return project

        # Проверка, является ли пользователь членом проекта или его владельцем
        is_member = any(member.id == user_id for member in project.members)
        if not is_member and project.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к этому проекту",
            )

        # Отключаем объект от сессии и возвращаем его
        self.session.expunge(project)
        return project

    async def get_projects_for_user(
        self, user_id: UUID, is_superuser: bool = False
    ) -> List[Project]:
        """Получение всех проектов пользователя.

        Args:
            user_id: ID пользователя
            is_superuser: Флаг суперпользователя

        Returns:
            Список проектов пользователя
        """
        if is_superuser:
            # Суперпользователь видит все проекты
            query = select(Project).order_by(Project.created_at.desc())
        else:
            # Обычный пользователь видит проекты, где он владелец или участник
            query = (
                select(Project)
                .outerjoin(project_members, Project.id == project_members.c.project_id)
                .where(
                    (Project.owner_id == user_id)
                    | (project_members.c.user_id == user_id)
                )
                .order_by(Project.created_at.desc())
            )

        result = await self.session.execute(query)
        projects = result.scalars().all()

        # Отключаем объекты от сессии, чтобы избежать попыток загрузки связанных данных
        for project in projects:
            self.session.expunge(project)

        return projects

    async def update_project(
        self, project_id: int, data: ProjectUpdate, user_id: UUID
    ) -> Project:
        """Обновление проекта с проверкой прав доступа.

        Args:
            project_id: ID проекта
            data: Данные для обновления
            user_id: ID пользователя

        Returns:
            Обновленный проект

        Raises:
            HTTPException: Если проект не найден, пользователь не имеет прав админа
        """
        # Проверяем, существует ли проект и является ли пользователь его администратором
        await self._check_project_admin(project_id, user_id)

        # Подготовка данных для обновления
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            # Если данных для обновления нет, просто возвращаем текущий проект
            return await self.get_project_by_id(project_id, user_id, False)

        # Обновление проекта
        stmt = update(Project).where(Project.id == project_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()

        # Получаем обновленный проект
        return await self.get_project_by_id(project_id, user_id, False)

    async def delete_project(self, project_id: int, user_id: UUID) -> Dict[str, Any]:
        """Удаление проекта.

        Args:
            project_id: ID проекта
            user_id: ID пользователя

        Returns:
            Сообщение об успешном удалении

        Raises:
            HTTPException: Если проект не найден, пользователь не имеет прав админа
        """
        # Проверяем, существует ли проект и является ли пользователь его владельцем
        project = await self._check_project_admin(project_id, user_id)

        # Проверка, является ли пользователь владельцем проекта
        if project.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только владелец проекта может удалить его",
            )

        # Проверка, не является ли проект публичным
        if project.name == "Public" and project.owner_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Публичный проект нельзя удалить",
            )

        # Удаление проекта (связанные записи удалятся автоматически благодаря CASCADE)
        stmt = delete(Project).where(Project.id == project_id)
        await self.session.execute(stmt)
        await self.session.commit()

        return {"message": f"Проект с ID {project_id} успешно удален"}

    async def add_project_member(
        self, project_id: int, data: ProjectMemberCreate, user_id: UUID
    ) -> Dict[str, Any]:
        """Добавление пользователя в проект.

        Args:
            project_id: ID проекта
            data: Данные о новом участнике (email и признак админа)
            user_id: ID пользователя, выполняющего операцию

        Returns:
            Сообщение об успешном добавлении

        Raises:
            HTTPException: Если проект не найден, пользователь не имеет прав админа,
                          или добавляемый пользователь не найден
        """
        # Проверяем, существует ли проект и является ли пользователь его администратором
        await self._check_project_admin(project_id, user_id)

        # Ищем пользователя по email
        query = select(User).where(User.email == data.email)
        result = await self.session.execute(query)
        new_member = result.scalars().first()

        if not new_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с email {data.email} не найден",
            )

        # Проверяем, не добавлен ли пользователь уже в проект
        query = select(project_members).where(
            project_members.c.project_id == project_id,
            project_members.c.user_id == new_member.id,
        )
        result = await self.session.execute(query)
        existing_member = result.first()

        if existing_member:
            # Если пользователь уже в проекте, просто обновляем его роль
            stmt = (
                update(project_members)
                .where(
                    project_members.c.project_id == project_id,
                    project_members.c.user_id == new_member.id,
                )
                .values(is_admin=data.is_admin)
            )
            await self.session.execute(stmt)
            await self.session.commit()

            return {"message": f"Роль пользователя с email {data.email} обновлена"}

        # Добавляем пользователя в проект
        stmt = project_members.insert().values(
            project_id=project_id,
            user_id=new_member.id,
            is_admin=data.is_admin,
            joined_at=datetime.now(timezone.utc),
        )
        await self.session.execute(stmt)
        await self.session.commit()

        return {
            "message": f"Пользователь с email {data.email} успешно добавлен в проект"
        }

    async def remove_project_member(
        self, project_id: int, member_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Удаление пользователя из проекта.

        Args:
            project_id: ID проекта
            member_id: ID удаляемого участника
            user_id: ID пользователя, выполняющего операцию

        Returns:
            Сообщение об успешном удалении

        Raises:
            HTTPException: Если проект не найден, пользователь не имеет прав админа,
                          нельзя удалить владельца проекта
        """
        # Проверяем, существует ли проект и является ли пользователь его администратором
        project = await self._check_project_admin(project_id, user_id)

        # Нельзя удалить владельца проекта
        if member_id == project.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить владельца проекта",
            )

        # Удаляем пользователя из проекта
        stmt = delete(project_members).where(
            project_members.c.project_id == project_id,
            project_members.c.user_id == member_id,
        )
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не является участником проекта",
            )

        await self.session.commit()

        return {"message": "Пользователь успешно удален из проекта"}

    async def create_public_project(self) -> Project:
        """Создание или получение публичного проекта.

        Returns:
            Публичный проект
        """
        # Проверяем, существует ли уже публичный проект
        query = select(Project).where(Project.name == "Public")
        result = await self.session.execute(query)
        public_project = result.scalars().first()

        # Если публичный проект существует, возвращаем его
        if public_project:
            # Изолируем из сессии, чтобы избежать загрузки связей
            self.session.expunge(public_project)
            return public_project

        # Получаем ID администратора системы (первого суперпользователя)
        from models.user import User
        from uuid import uuid4

        query = select(User).where(User.is_superuser == True).limit(1)
        result = await self.session.execute(query)
        admin = result.scalars().first()

        # Если администратора нет, создаем системного пользователя
        if not admin:
            # Для создания хеша пароля
            from fastapi_users.password import PasswordHelper

            password_helper = PasswordHelper()
            system_user_id = uuid4()
            new_admin = User(
                id=system_user_id,
                email="system@example.com",
                hashed_password=password_helper.hash(str(uuid4())),  # Случайный пароль
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            self.session.add(new_admin)
            await self.session.commit()
            admin_id = system_user_id
        else:
            admin_id = admin.id

        # Создаем публичный проект с ограничением на срок жизни ссылок
        public_project = Project(
            name="Public",
            description="Проект для публичных ссылок и незарегистрированных пользователей",
            default_link_lifetime_days=5,  # Максимальный срок жизни ссылок - 5 дней
            owner_id=admin_id,  # Назначаем владельцем администратора системы
        )

        self.session.add(public_project)
        await self.session.commit()

        # Получаем проект без связей и изолируем его из сессии
        query = select(Project).where(Project.id == public_project.id)
        result = await self.session.execute(query)
        public_project = result.scalars().first()
        self.session.expunge(public_project)

        return public_project

    async def _check_project_admin(self, project_id: int, user_id: UUID) -> Project:
        """Проверка, является ли пользователь администратором проекта.

        Args:
            project_id: ID проекта
            user_id: ID пользователя

        Returns:
            Проект, если пользователь является его администратором

        Raises:
            HTTPException: Если проект не найден или пользователь не является админом
        """
        query = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members))
        )
        result = await self.session.execute(query)
        project = result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Проект с ID {project_id} не найден",
            )

        # Для публичного проекта доступ запрещен
        if project.name == "Public":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Публичный проект нельзя редактировать",
            )

        # Проверка, является ли пользователь владельцем или администратором
        if project.owner_id == user_id:
            # Мы не делаем session.expunge здесь, чтобы сохранить данные связей
            # для последующих проверок в вызывающих методах
            return project

        # Проверяем, есть ли пользователь среди администраторов проекта
        query = select(project_members).where(
            project_members.c.project_id == project_id,
            project_members.c.user_id == user_id,
            project_members.c.is_admin == True,
        )
        result = await self.session.execute(query)
        is_admin = result.first() is not None

        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Для выполнения этой операции требуются права администратора проекта",
            )

        return project
