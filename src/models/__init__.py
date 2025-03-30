# flake8: noqa
# Import Base first to avoid circular dependencies if models depend on each other
from src.core.database import Base

# Import all models here so that Alembic can discover them
from .user import User
from .project import Project, project_members
from .link import Link
