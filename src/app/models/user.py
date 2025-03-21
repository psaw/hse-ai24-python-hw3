from datetime import datetime
from typing import List
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship
from app.schemas.user import UserBase
from app.core.exceptions import UserNotFoundError


class User(UserBase, SQLModel, table=True):
    """User model"""

    __tablename__ = "users"

    id: int = Field(default=None, primary_key=True)
    email: EmailStr = Field(..., unique=True)
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def get_by_id(cls, session, user_id: int) -> "User":
        """Get user by ID or raise UserNotFoundError"""
        user = session.get(cls, user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    @classmethod
    def update(cls, session, user_id: int, **kwargs) -> "User":
        """Update user by ID"""
        user = cls.get_by_id(session, user_id)
        for key, value in kwargs.items():
            setattr(user, key, value)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
