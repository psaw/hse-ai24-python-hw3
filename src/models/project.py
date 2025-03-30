from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Table,
    UUID,
)
from sqlalchemy.orm import relationship
from src.core.database import Base


def utcnow_with_tz():
    """Возвращает текущее время в UTC с явным указанием часового пояса."""
    return datetime.now(timezone.utc)


# Таблица для связи проектов и пользователей с ролями
project_members = Table(
    "project_members",
    Base.metadata,
    Column(
        "project_id",
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("user_id", UUID, ForeignKey("users.id"), primary_key=True),  # UUID as string
    Column("is_admin", Boolean, default=False),
    Column("joined_at", DateTime(timezone=True), default=utcnow_with_tz),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    default_link_lifetime_days = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime(timezone=True), default=utcnow_with_tz)
    owner_id = Column(
        UUID, ForeignKey("users.id"), nullable=True
    )  # UUID as string, может быть NULL для публичного проекта

    # Отношения
    members = relationship("User", secondary=project_members, back_populates="projects")
    links = relationship("Link", back_populates="project")
    owner = relationship("User", foreign_keys=[owner_id])

    def __repr__(self):
        return f"Project(id={self.id}, name={self.name}, owner_id={self.owner_id})"
