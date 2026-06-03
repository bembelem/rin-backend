import asyncio
import socket
import time
from datetime import datetime

import psutil

from app.core.docker_stats import get_containers
from app.schemas.schemas import ServerMetricsSchema, MemoryInfo, DiskInfo, NetworkInfo, LoadAverage, ContainerInfo
from config import settings

SERVER_NAME = settings.SERVER_NAME

def get_cpu() -> float:
    return psutil.cpu_percent(interval=0.5)

def get_memory() -> dict:
    mem = psutil.virtual_memory()
    return {
        "used_mb": mem.used // 1024 // 1024,
        "total_mb": mem.total // 1024 // 1024,
        "percent": mem.percent,
    }

def get_disk() -> dict:
    disk = psutil.disk_usage("/")
    return {
        "used_gb": round(disk.used / 1024 ** 3, 1),
        "total_gb": round(disk.total / 1024 ** 3, 1),
        "percent": disk.percent,
    }

def get_network() -> dict:
    net1 = psutil.net_io_counters()
    time.sleep(0.5)
    net2 = psutil.net_io_counters()
    rx_per_sec = (net2.bytes_recv - net1.bytes_recv) * 2
    tx_per_sec = (net2.bytes_sent - net1.bytes_sent) * 2
    return {
        "rx_bytes": net2.bytes_recv,
        "tx_bytes": net2.bytes_sent,
        "rx_mb_per_sec": round(rx_per_sec / 1_000_000, 3),
        "tx_mb_per_sec": round(tx_per_sec / 1_000_000, 3),
    }

def get_load_average() -> dict:
    try:
        la = psutil.getloadavg()
        return {
            "min_1": round(la[0], 2),
            "min_5": round(la[1], 2),
            "min_15": round(la[2], 2),
        }
    except AttributeError:
        return {"min_1": None, "min_5": None, "min_15": None}

def get_uptime() -> int:
    return int(time.time() - psutil.boot_time())

def get_temperature() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
    except AttributeError:
        return None
    if not temps:
        return None
    for entries in temps.values():
        for entry in entries:
            t = entry.current
            # Отсеиваем нефизичные показания: контейнеры/виртуалки (Render и т.п.)
            # часто отдают -273.1 (абсолютный ноль) = «датчик недоступен».
            if t is not None and -50 <= t <= 150:
                return round(t, 1)
    return None


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


async def collect_metrics() -> ServerMetricsSchema:
    loop = asyncio.get_event_loop()

    cpu, memory, disk, network = await asyncio.gather(
        loop.run_in_executor(None, get_cpu),
        loop.run_in_executor(None, get_memory),
        loop.run_in_executor(None, get_disk),
        loop.run_in_executor(None, get_network),
    )

    containers = await get_containers()

    return ServerMetricsSchema(
        server_name=SERVER_NAME,
        ip=get_local_ip(),
        status="up",
        timestamp=datetime.utcnow(),
        cpu_percent=cpu,
        memory=MemoryInfo(**memory),
        disk=DiskInfo(**disk),
        network=NetworkInfo(**network),
        load_average=LoadAverage(**get_load_average()),
        uptime_seconds=get_uptime(),
        temperature_c=get_temperature(),
        containers=[ContainerInfo(**c) for c in containers],
    )
