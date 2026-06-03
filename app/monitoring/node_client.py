import asyncio
import logging

import httpx

from app.core.metrics import collect_metrics
from config import settings

logger = logging.getLogger(__name__)


class NodeClient:
    """
    На ROLE=node:
      1. При старте регистрируется на base через POST /register.
      2. В цикле собирает локальные метрики и пушит их на base через POST /metrics/push.

    На base ничего не пушим: репозиторий заполняется его собственным MetricsCollector'ом
    плюс приходящими снапшотами от нод.
    """

    def __init__(
        self,
        base_url: str,
        server_name: str,
        api_key: str,
        interval: float,
        timeout: float = 5.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.server_name = server_name
        self.headers = {"X-API-Key": api_key}
        self.interval = interval
        self.timeout = timeout
        self._task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None

    async def _register(self) -> None:
        assert self._client is not None
        try:
            r = await self._client.post(
                f"{self.base_url}/register",
                params={"server_name": self.server_name},
                headers=self.headers,
            )
            r.raise_for_status()
            logger.info("registered on base: %s", self.base_url)
        except Exception as e:
            logger.error("register failed: %s", e)

    async def _push_once(self) -> None:
        assert self._client is not None
        snapshot = await collect_metrics()
        payload = snapshot.model_dump(mode="json", exclude={"ip"})
        try:
            r = await self._client.post(
                f"{self.base_url}/metrics/push",
                json=payload,
                headers=self.headers,
            )
            r.raise_for_status()
        except Exception as e:
            logger.warning("push failed: %s", e)

    async def _loop(self) -> None:
        # Регистрация с ретраями: base может ещё не подняться к моменту старта ноды.
        while True:
            await self._register()
            break  # одной попытки достаточно, /register идемпотентен
        while True:
            try:
                await self._push_once()
            except Exception as e:
                logger.error("push loop iteration failed: %s", e)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=self.timeout)
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        if self._client:
            await self._client.aclose()


node_client = NodeClient(
    base_url=settings.BASE_URL,
    server_name=settings.SERVER_NAME,
    api_key=settings.API_KEY,
    interval=settings.PUSH_INTERVAL,
    timeout=settings.HTTP_TIMEOUT,
)
