# Развёртывание RIN Watchdog

Система состоит из **одного BASE-сервера** (центральный агрегатор + БД + API)
и **нескольких NODE-серверов** (сборщики метрик, пушат на base).

Архитектура — push-модель: узлы сами отправляют метрики на base
(работает за NAT, узлы не нужно делать публично доступными).

---

## Требования

- Linux-сервер(ы) с установленными **Docker** и **Docker Compose v2**.
- Сетевая доступность: NODE-серверы должны иметь исходящий доступ к `BASE:8080`.
- На BASE открыть входящий порт **8080** (firewall).

> ⚠️ **Docker Desktop на Windows/macOS:** контейнер видит метрики Linux-ВМ,
> а не вашей ОС. Корректные хост-метрики получаются только при нативном Docker
> на Linux.

---

## BASE-сервер

1. Склонировать репозиторий, перейти в каталог.
2. Создать `.env` (рядом с `docker-compose.yml`):

   ```env
   API_KEY=<сгенерируйте: openssl rand -hex 32>
   SERVER_NAME=base-1
   DB_NAME=rin-watchdog-backend
   DB_USER=postgres
   DB_PASS=<надёжный пароль>
   # CORS_ORIGINS=https://dashboard.example.com   # для прод-фронта
   ```

3. Запустить:

   ```bash
   docker compose up -d --build
   ```

   PostgreSQL поднимется, агент применит миграции Alembic и начнёт сбор.

4. Проверка:

   ```bash
   curl http://localhost:8080/health      # {"status":"ok",...}
   curl http://localhost:8080/servers     # список зарегистрированных серверов
   ```

**Что монтируется в контейнер base** (для корректных хост-метрик на Linux):
- `/var/run/docker.sock` — статистика других контейнеров;
- `/proc` → `/host/proc` — CPU/RAM/сеть/uptime хоста;
- `/` → `/host/root` — диск хоста.

---

## NODE-сервер (на каждом узле)

1. Склонировать репозиторий, перейти в каталог.
2. Создать `.env`:

   ```env
   SERVER_NAME=node-1                       # УНИКАЛЬНОЕ имя на каждом узле
   API_KEY=<тот же ключ, что на base>
   BASE_URL=http://<ip-или-домен-base>:8080
   ```

3. Запустить:

   ```bash
   docker compose -f docker-compose.node.yml up -d --build
   ```

Узел зарегистрируется на base (`POST /register`) и начнёт пушить метрики.
БД и порты узлу не нужны — он только инициирует исходящие соединения.

> На каждом узле `SERVER_NAME` должно быть **уникальным**, иначе метрики
> разных узлов сольются в один сервер в реестре.

---

## Проверка связки

На BASE:

```bash
curl http://localhost:8080/servers
```

Должны появиться base и все ноды. Живой поток метрик всех серверов:

```
ws://<base>:8080/metrics      # кадры {"action":"snapshot","data":{...}}
```

---

## Продакшн (рекомендации)

- Поставить **nginx** перед base: TLS (`wss://`, `https://`), проксирование на
  `127.0.0.1:8080`. Прокинуть `X-Forwarded-For` и запускать uvicorn с
  `--proxy-headers`, чтобы IP узлов определялись корректно за прокси.
- Закрыть `GET /key` от публичного доступа на уровне nginx.
- Настроить бэкап тома `pgdata`.
- Параметры тюнятся через `.env`: `COLLECT_INTERVAL`, `RETENTION_DAYS`,
  `PUSH_INTERVAL` и др. (см. `.env.example`).

---

## Управление миграциями

Схема накатывается автоматически при старте base. Вручную:

```bash
docker compose exec base uv run alembic upgrade head     # применить
docker compose exec base uv run alembic current          # текущая версия
```

После изменения ORM-моделей:

```bash
docker compose exec base uv run alembic revision --autogenerate -m "описание"
```
