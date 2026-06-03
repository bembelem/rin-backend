import asyncio
import logging

from database.repositories import metrics_db
from config import settings

logger = logging.getLogger(__name__)


class RetentionWorker:
    """Периодически удаляет из БД снапшоты старше RETENTION_DAYS."""

    def __init__(self, days: int, interval: float):
        self.days = days
        self.interval = interval
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        while True:
            try:
                deleted = await metrics_db.delete_older_than(self.days)
                if deleted:
                    logger.info("retention: удалено %d снапшотов старше %d дн.", deleted, self.days)
            except Exception as e:
                logger.error("retention failed: %s", e)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()


retention_worker = RetentionWorker(
    days=settings.RETENTION_DAYS,
    interval=settings.RETENTION_INTERVAL,
)
