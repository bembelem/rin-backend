from datetime import datetime, timezone, timedelta

from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from database.database import async_session_maker
from database.models import Server, MetricSnapshot, Container
from app.schemas.schemas import (
    ServerMetricsSchema,
    ServerInfo,
    MemoryInfo,
    DiskInfo,
    NetworkInfo,
    LoadAverage,
    ContainerInfo,
)


async def _upsert_server(session: AsyncSession, name: str, ip: str | None) -> Server:
    """Найти сервер по имени или создать. Обновить ip/last_seen."""
    res = await session.execute(select(Server).where(Server.name == name))
    server = res.scalar_one_or_none()
    if server is None:
        server = Server(name=name, ip=ip)
        session.add(server)
        await session.flush()
    else:
        if ip:
            server.ip = ip
        server.last_seen = datetime.now(timezone.utc)
    return server


class MetricsDBRepository:
    """Персистентное хранилище метрик в PostgreSQL (история мониторинга)."""

    async def save_snapshot(self, m: ServerMetricsSchema) -> None:
        async with async_session_maker() as session:
            server = await _upsert_server(session, m.server_name, m.ip)
            snapshot = MetricSnapshot(
                server_id=server.id,
                timestamp=m.timestamp,
                status=m.status,
                cpu_percent=m.cpu_percent,
                memory_used_mb=m.memory.used_mb,
                memory_total_mb=m.memory.total_mb,
                memory_percent=m.memory.percent,
                disk_used_gb=m.disk.used_gb,
                disk_total_gb=m.disk.total_gb,
                disk_percent=m.disk.percent,
                net_rx_bytes=m.network.rx_bytes,
                net_tx_bytes=m.network.tx_bytes,
                net_rx_mb_per_sec=m.network.rx_mb_per_sec,
                net_tx_mb_per_sec=m.network.tx_mb_per_sec,
                load_1m=m.load_average.min_1,
                load_5m=m.load_average.min_5,
                load_15m=m.load_average.min_15,
                uptime_seconds=m.uptime_seconds,
                temperature_c=m.temperature_c,
            )
            snapshot.containers = [
                Container(
                    container_id=c.id,
                    name=c.name,
                    status=c.status,
                    image=c.image,
                    cpu_percent=c.cpu_percent,
                    memory_mb=c.memory_mb,
                    memory_limit_mb=c.memory_limit_mb,
                    net_rx_bytes=c.net_rx_bytes,
                    net_tx_bytes=c.net_tx_bytes,
                )
                for c in m.containers
            ]
            session.add(snapshot)
            await session.commit()

    async def get_latest(self, server_name: str) -> ServerMetricsSchema | None:
        async with async_session_maker() as session:
            res = await session.execute(
                select(MetricSnapshot)
                .join(Server)
                .where(Server.name == server_name)
                .order_by(desc(MetricSnapshot.timestamp))
                .limit(1)
                .options(
                    selectinload(MetricSnapshot.containers),
                    joinedload(MetricSnapshot.server),
                )
            )
            snapshot = res.scalar_one_or_none()
            if snapshot is None:
                return None
            return self._to_schema(snapshot, server_name)

    async def get_history(self, server_name: str, limit: int = 60) -> list[ServerMetricsSchema]:
        async with async_session_maker() as session:
            res = await session.execute(
                select(MetricSnapshot)
                .join(Server)
                .where(Server.name == server_name)
                .order_by(desc(MetricSnapshot.timestamp))
                .limit(limit)
                .options(
                    selectinload(MetricSnapshot.containers),
                    joinedload(MetricSnapshot.server),
                )
            )
            snapshots = res.scalars().all()
            # вернуть в хронологическом порядке (старые → новые)
            return [self._to_schema(s, server_name) for s in reversed(snapshots)]

    async def delete_older_than(self, days: int) -> int:
        """Удалить снапшоты старше N дней. Контейнеры удаляются каскадом (ON DELETE CASCADE).

        Возвращает число удалённых снапшотов.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with async_session_maker() as session:
            res = await session.execute(
                delete(MetricSnapshot).where(MetricSnapshot.timestamp < cutoff)
            )
            await session.commit()
            return res.rowcount or 0

    @staticmethod
    def _to_schema(s: MetricSnapshot, server_name: str) -> ServerMetricsSchema:
        return ServerMetricsSchema(
            server_name=server_name,
            ip=s.server.ip if s.server else None,
            status=s.status,
            timestamp=s.timestamp,
            cpu_percent=s.cpu_percent,
            memory=MemoryInfo(
                used_mb=s.memory_used_mb,
                total_mb=s.memory_total_mb,
                percent=s.memory_percent,
            ),
            disk=DiskInfo(
                used_gb=s.disk_used_gb,
                total_gb=s.disk_total_gb,
                percent=s.disk_percent,
            ),
            network=NetworkInfo(
                rx_bytes=s.net_rx_bytes,
                tx_bytes=s.net_tx_bytes,
                rx_mb_per_sec=s.net_rx_mb_per_sec,
                tx_mb_per_sec=s.net_tx_mb_per_sec,
            ),
            load_average=LoadAverage(min_1=s.load_1m, min_5=s.load_5m, min_15=s.load_15m),
            uptime_seconds=s.uptime_seconds,
            temperature_c=s.temperature_c,
            containers=[
                ContainerInfo(
                    id=c.container_id,
                    name=c.name,
                    status=c.status,
                    image=c.image,
                    cpu_percent=c.cpu_percent,
                    memory_mb=c.memory_mb,
                    memory_limit_mb=c.memory_limit_mb,
                    net_rx_bytes=c.net_rx_bytes,
                    net_tx_bytes=c.net_tx_bytes,
                )
                for c in s.containers
            ],
        )


class ServerDBRegistry:
    """Реестр серверов в БД. Заменяет in-memory ServerRegistry."""

    async def register(self, name: str, ip: str) -> None:
        async with async_session_maker() as session:
            await _upsert_server(session, name, ip)
            await session.commit()

    async def is_registered(self, ip: str) -> bool:
        async with async_session_maker() as session:
            res = await session.execute(select(Server.id).where(Server.ip == ip).limit(1))
            return res.first() is not None

    async def get_all(self) -> list[ServerInfo]:
        async with async_session_maker() as session:
            res = await session.execute(select(Server).order_by(Server.name))
            return [ServerInfo(name=s.name, ip=s.ip or "") for s in res.scalars().all()]


metrics_db = MetricsDBRepository()
server_db_registry = ServerDBRegistry()
