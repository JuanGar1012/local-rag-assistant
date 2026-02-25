from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    APP_NAME: str = "Local RAG Assistant"
    APP_ENV: str = "dev"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: int = 120

    CHROMA_DIR: str = "data/chroma"
    CHROMA_COLLECTION: str = "portfolio_docs"
    SQLITE_PATH: str = "data/app.db"
    DOCS_DIR: str = "data/docs"
    BENCHMARK_PATH: str = "data/benchmarks/golden_eval.jsonl"
    REPORTS_DIR: str = "data/reports"

    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 150
    TOP_K: int = 5
    INGEST_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    INGEST_ALLOWED_HOSTS: str = ""
    INGEST_BLOCKED_HOSTS: str = "localhost,127.0.0.1,0.0.0.0"
    INGEST_ALLOW_PRIVATE_IPS: bool = False
    INGEST_LINK_MAX_RETRIES: int = 2
    INGEST_LINK_BACKOFF_SECONDS: float = 1.0
    WRITE_API_KEY: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlite_path(self) -> Path:
        return Path(self.SQLITE_PATH)

    @property
    def chroma_dir(self) -> Path:
        return Path(self.CHROMA_DIR)

    @property
    def docs_dir(self) -> Path:
        return Path(self.DOCS_DIR)

    @property
    def benchmark_path(self) -> Path:
        return Path(self.BENCHMARK_PATH)

    @property
    def reports_dir(self) -> Path:
        return Path(self.REPORTS_DIR)

    @property
    def ingest_allowed_hosts(self) -> list[str]:
        return [item.strip().lower() for item in self.INGEST_ALLOWED_HOSTS.split(",") if item.strip()]

    @property
    def ingest_blocked_hosts(self) -> list[str]:
        return [item.strip().lower() for item in self.INGEST_BLOCKED_HOSTS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
