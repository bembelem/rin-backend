import asyncio
import logging
from collections import deque
from typing import TypeAlias

from app.api.websocket import manager
from app.schemas.schemas import ServerMetricsSchema, ServerInfo
from database.repositories import metrics_db
from config import settings

logger = logging.getLogger(__name__)

ServerName: TypeAlias = str
MetricsHistory: TypeAlias = deque[ServerMetricsSchema]

class MetricsRepository:
    def __init__(self, window: int = 60):
        self._data: dict[ServerName, MetricsHistory] = {}
        self._lock = asyncio.Lock()
        self._window = window

    async def push(self, metrics: ServerMetricsSchema):
        # 1. горячий кэш (realtime)
        async with self._lock:
            if metrics.server_name not in self._data:
                self._data[metrics.server_name] = deque(maxlen=self._window)
            self._data[metrics.server_name].append(metrics)
        # 2. realtime-вещание подключённым WS-клиентам
        await manager.broadcast(metrics.model_dump(mode="json", by_alias=True))
        # 3. персистентность в БД (best-effort — сбой БД не должен ронять стрим)
        try:
            await metrics_db.save_snapshot(metrics)
        except Exception as e:
            logger.error(f"DB persist failed: {e}")

    async def get_server_latest(self, server: str) -> ServerMetricsSchema | None:
        async with self._lock:
            if server not in self._data or not self._data[server]:
                return None
            return self._data[server][-1]

    async def get_server_all(self, server: str) -> MetricsHistory | None:
        async with self._lock:
            if server not in self._data:
                return None
            return self._data[server]

    async def get_all(self) -> dict[ServerName, MetricsHistory]:
        async with self._lock:
            return self._data

    async def get_known_servers(self) -> list[ServerInfo]:
        async with self._lock:
            result = []
            for metrics in self._data.values():
                if metrics:
                    latest = metrics[-1]
                    result.append(ServerInfo(name=latest.server_name, ip=latest.ip))
            return result

metrics_repository = MetricsRepository(window=settings.HISTORY_WINDOW)