from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class Server(Base):
    """Реестр серверов. Переживает рестарт (раньше registry жил в памяти)."""

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    snapshots: Mapped[list["MetricSnapshot"]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    alert_rules: Mapped[list["AlertRule"]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    alert_events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )


class MetricSnapshot(Base):
    """Снимок метрик хоста на момент времени."""

    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(16))

    cpu_percent: Mapped[float] = mapped_column(Float)

    memory_used_mb: Mapped[int] = mapped_column(Integer)
    memory_total_mb: Mapped[int] = mapped_column(Integer)
    memory_percent: Mapped[float] = mapped_column(Float)

    disk_used_gb: Mapped[float] = mapped_column(Float)
    disk_total_gb: Mapped[float] = mapped_column(Float)
    disk_percent: Mapped[float] = mapped_column(Float)

    net_rx_bytes: Mapped[int] = mapped_column(BigInteger)
    net_tx_bytes: Mapped[int] = mapped_column(BigInteger)
    net_rx_mb_per_sec: Mapped[float] = mapped_column(Float)
    net_tx_mb_per_sec: Mapped[float] = mapped_column(Float)

    load_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_5m: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_15m: Mapped[float | None] = mapped_column(Float, nullable=True)

    uptime_seconds: Mapped[int] = mapped_column(Integer)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    server: Mapped["Server"] = relationship(back_populates="snapshots")
    containers: Mapped[list["Container"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class Container(Base):
    """Метрики Docker-контейнера, привязанные к конкретному снимку."""

    __tablename__ = "containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("metric_snapshots.id", ondelete="CASCADE"), index=True
    )

    container_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    image: Mapped[str] = mapped_column(String(512))
    cpu_percent: Mapped[float] = mapped_column(Float)
    memory_mb: Mapped[int] = mapped_column(Integer)
    memory_limit_mb: Mapped[int] = mapped_column(Integer)
    net_rx_bytes: Mapped[int] = mapped_column(BigInteger)
    net_tx_bytes: Mapped[int] = mapped_column(BigInteger)

    snapshot: Mapped["MetricSnapshot"] = relationship(back_populates="containers")


class AlertRule(Base):
    """Правило порога: сработать, когда metric `op` threshold (напр. cpu_percent > 90)."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # null = правило применяется ко всем серверам
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    metric: Mapped[str] = mapped_column(String(64))   # cpu_percent | memory_percent | disk_percent | temperature_c
    op: Mapped[str] = mapped_column(String(2))         # ">" | ">=" | "<" | "<="
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server: Mapped["Server"] = relationship(back_populates="alert_rules")
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    """Факт срабатывания правила. Журнал событий + защита от повторного спама."""

    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)

    metric: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)        # фактическое значение в момент срабатывания
    threshold: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String(512))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    rule: Mapped["AlertRule"] = relationship(back_populates="events")
    server: Mapped["Server"] = relationship(back_populates="alert_events")
