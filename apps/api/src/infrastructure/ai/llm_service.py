"""Servicio LLM de alto nivel: Qwen vía Hugging Face, con tareas tipadas."""

from __future__ import annotations

import logging

from src.config.settings import Settings, get_settings
from src.infrastructure.ai.hf_inference_client import (
    ChatMessage,
    HFInferenceClient,
    HFInferenceError,
)
from src.infrastructure.ai.model_router import ModelBackend, ModelRouter, TaskType

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.router = ModelRouter(self.settings)
        self.hf = HFInferenceClient(self.settings)

    @property
    def enabled(self) -> bool:
        backend = self.settings.llm_backend.lower()
        if backend == ModelBackend.HF_INFERENCE_API:
            return self.hf.available
        # Permitir HF si hay token aunque el backend legacy diga llama_cpp,
        # cuando se activa el flag de fallback/API.
        return self.settings.hf_inference_api_fallback and self.hf.available

    def generate(
        self,
        task: TaskType,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
    ) -> str:
        config = self.router.resolve(task)
        messages = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]
        if not self.enabled:
            raise HFInferenceError("LLM no disponible (sin HF_TOKEN o backend desactivado)")
        return self.hf.chat(
            messages,
            model=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            json_mode=json_mode,
        )

    def generate_json(self, task: TaskType, system: str, user: str) -> dict:
        config = self.router.resolve(task)
        messages = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]
        if not self.enabled:
            raise HFInferenceError("LLM no disponible (sin HF_TOKEN o backend desactivado)")
        return self.hf.chat_json(
            messages,
            model=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
