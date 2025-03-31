import sys
from pathlib import Path
from loguru import logger
from src.core.config import settings
from contextvars import ContextVar

# Контекстная переменная для Request ID
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Configure loguru
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss Z}</green> | "
    "<level>{level: <8}</level> | "
    "<yellow>RID:{extra[request_id]}</yellow> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


# Функция для добавления Request ID в запись лога
def request_id_patcher(record):
    record["extra"]["request_id"] = request_id_var.get()


# Применяем патчер к логгеру
logger = logger.patch(request_id_patcher)

logger.remove()

# Add console handler
logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level=settings.LOG_LEVEL,
    colorize=True,
)

# Add file handler
logger.add(
    LOG_DIR / "app.log",
    format=LOG_FORMAT,
    level="INFO",
    rotation="10 MB",
    retention="5 days",
    encoding="utf-8",
    serialize=True,
)
