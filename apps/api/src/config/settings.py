"""Configuración de la aplicación."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    content_exclude_dirs: str = "apps,workers,infra,scripts,docs,node_modules,.git,.venv,venv,data,models,.cache,huggingface"

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

    llm_backend: str = "llama_cpp"
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_model_light: str = "Qwen/Qwen2.5-3B-Instruct"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    stt_model: str = "openai/whisper-large-v3"
    hf_token: str = ""
    hf_inference_api_fallback: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    embedding_enabled: bool = True
    chunk_max_chars: int = 3000

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
