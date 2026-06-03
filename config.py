import secrets
import socket
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def ensure_api_key_exists():
    env_file = Path(__file__).parent / ".env"
    content = env_file.read_text() if env_file.exists() else ""
    if "API_KEY=" not in content:
        key = secrets.token_hex(32)
        with open(env_file, "a") as f:
            f.write(f"\nAPI_KEY={key}\n")

class Settings(BaseSettings):
    DB_NAME: str
    DB_PORT: str
    DB_USER: str
    DB_PASS: str
    DB_HOST: str

    API_KEY: str
    SERVER_NAME: str = Field(default_factory=socket.gethostname)
    WS_INTERVAL: float = 2.0

    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "info"

    # Распределённая роль инстанса
    ROLE: str = "base"                 # "base" | "node"
    BASE_URL: str = "http://localhost:8080"   # куда нода пушит метрики
    PUSH_INTERVAL: float = 2.0         # как часто нода шлёт снапшот на base

    # Сбор и хранение метрик
    COLLECT_INTERVAL: float = 1.0      # как часто инстанс снимает свои метрики, сек
    HISTORY_WINDOW: int = 60           # сколько последних снапшотов хранить в памяти на сервер

    # Retention: удаление старых снапшотов из БД
    RETENTION_DAYS: int = 7            # хранить снапшоты не старше N дней
    RETENTION_INTERVAL: float = 3600  # как часто запускать чистку, сек

    # Сеть
    HTTP_TIMEOUT: float = 5.0          # таймаут исходящих запросов ноды на base, сек
    CORS_ORIGINS: str = "*"            # разрешённые origin'ы через запятую ("*" = все)

    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env", extra="ignore")

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # dsn = "postgresql+asyncpg://postgres:mypassword@localhost:5432/mydb"
    @property
    def DB_URL_ASYNC(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DB_URL_SYNC(self):
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

ensure_api_key_exists()
settings = Settings() # type: ignore

