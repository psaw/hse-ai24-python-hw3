from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.config import settings
from app.schemas.link import LinkBase
from app.core.exceptions import LinkNotFoundError


class Link(LinkBase, SQLModel, table=True):
    """Link model"""

    __tablename__ = "links"

    id: int = Field(default=None, primary_key=True)
    original_url: str = Field(..., description="Original URL")
    short_code: str = Field(..., description="Short code for the link")
    custom_alias: Optional[str] = Field(None, description="Custom alias for the link")
    is_public: bool = Field(default=False, description="Whether the link is public")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="Link expiration date")
    last_used_at: Optional[datetime] = Field(
        None, description="Last time the link was used"
    )
    visits_count: int = Field(
        default=0, description="Number of times the link was visited"
    )
    project_id: Optional[int] = Field(None, foreign_key="projects.id")

    def __init__(self, **data):
        super().__init__(**data)
        # Set expiration date for public links
        if self.is_public and self.expires_at is None:
            self.expires_at = datetime.now() + timedelta(
                days=settings.PUBLIC_PROJECT_LINK_EXPIRY_DAYS
            )

    @classmethod
    def get_by_id(cls, session, link_id: int) -> "Link":
        """Get link by ID or raise LinkNotFoundError"""
        link = session.get(cls, link_id)
        if link is None:
            raise LinkNotFoundError(link_id)
        return link

    @classmethod
    def get_by_short_code(cls, session, short_code: str) -> "Link":
        """Get link by short code or raise LinkNotFoundError"""
        link = session.query(cls).filter(cls.short_code == short_code).first()
        if link is None:
            raise LinkNotFoundError(short_code)
        return link
