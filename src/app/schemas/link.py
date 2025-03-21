from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator, HttpUrl


class LinkBase(BaseModel):
    """Base link schema"""

    original_url: HttpUrl = Field(..., description="Original URL")
    short_code: str = Field(..., description="Short code for the link")
    custom_alias: Optional[str] = Field(None, description="Custom alias for the link")
    is_public: bool = Field(default=False, description="Whether the link is public")
    expires_at: Optional[datetime] = Field(None, description="Link expiration date")
    project_id: Optional[int] = Field(None, description="Project ID")

    @validator("short_code")
    def validate_short_code(cls, v):
        if not v:
            raise ValueError("Short code cannot be empty")
        if len(v) > 10:
            raise ValueError("Short code cannot be longer than 10 characters")
        return v

    @validator("custom_alias")
    def validate_custom_alias(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Custom alias cannot be longer than 50 characters")
        return v

    @validator("expires_at")
    def validate_expires_at(cls, v):
        if v is not None and v < datetime.now():
            raise ValueError("Expiration date cannot be in the past")
        return v

    @validator("project_id")
    def validate_project_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Project ID must be positive")
        return v
