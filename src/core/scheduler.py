from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session
from src.services.link import LinkService
from src.core.logger import logger
from src.core.config import settings


class Scheduler:
    """Планировщик фоновых задач.

    Реализует паттерн Singleton для обеспечения единственного экземпляра планировщика
    во всем приложении. Использует APScheduler для управления асинхронными задачами.

    Основные задачи:
    - Автоматическая очистка истекших ссылок с настраиваемым интервалом
    - Логирование результатов выполнения задач
    - Обработка ошибок при выполнении задач

    Attributes:
        scheduler (AsyncIOScheduler): Экземпляр планировщика APScheduler
        _instance (Scheduler): Единственный экземпляр класса (Singleton)
        _initialized (bool): Флаг инициализации экземпляра

    Example:
        >>> scheduler = Scheduler()
        >>> scheduler.start()  # Запуск планировщика
        >>> scheduler.shutdown()  # Остановка планировщика
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.scheduler = AsyncIOScheduler()
            self._setup_jobs()
            self._initialized = True

    def _setup_jobs(self):
        """Настройка задач планировщика."""
        # Запускаем очистку истекших ссылок с интервалом из конфигурации
        self.scheduler.add_job(
            self._cleanup_expired_links,
            IntervalTrigger(minutes=settings.SCHEDULER_CLEANUP_INTERVAL),
            id="cleanup_expired_links",
            name="Cleanup expired links",
            replace_existing=True,
        )
        logger.info(
            f"Scheduler configured to run cleanup every {settings.SCHEDULER_CLEANUP_INTERVAL} minutes"
        )

    async def _cleanup_expired_links(self):
        """Очистка истекших ссылок."""
        try:
            # Получаем сессию БД
            async for session in get_async_session():
                # Создаем сервис для работы со ссылками
                link_service = LinkService(session)

                # Выполняем очистку
                logger.debug(" > > Entering cleanup_expired_links")
                deleted_count = await link_service.cleanup_expired_links()
                logger.debug(" > > Exiting cleanup_expired_links")

                logger.info(f"Cleaned up {deleted_count} expired links")
        except Exception as e:
            logger.exception(f"Error during cleanup of expired links: {e}")

    def start(self):
        """Запуск планировщика."""
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        """Остановка планировщика."""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
