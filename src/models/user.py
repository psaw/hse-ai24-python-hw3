from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from core.database import get_async_session, Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    # Отношения
    projects = relationship(
        "Project", secondary="project_members", back_populates="members"
    )


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
