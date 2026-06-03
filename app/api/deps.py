from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

from config import settings

API_KEY = settings.API_KEY
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")