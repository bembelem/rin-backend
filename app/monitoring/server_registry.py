import asyncio

from app.schemas.schemas import ServerInfo


class ServerRegistry:
    def __init__(self):
        self._servers: dict[str, ServerInfo] = {}
        self._ips: set[str] = set()
        self._lock = asyncio.Lock()

    async def register(self, name: str, ip: str):
        async with self._lock:
            self._servers[name] = ServerInfo(name=name, ip=ip)
            self._ips.add(ip)

    async def get_all(self) -> list[ServerInfo]:
        async with self._lock:
            return list(self._servers.values())

    async def is_registered(self, ip: str) -> bool:
        async with self._lock:
            return ip in self._ips

server_registry = ServerRegistry()