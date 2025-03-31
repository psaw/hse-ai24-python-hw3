from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    BigInteger,
    UUID,
)
from sqlalchemy.orm import relationship
from src.core.database import Base


def utcnow_with_tz():
    """Возвращает текущее время в UTC с явным указанием часового пояса."""
    return datetime.now(timezone.utc)


class Link(Base):
    __tablename__ = "links"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow_with_tz)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=False)  # UUID as string
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    clicks_count = Column(BigInteger, default=0)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    is_public = Column(Boolean, default=False)

    # Отношения
    owner = relationship("User", foreign_keys=[owner_id])
    project = relationship("Project", back_populates="links")

    def __repr__(self):
        return f"Link(id={self.id}, short={self.short_code}, orig={self.original_url}, prj={self.project_id}, exp={self.expires_at})"
