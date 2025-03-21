from sqlmodel import Relationship

from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.link import Link


def setup_relationships():
    """Setup relationships between models"""
    # User relationships
    User.projects = Relationship(back_populates="owner")
    User.project_memberships = Relationship(back_populates="user")

    # Project relationships
    Project.owner = Relationship(back_populates="projects")
    Project.members = Relationship(back_populates="project")
    Project.links = Relationship(back_populates="project")

    # ProjectMember relationships
    ProjectMember.user = Relationship(back_populates="project_memberships")
    ProjectMember.project = Relationship(back_populates="members")

    # Link relationships
    Link.project = Relationship(back_populates="links")
