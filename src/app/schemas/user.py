from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base schema for user"""

    email: EmailStr = Field(..., description="User email address")

    model_config = {
        "str_strip_whitespace": True,  # Удаляет пробелы
        "str_to_lower": True,  # Преобразует в нижний регистр
    }


class UserCreate(UserBase):
    """Schema for creating a new user"""

    pass


class UserUpdate(UserBase):
    """Schema for updating a user"""

    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    """Schema for user in database"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """Schema for user response"""

    pass
