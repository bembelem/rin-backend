import asyncio
import logging

from app.core.metrics import collect_metrics
from app.monitoring.metrics_repository import MetricsRepository

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self, repository: MetricsRepository, interval: float = 1.0):
        self.repository = repository
        self.interval = interval
        self._task = None

    async def _loop(self):
        while True:
            try:
                schema = await collect_metrics()
                await self.repository.push(schema)
            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")
            await asyncio.sleep(self.interval)

    def start(self):
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        if self._task:
            self._task.cancel()