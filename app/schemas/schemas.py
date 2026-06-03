from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ServerStatus(str, Enum):
    UP = "up"
    DOWN = "down"


class ContainerStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


class MetricsMode(str, Enum):
    SYSTEM = "system"
    DOCKER = "docker"


class WsAction(str, Enum):
    SNAPSHOT = "snapshot"


class ContainerInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    status: ContainerStatus
    image: str = Field(..., min_length=1, max_length=512)
    cpu_percent: float = Field(..., ge=0)
    memory_mb: int = Field(..., ge=0)
    memory_limit_mb: int = Field(..., ge=0, description="0 = без лимита")
    net_rx_bytes: int = Field(..., ge=0)
    net_tx_bytes: int = Field(..., ge=0)


class MemoryInfo(BaseModel):
    used_mb: int = Field(..., ge=0)
    total_mb: int = Field(..., gt=0)
    percent: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def _used_not_exceed_total(self):
        if self.used_mb > self.total_mb:
            raise ValueError("used_mb must be <= total_mb")
        return self


class DiskInfo(BaseModel):
    used_gb: float = Field(..., ge=0)
    total_gb: float = Field(..., gt=0)
    percent: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def _used_not_exceed_total(self):
        if self.used_gb > self.total_gb:
            raise ValueError("used_gb must be <= total_gb")
        return self


class NetworkInfo(BaseModel):
    rx_bytes: int = Field(..., ge=0)
    tx_bytes: int = Field(..., ge=0)
    rx_mb_per_sec: float = Field(..., ge=0)
    tx_mb_per_sec: float = Field(..., ge=0)


class LoadAverage(BaseModel):
    # Внутреннее имя поля min_1 — для входа (нода шлёт min_1/min_5/min_15);
    # наружу (WS/REST, by_alias=True) сериализуется как 1m/5m/15m — контракт фронта.
    min_1: float | None = Field(None, ge=0, serialization_alias="1m")
    min_5: float | None = Field(None, ge=0, serialization_alias="5m")
    min_15: float | None = Field(None, ge=0, serialization_alias="15m")

    model_config = {"populate_by_name": True}


class ServerInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ip: str = Field(..., min_length=1, max_length=45)


class ServerMetricsSchema(BaseModel):
    server_name: str = Field(..., min_length=1, max_length=255, serialization_alias="name")
    ip: str | None = Field(None, max_length=45)
    status: ServerStatus
    timestamp: datetime
    cpu_percent: float = Field(..., ge=0, le=100)
    memory: MemoryInfo
    disk: DiskInfo
    network: NetworkInfo
    load_average: LoadAverage
    uptime_seconds: int = Field(..., ge=0)
    temperature_c: float | None = Field(None, ge=-50, le=150)
    containers: list[ContainerInfo]


class ServerMetricsRequest(BaseModel):
    server_name: str = Field(..., min_length=1, max_length=255)
    status: ServerStatus
    timestamp: datetime
    cpu_percent: float = Field(..., ge=0, le=100)
    memory: MemoryInfo
    disk: DiskInfo
    network: NetworkInfo
    load_average: LoadAverage
    uptime_seconds: int = Field(..., ge=0)
    temperature_c: float | None = Field(None, ge=-50, le=150)
    containers: list[ContainerInfo]
