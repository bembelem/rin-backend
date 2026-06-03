from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import router as ws_router
from app.monitoring.metrics_collector import MetricsCollector
from app.monitoring.metrics_repository import metrics_repository
from app.monitoring.node_client import node_client
from app.monitoring.retention import retention_worker
from database.database import init_db
from config import settings

collector = MetricsCollector(repository=metrics_repository, interval=settings.COLLECT_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ROLE == "node":
        # Нода: только собирает и отправляет на base, БД не нужна.
        node_client.start()
        yield
        await node_client.stop()
    else:
        # Base: инициализируем схему БД, затем крутим локальный сбор + чистку.
        # Снапшоты от нод приходят через /metrics/push и тоже пишутся в БД.
        await init_db()
        collector.start()
        retention_worker.start()
        yield
        retention_worker.stop()
        collector.stop()

app = FastAPI(title="RIN Watchdog Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS_LIST, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
    )