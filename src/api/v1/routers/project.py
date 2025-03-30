from uuid import UUID
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.users import current_active_user
from core.database import get_async_session
from models.user import User
from schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectMemberCreate,
    PublicProject,
    ProjectCreateResponse,
)
from services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


async def get_project_service(session: AsyncSession = Depends(get_async_session)):
    """Получение сервиса для работы с проектами."""
    return ProjectService(session)


@router.post(
    "", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Создание нового проекта.

    Текущий пользователь автоматически становится владельцем и администратором проекта.
    """
    return await project_service.create_project(data, user.id)


@router.get("", response_model=List[ProjectCreateResponse])
async def get_user_projects(
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Получение всех проектов пользователя.

    Обычный пользователь видит проекты, где он является владельцем или участником.
    Администратор (is_superuser) видит все проекты системы.
    """
    projects = await project_service.get_projects_for_user(user.id, user.is_superuser)
    return projects


@router.get("/public", response_model=PublicProject)
async def get_public_project(
    project_service: ProjectService = Depends(get_project_service),
):
    """Получение публичного проекта.

    Не требует аутентификации.
    """
    return await project_service.create_public_project()


@router.get("/{project_id}", response_model=ProjectCreateResponse)
async def get_project(
    project_id: int,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Получение проекта по ID.

    Обычный пользователь может получить только свои проекты и те, где он участник.
    Администратор (is_superuser) может получить любой проект.
    """
    return await project_service.get_project_by_id(
        project_id, user.id, user.is_superuser
    )


@router.put("/{project_id}", response_model=ProjectCreateResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Обновление проекта.

    Только администратор проекта может обновлять его данные.
    """
    return await project_service.update_project(project_id, data, user.id)


@router.delete("/{project_id}", response_model=Dict[str, Any])
async def delete_project(
    project_id: int,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Удаление проекта.

    Только владелец проекта может удалить его.
    """
    return await project_service.delete_project(project_id, user.id)


@router.post("/{project_id}/members", response_model=Dict[str, Any])
async def add_project_member(
    project_id: int,
    data: ProjectMemberCreate,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Добавление пользователя в проект.

    Только администратор проекта может добавлять новых участников.
    """
    return await project_service.add_project_member(project_id, data, user.id)


@router.delete("/{project_id}/members/{member_id}", response_model=Dict[str, Any])
async def remove_project_member(
    project_id: int,
    member_id: UUID,
    user: User = Depends(current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Удаление пользователя из проекта.

    Только администратор проекта может удалять участников.
    Владельца проекта удалить нельзя.
    """
    return await project_service.remove_project_member(project_id, member_id, user.id)
