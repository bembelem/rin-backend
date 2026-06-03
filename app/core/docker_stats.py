import asyncio
from typing import Optional

import aiodocker
import docker

_client: Optional[docker.DockerClient] = None

def get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client

def _calculate_cpu_percent(stats: dict) -> float:
    try:
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        num_cpus = stats["cpu_stats"].get("online_cpus") or len(
            stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
        )
        if system_delta > 0:
            return round((cpu_delta / system_delta) * num_cpus * 100, 2)
    except (KeyError, ZeroDivisionError):
        pass
    return 0.0

async def _get_container_info(docker_client: aiodocker.Docker, container: dict) -> dict:
    container_id = container["Id"][:12]
    name = container["Names"][0].lstrip("/")
    status = container["State"]
    image = container["Image"]

    entry = {
        "id": container_id,
        "name": name,
        "status": status,
        "image": image,
        "cpu_percent": 0.0,
        "memory_mb": 0,
        "memory_limit_mb": 0,
        "net_rx_bytes": 0,
        "net_tx_bytes": 0,
    }

    if status == "running":
        try:
            c = docker_client.containers.container(container["Id"])
            stats = await c.stats(stream=False)
            stats = stats[0]
            entry["cpu_percent"] = _calculate_cpu_percent(stats)
            mem = stats.get("memory_stats", {})
            entry["memory_mb"] = mem.get("usage", 0) // 1024 // 1024
            entry["memory_limit_mb"] = mem.get("limit", 0) // 1024 // 1024
            networks = stats.get("networks", {})
            entry["net_rx_bytes"] = sum(v["rx_bytes"] for v in networks.values())
            entry["net_tx_bytes"] = sum(v["tx_bytes"] for v in networks.values())
        except Exception:
            pass

    return entry

async def get_containers() -> list[dict]:
    try:
        async with aiodocker.Docker() as docker_client:
            containers = await docker_client.containers.list(all=True)
            return await asyncio.gather(*[
                _get_container_info(docker_client, c._container)
                for c in containers
            ])
    except Exception:
        return []