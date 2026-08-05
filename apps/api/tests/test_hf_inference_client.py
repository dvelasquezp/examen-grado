"""Tests del cliente Hugging Face y evaluación oral con fallback."""

from src.application.study.oral_exam_service import OralExamService
from src.config.settings import Settings
from src.infrastructure.ai.hf_inference_client import HFInferenceClient, HFInferenceError
from src.infrastructure.ai.llm_service import LLMService
from src.infrastructure.ai.model_router import ModelBackend, ModelRouter, TaskType


def test_hf_client_requires_token():
    client = HFInferenceClient(Settings(hf_token=""))
    assert not client.available
    try:
        client.chat([{"role": "user", "content": "hola"}])
        assert False, "debía fallar sin token"
    except HFInferenceError as exc:
        assert "HF_TOKEN" in str(exc)


def test_strip_thinking_blocks():
    text = "<think>razonamiento interno</think>\n\n{\"score\": 0.8}"
    assert HFInferenceClient._strip_thinking(text) == '{"score": 0.8}'


def test_parse_json_from_fenced_block():
    raw = '```json\n{"short_example": "hola", "practical_case": "caso"}\n```'
    data = HFInferenceClient._parse_json(raw)
    assert data["short_example"] == "hola"


def test_model_router_uses_hf_backend():
    settings = Settings(
        llm_backend="hf_inference_api",
        llm_model="Qwen/Qwen3-32B",
        hf_token="fake",
    )
    router = ModelRouter(settings)
    config = router.resolve(TaskType.ORAL_EVALUATION)
    assert config.backend == ModelBackend.HF_INFERENCE_API
    assert config.model_id == "Qwen/Qwen3-32B"


def test_llm_service_disabled_without_token():
    service = LLMService(Settings(llm_backend="hf_inference_api", hf_token=""))
    assert not service.enabled


def test_oral_heuristic_fallback_still_works():
    definition = "El contrato es un acuerdo de voluntades entre dos o más partes"
    answer = "Es un acuerdo de voluntades entre partes que crea obligaciones"
    result = OralExamService._evaluate(answer, definition)
    assert result["coverage"] > 0.3
    assert "score" in result
