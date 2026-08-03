"""Configuración Celery."""

from celery import Celery

from src.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "examen_grado",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Santiago",
    enable_utc=True,
    task_routes={
        "src.infrastructure.messaging.tasks.ingest_document": {"queue": "ingestion"},
        "src.infrastructure.messaging.tasks.discover_subjects": {"queue": "ingestion"},
    },
)

celery_app.autodiscover_tasks(["src.infrastructure.messaging"])
