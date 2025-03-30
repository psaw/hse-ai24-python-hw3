from datetime import datetime, timezone
from typing import Optional


def ensure_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """Убедиться, что дата содержит информацию о часовом поясе UTC."""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt