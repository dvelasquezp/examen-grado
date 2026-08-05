"""Configuración de la aplicación."""

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_query_params(url: str, params: set[str]) -> str:
    """Quita parámetros de la query string conservando el resto de la URL."""
    parsed = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in params]
    return urlunsplit(parsed._replace(query=urlencode(kept)))


def _clean_async_db_url(value: str) -> str:
    """asyncpg no acepta sslmode/channel_binding; el SSL se pasa en connect_args."""
    return _strip_query_params(value, {"channel_binding", "sslmode"})


def _clean_sync_db_url(value: str) -> str:
    """psycopg2 sí entiende sslmode, pero no channel_binding."""
    return _strip_query_params(value, {"channel_binding"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Examen de Grado"
    app_env: str = "development"
    debug: bool = True

    content_path: str = "."
    content_exclude_dirs: str = "apps,workers,infra,scripts,docs,node_modules,.git,.venv,venv,data,models,.cache,huggingface,dist"

    database_url: str = "postgresql+asyncpg://examen:examen@localhost:5432/examen_grado"
    database_url_sync: str = "postgresql://examen:examen@localhost:5432/examen_grado"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "examen_grado_secret"

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "examen_minio"
    s3_secret_key: str = "examen_minio_secret"
    s3_bucket: str = "examen-grado"

    llm_backend: str = "hf_inference_api"
    llm_model: str = "Qwen/Qwen3-32B"
    llm_model_light: str = "Qwen/Qwen3-32B"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    stt_model: str = "openai/whisper-large-v3"
    hf_token: str = ""
    hf_inference_api_fallback: bool = True
    hf_inference_base_url: str = "https://router.huggingface.co/v1"
    hf_inference_provider_policy: str = "cheapest"
    hf_inference_timeout_seconds: float = 90.0

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    embedding_enabled: bool = True
    chunk_max_chars: int = 3000

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_async_db_url(value)
        return value

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def normalize_sync_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_sync_db_url(value)
        return value

    @property
    def database_requires_ssl(self) -> bool:
        host = urlsplit(self.database_url).hostname or ""
        return host not in {"localhost", "127.0.0.1", "postgres", "db"}

    @property
    def exclude_dirs(self) -> set[str]:
        return {d.strip() for d in self.content_exclude_dirs.split(",") if d.strip()}

    @property
    def cors_origins_list(self) -> list[str]:
        origins: list[str] = []
        for origin in self.cors_origins.split(","):
            origin = origin.strip()
            if not origin:
                continue
            if not origin.startswith(("http://", "https://")):
                origin = f"https://{origin}"
            origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
