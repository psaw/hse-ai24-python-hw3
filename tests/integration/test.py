from sqlmodel import Field, SQLModel


class TestTable(SQLModel, table=True):
    __tablename__ = "test_table"

    id: int = Field(default=None, primary_key=True)
    name: str
