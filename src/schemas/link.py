from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, field_validator
from core.logger import logger

from utils.utils import ensure_timezone


class LinkPublicBase(BaseModel):
    """Базовая схема с публичной информацией о ссылке."""

    original_url: HttpUrl
    short_code: Optional[str] = Field(None, min_length=3, max_length=15)
    expires_at: Optional[datetime] = Field(
        None,
        description="Время истечения ссылки",
    )



class LinkBase(LinkPublicBase):
    """Базовая схема для ссылки.

    Добавляет:
    - project_id: ID проекта
    - owner_id: ID владельца ссылки
    - created_at: Дата создания ссылки
    - is_public: Флаг публичности ссылки"""

    created_at: datetime
    project_id: Optional[int] = None
    owner_id: Optional[UUID] = None
    is_public: Optional[bool] = False


class Link(LinkBase):
    """Полная схема для ссылки.

    Добавляет:
    - id: ID ссылки
    - short_code: Код ссылки стал обязательным полем
    - created_at: Дата создания ссылки
    - owner_id: ID владельца ссылки
    - is_public: Флаг публичности ссылки"""

    id: int
    short_code: str
    is_public: bool
    clicks_count: int = 0
    last_clicked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LinkStats(LinkPublicBase):
    """Схема для статистики ссылки.

    Добавляет к публичной информации:
    - clicks_count: Количество кликов
    - last_clicked_at: Дата последнего клика"""

    clicks_count: int
    last_clicked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LinkCreate(LinkPublicBase):
    """Схема для создания ссылки."""

    project_id: Optional[int] = None
    is_public: Optional[bool] = False


class LinkUpdate(BaseModel):
    """Схема для обновления ссылки.

    Обновить у ссылки можно только эти три поля:
    - original_url: URL ссылки
    - expires_at: Время истечения ссылки
    - is_public: Флаг публичности ссылки

    Все поля необязательные, можно обновить только то, что нужно."""

    original_url: Optional[HttpUrl] = Field(None, description="URL ссылки")
    expires_at: Optional[datetime] = Field(None, description="Время истечения ссылки")
    is_public: Optional[bool] = Field(None, description="Флаг публичности ссылки")


class LinkResponse(LinkPublicBase):
    """Схема для ответа на запрос популярных ссылок.

    Добавляет:
    - clicks_count: Количество кликов (популярность)"""

    clicks_count: Optional[int] = 0


class LinkCache(Link):
    """Схема для кэширования ссылки.

    Меняет типы полей на строковые, чтобы можно было сохранить в Redis."""

    expires_at: str  # ISO формат строки
    owner_id: str  # UUID в виде строки
    created_at: str  # ISO формат строки
    last_clicked_at: Optional[str] = None  # ISO формат строки
    clicks_count: int = 0

    @classmethod
    def from_link(cls, link: Link) -> "LinkCache":
        """Создание этой схемы из Link."""
        return cls(
            id=link.id,
            original_url=link.original_url,
            short_code=link.short_code,
            owner_id=str(link.owner_id),
            project_id=link.project_id,
            is_public=link.is_public,
            created_at=link.created_at.replace(tzinfo=timezone.utc).isoformat(),
            expires_at=link.expires_at.replace(tzinfo=timezone.utc).isoformat(),
            last_clicked_at=link.last_clicked_at.replace(
                tzinfo=timezone.utc
            ).isoformat()
            if link.last_clicked_at
            else None,
            clicks_count=link.clicks_count,
        )

    def to_link(self) -> Link:
        """Восстановление из этой схемы в Link."""
        return Link(
            id=self.id,
            original_url=self.original_url,
            short_code=self.short_code,
            project_id=self.project_id,
            owner_id=UUID(self.owner_id) if self.owner_id else None,
            is_public=self.is_public,
            expires_at=datetime.fromisoformat(self.expires_at).replace(
                tzinfo=timezone.utc
            )
            if self.expires_at
            else None,
            created_at=datetime.fromisoformat(self.created_at).replace(
                tzinfo=timezone.utc
            ),
            last_clicked_at=datetime.fromisoformat(self.last_clicked_at).replace(
                tzinfo=timezone.utc
            )
            if self.last_clicked_at
            else None,
            clicks_count=self.clicks_count,
        )


class LinkCacheStatic(Link):
    """Схема для кэширования только постоянных данных ссылки без статистики.

    Заменяет типы полей на строковые, чтобы можно было сохранить в Redis."""

    id: int
    original_url: str
    short_code: str
    owner_id: str  # UUID в виде строки
    project_id: int
    is_public: bool = False
    created_at: str  # ISO формат строки
    expires_at: str  # ISO формат строки

    @classmethod
    def from_link(cls, link: Link) -> "LinkCacheStatic":
        """Создание схемы кэша из модели Link."""
        link_static = cls(
            id=link.id,
            original_url=link.original_url,
            short_code=link.short_code,
            owner_id=str(link.owner_id),
            project_id=link.project_id,
            is_public=link.is_public,
            created_at=ensure_timezone(link.created_at).isoformat(),
            expires_at=ensure_timezone(link.expires_at).isoformat(),
        )
        logger.debug(f" > > LinkCacheStatic.from_link: {link_static}")
        return link_static

    def to_link(
        self, clicks_count: int = 0, last_clicked_at: Optional[datetime] = None
    ) -> Link:
        """Преобразование схемы кэша обратно в модель Link с добавлением статистики."""
        return Link(
            id=self.id,
            original_url=self.original_url,
            short_code=self.short_code,
            owner_id=UUID(self.owner_id),
            project_id=self.project_id,
            is_public=self.is_public,
            expires_at=datetime.fromisoformat(self.expires_at).replace(
                tzinfo=timezone.utc
            ),
            created_at=datetime.fromisoformat(self.created_at).replace(
                tzinfo=timezone.utc
            ),
            clicks_count=clicks_count,
            last_clicked_at=last_clicked_at,
        )


class LinkClickStats(BaseModel):
    """Схема для хранения статистики кликов."""

    clicks_count: int = 0
    last_clicked_at: Optional[str] = None  # ISO формат строки

    @classmethod
    def from_link(cls, link: Link) -> "LinkClickStats":
        """Создание схемы статистики из модели Link."""
        return cls(
            clicks_count=link.clicks_count,
            last_clicked_at=link.last_clicked_at.replace(
                tzinfo=timezone.utc
            ).isoformat()
            if link.last_clicked_at
            else None,
        )

    def to_datetime(self) -> Optional[datetime]:
        """Преобразование строки last_clicked_at в datetime."""
        if self.last_clicked_at:
            return datetime.fromisoformat(self.last_clicked_at).replace(
                tzinfo=timezone.utc
            )
        return None
