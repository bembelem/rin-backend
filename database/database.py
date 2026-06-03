import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

engine_async = create_async_engine(settings.DB_URL_ASYNC)

engine_sync = create_engine(settings.DB_URL_SYNC)

async_session_maker = async_sessionmaker(bind=engine_async, expire_on_commit=False)

sync_session_maker = sessionmaker(bind=engine_sync, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


def _run_migrations() -> None:
    """Накатить миграции отдельным процессом — `alembic upgrade head`."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed (code {result.returncode}):\n"
            f"{result.stdout}\n{result.stderr}"
        )


async def init_db() -> None:
    """Привести схему БД к актуальной версии (миграции Alembic)."""
    await asyncio.to_thread(_run_migrations)
