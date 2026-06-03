from pydantic import BaseModel, Field

from app.schemas.schemas import ServerInfo, ContainerInfo, MemoryInfo, DiskInfo, NetworkInfo, LoadAverage
from datetime import datetime


class WsMessage(BaseModel):
    action: str
    data: dict

class ServersResponse(BaseModel):
    count: int
    servers: list[ServerInfo]

class SystemMetricsSchema(BaseModel):
    server_name: str = Field(..., serialization_alias="name")
    ip: str | None
    status: str
    timestamp: datetime
    cpu_percent: float
    memory: MemoryInfo
    disk: DiskInfo
    network: NetworkInfo
    load_average: LoadAverage
    uptime_seconds: int
    temperature_c: float | None = None

class DockerMetricsSchema(BaseModel):
    server_name: str = Field(..., serialization_alias="name")
    containers: list[ContainerInfo]