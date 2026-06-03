import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings

router = APIRouter()
WS_INTERVAL = settings.WS_INTERVAL

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps({
            "action": "snapshot",
            "data": data
        })
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception as e:
                print(f"broadcast error: {e}")
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

manager = ConnectionManager()

async def _stream(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)


# Контракт фронта: VITE_WS_METRICS_URL=ws://host:8080/metrics
@router.websocket("/metrics")
async def websocket_metrics(ws: WebSocket):
    await _stream(ws)

    
# Совместимость: исторический путь, описан в openapi.yaml.
@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await _stream(ws)
