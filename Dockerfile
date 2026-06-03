# syntax=docker/dockerfile:1
FROM python:3.14-slim

# uv — менеджер зависимостей
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Минимальные build-инструменты на случай, если под Python 3.14 нет готовых
# wheel'ов (psutil/asyncpg) и пакеты собираются из исходников.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Сначала только манифесты — слой с зависимостями кэшируется отдельно от кода
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Затем исходники
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
