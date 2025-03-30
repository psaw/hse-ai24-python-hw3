from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_link_lifetime_days: int = Field(default=30, ge=1, le=365)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    default_link_lifetime_days: Optional[int] = Field(None, ge=1, le=365)


class ProjectMemberBase(BaseModel):
    is_admin: bool = False


class ProjectMemberCreate(ProjectMemberBase):
    email: str


class ProjectMember(ProjectMemberBase):
    user_id: UUID
    joined_at: datetime

    class Config:
        from_attributes = True


# Схема для создания проекта без списка участников
class ProjectCreateResponse(ProjectBase):
    id: int
    created_at: datetime
    owner_id: Optional[UUID] = None  # None - для публичного проекта

    class Config:
        from_attributes = True


class Project(ProjectBase):
    id: int
    created_at: datetime
    owner_id: Optional[UUID] = None
    members: List[ProjectMember] = []

    class Config:
        from_attributes = True

    def __repr__(self):
        return f"Project(id={self.id}, name={self.name}, owner_id={self.owner_id})"


# Специальная схема для публичного проекта без членов
class PublicProject(ProjectBase):
    id: int
    created_at: datetime
    owner_id: Optional[UUID] = None

    class Config:
        from_attributes = True
