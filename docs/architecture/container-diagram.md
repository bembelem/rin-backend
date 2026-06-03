**L2 - Container Diagram** (что внутри RIN Watchdog, как достигается распределённость)

```mermaid
flowchart TB
 subgraph Base_inst["Инстанс · ROLE=base"]
        FrontB["📦 nginx<br>TLS · раздаёт SPA + reverse-proxy"]
        BackB["🧭 FastAPI<br>реестр узлов · релэй метрик · выпуск ключей<br>+ свои метрики хоста"]
        SPA["🖼️ Дашборд SPA<br>исполняется в браузере"]
  end
 subgraph Node_inst["Инстанс · ROLE=node · ×N"]
        BackN["📡 FastAPI<br>сборщик метрик · push на Base"]
  end
    User["👤 Пользователь"] -- "https://bromage.ru" --> FrontB
    FrontB -. отдаёт SPA .-> SPA
    FrontB <-- "compose-сеть" --> BackB
    BackB -. "Ключ" .-> User
    User -. "вставляет ключ в .env при деплое" .-> Node_inst
    BackN -. регистрация при старте .-> FrontB
    BackN -- HTTPS · push метрик --> FrontB
    BackB --> HostB["🖥️ Хост · Base"] & DockerB["🐳 Docker · Base"]
    BackN --> HostN["🖥️ Хост · Node"] & DockerN["🐳 Docker · Node"]