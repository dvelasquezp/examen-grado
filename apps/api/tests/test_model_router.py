"""Tests del Model Router."""

from src.config.settings import Settings
from src.infrastructure.ai.model_router import ModelBackend, ModelRouter, TaskType


def test_resolve_concept_extraction():
    settings = Settings()
    router = ModelRouter(settings)
    config = router.resolve(TaskType.CONCEPT_EXTRACTION)
    assert config.model_id == settings.llm_model
    assert config.backend == ModelBackend.LLAMA_CPP


def test_resolve_light_tasks_use_smaller_model():
    settings = Settings()
    router = ModelRouter(settings)
    config = router.resolve(TaskType.FLASHCARD_GENERATION)
    assert config.model_id == settings.llm_model_light


def test_resolve_embedding():
    settings = Settings()
    router = ModelRouter(settings)
    config = router.resolve(TaskType.EMBEDDING)
    assert config.model_id == settings.embedding_model
    assert config.backend == ModelBackend.TRANSFORMERS


def test_resolve_stt():
    settings = Settings()
    router = ModelRouter(settings)
    config = router.resolve(TaskType.SPEECH_TO_TEXT)
    assert config.model_id == settings.stt_model
    assert config.backend == ModelBackend.FASTER_WHISPER


def test_list_models():
    settings = Settings()
    router = ModelRouter(settings)
    models = router.list_models()
    assert "llm_primary" in models
    assert "embedding" in models
    assert "stt" in models
