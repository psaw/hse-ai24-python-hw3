from datetime import datetime
from sqlmodel import Field, SQLModel

from app.core.exceptions import ProjectNotFoundError
from app.schemas.project import ProjectBase
from app.schemas.project_member import ProjectMemberBase


class Project(ProjectBase, SQLModel, table=True):
    """Project model"""

    __tablename__ = "projects"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(..., description="Project name")
    default_lifetime_days: int = Field(
        ..., description="Default lifetime for links in days"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    owner_id: int = Field(foreign_key="users.id")

    @classmethod
    def get_by_id(cls, session, project_id: int) -> "Project":
        """Get project by ID or raise ProjectNotFoundError"""
        project = session.get(cls, project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project


class ProjectMember(ProjectMemberBase, SQLModel, table=True):
    """Project member model"""

    __tablename__ = "project_members"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    project_id: int = Field(foreign_key="projects.id")
    is_admin: bool = Field(default=False, description="Whether the member is an admin")
    joined_at: datetime = Field(default_factory=datetime.now)
