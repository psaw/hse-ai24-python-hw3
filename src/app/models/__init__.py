# from .base import Base
# from .user import User

# __all__ = ["Base", "User"]
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.link import Link
from app.models.relationships import setup_relationships

# Setup relationships between models
setup_relationships()

__all__ = ["User", "Project", "ProjectMember", "Link"]
