from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class TestTable(Base):
    """Test table model"""
    __tablename__ = "test_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) 