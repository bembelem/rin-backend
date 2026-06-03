from fastapi import APIRouter, HTTPException, Depends, Query
from starlette.requests import Request

from app.api.schemas.metrics import ServersResponse, SystemMetricsSchema, DockerMetricsSchema
from app.monitoring.metrics_repository import metrics_repository
from app.schemas.schemas import ServerMetricsSchema, ServerMetricsRequest, MetricsMode
from app.api.deps import verify_api_key
from database.repositories import metrics_db, server_db_registry as server_registry
from config import settings

router = APIRouter(tags=["System"])
SERVER_NAME = settings.SERVER_NAME

@router.get(
    "/health",
    summary="Хелс-чек",
    description="Проверяет доступность агента. Используется фронтом перед подключением по WebSocket.",
)
async def health():
    return {"status": "ok", "server": SERVER_NAME}

@router.get(
    "/metrics",
    summary="Снимок метрик",
    description="Одноразовый снимок метрик. `mode=system` — только хост, `mode=docker` — только контейнеры.",
    response_model=ServerMetricsSchema | SystemMetricsSchema | DockerMetricsSchema,
)
async def metrics(mode: MetricsMode | None = Query(default=None)):
    result = await metrics_repository.get_server_latest(SERVER_NAME)
    if result is None:
        raise HTTPException(status_code=503, detail="No metrics collected yet")
    if mode is MetricsMode.SYSTEM:
        return SystemMetricsSchema(**result.model_dump(exclude={"containers"}))
    if mode is MetricsMode.DOCKER:
        return DockerMetricsSchema(server_name=result.server_name, containers=result.containers)
    return result

@router.get(
    "/metrics/history",
    summary="История метрик",
    description="Возвращает последние N снимков метрик сервера из БД (хронологический порядок).",
    response_model=list[ServerMetricsSchema],
)
async def metrics_history(limit: int = Query(default=60, ge=1, le=1000)):
    return await metrics_db.get_history(SERVER_NAME, limit=limit)

@router.post("/metrics/push", dependencies=[Depends(verify_api_key)])
async def push_metrics(metrics_request: ServerMetricsRequest, request: Request):
    ip = request.client.host
    if not await server_registry.is_registered(ip):
        raise HTTPException(status_code=403, detail="Server not registered")
    metrics = ServerMetricsSchema(**metrics_request.model_dump(), ip=ip)
    await metrics_repository.push(metrics)
    return {"status": "ok"}

@router.post("/register", dependencies=[Depends(verify_api_key)])
async def register(request: Request, server_name: str):
    ip = request.client.host
    await server_registry.register(server_name, ip)
    return {"status": "ok"}

@router.get(
    "/servers",
    summary="Список серверов",
    description="Возвращает количество серверов и их имена.",
    response_model=ServersResponse
)
async def servers():
    servers = await server_registry.get_all()
    return ServersResponse(count=len(servers), servers=servers)
