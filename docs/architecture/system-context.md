**L1 - System Context** (система в окружении пользователей и других систем)

```mermaid
graph TB
    Admin[👤 SRE / Администратор<br/>Следит за состоянием инфраструктуры]

    System[🎯 RIN Watchdog<br/>Распределённая система мониторинга<br/>серверов и Docker-контейнеров]

    Dashboard[💻 Веб-дашборд<br/>Браузер пользователя]
    Docker[🐳 Docker Engine<br/>на каждом наблюдаемом хосте]
    Host[🖥️ Хост-ОС<br/>источник системных метрик]

    Admin -->|Просматривает состояние<br/>серверов и контейнеров| System
    System -->|Запрашивает снимки и поток метрик<br/>REST + WebSocket| Dashboard
    System -->|Читает метрики контейнеров<br/>Docker socket / Engine API| Docker
    System -->|Читает системные метрики<br/>psutil → /proc, sysfs| Host