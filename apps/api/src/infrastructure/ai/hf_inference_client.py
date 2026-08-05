"""Cliente Hugging Face Inference Providers (OpenAI-compatible)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from src.config.settings import Settings

logger = logging.getLogger(__name__)

THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


class HFInferenceError(RuntimeError):
    """Error al llamar a Hugging Face Inference Providers."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class HFInferenceClient:
    """Llama a Qwen vía https://router.huggingface.co/v1/chat/completions."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.hf_inference_base_url.rstrip("/")
        self.timeout = settings.hf_inference_timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.settings.hf_token.strip())

    def chat(
        self,
        messages: list[ChatMessage] | list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        if not self.available:
            raise HFInferenceError(
                "HF_TOKEN no configurado. Crea un token en Hugging Face "
                "(permiso «Make calls to Inference Providers») y añádelo al .env."
            )

        payload_messages = [
            {"role": m.role, "content": m.content} if isinstance(m, ChatMessage) else m
            for m in messages
        ]
        model_id = model or self.settings.llm_model
        # :cheapest prioriza proveedores baratos del plan gratuito cuando existen.
        if ":" not in model_id:
            model_id = f"{model_id}:{self.settings.hf_inference_provider_policy}"

        body: dict = {
            "model": model_id,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.settings.hf_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise HFInferenceError(
                f"Timeout ({self.timeout}s) llamando a Hugging Face."
            ) from exc
        except httpx.HTTPError as exc:
            raise HFInferenceError(f"Error de red con Hugging Face: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text[:500]
            raise HFInferenceError(
                f"Hugging Face HTTP {response.status_code}: {detail}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HFInferenceError(f"Respuesta HF inesperada: {data!r}") from exc

        return self._strip_thinking(content or "")

    def chat_json(
        self,
        messages: list[ChatMessage] | list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> dict:
        raw = self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
        return self._parse_json(raw)

    @staticmethod
    def _strip_thinking(text: str) -> str:
        cleaned = THINK_BLOCK.sub("", text).strip()
        if "</think>" in cleaned:
            cleaned = cleaned.split("</think>")[-1].strip()
        return cleaned

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise HFInferenceError(f"No se pudo parsear JSON del modelo: {text[:300]}")
            data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise HFInferenceError("El modelo no devolvió un objeto JSON")
        return data
