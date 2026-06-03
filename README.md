# RIN Watchdog Backend

Система мониторинга серверов и Docker-контейнеров с автоматическим обнаружением через DNS SRV-записи.

## Архитектура

```
Браузер
  │
  ├─ DNS SRV lookup ──→ DNS сервер
  │                        │
  │              адрес одного из Base-серверов
  │
  ├─ GET /servers ────→ Base (bromage.ru)
  │                        │
  │              список всех Node-серверов
  │
  ├─ WS /ws ──────────→ Node (сервер 1)
  ├─ WS /ws ──────────→ Node (сервер 2)
  └─ WS /ws ──────────→ Node (сервер 3)
```

Каждый экземпляр — самостоятельный сервер с одинаковым кодом. Роль задаётся через переменную окружения. **Node** собирает метрики хоста и Docker-контейнеров и отправляет их на Base. **Base** делает то же самое, плюс принимает регистрацию Node-серверов и отдаёт их список фронту.

## Структура репозитория

```
RIN-Watchdog-Backend/
├── app/                 # сервис 
├── database/            # схема БД и миграции
├── docs/                # документация API (GitHub Pages)
├── docker-compose.yml   # локальный запуск
└── README.md
```

## Стек

- **Python 3.14** + **FastAPI** + **uvicorn**
- **psutil** — метрики хоста
- **docker SDK** — метрики контейнеров
- **uv** — управление зависимостями
- **Docker** + **Docker Compose**

## Быстрый старт

```bash
git clone https://github.com/rin-foundation/RIN-Watchdog-Backend
cd RIN-Watchdog-Backend

uv sync
uv run uvicorn app.main:app --reload --port 8080
```

По умолчанию запускается в режиме Node. Для Base:

```bash
ROLE=base uv run uvicorn app.main:app --port 8080
```

## Документация API

Доступна на GitHub Pages: `https://<username>.github.io/RIN-Watchdog-Backend/`