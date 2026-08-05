"""Router de modelos IA — selecciona el mejor modelo gratuito por tarea."""

from enum import StrEnum

from src.config.settings import Settings


class TaskType(StrEnum):
    CONCEPT_EXTRACTION = "concept_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    DEFINITION_MERGE = "definition_merge"
    FLASHCARD_GENERATION = "flashcard_generation"
    EXAMPLE_GENERATION = "example_generation"
    ORAL_QUESTION = "oral_question"
    ORAL_EVALUATION = "oral_evaluation"
    MODEL_ANSWER = "model_answer"
    CASE_GENERATION = "case_generation"
    EMBEDDING = "embedding"
    SPEECH_TO_TEXT = "speech_to_text"


class ModelBackend(StrEnum):
    LLAMA_CPP = "llama_cpp"
    TRANSFORMERS = "transformers"
    HF_INFERENCE_API = "hf_inference_api"
    FASTER_WHISPER = "faster_whisper"


class ModelConfig:
    def __init__(
        self,
        model_id: str,
        backend: ModelBackend,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ):
        self.model_id = model_id
        self.backend = backend
        self.max_tokens = max_tokens
        self.temperature = temperature


class ModelRouter:
    """Selecciona modelos Hugging Face gratuitos según la tarea."""

    TASK_MODEL_MAP: dict[TaskType, ModelConfig] = {}

    def __init__(self, settings: Settings):
        self.settings = settings
        backend = self._llm_backend(settings)
        light_max = 900 if backend == ModelBackend.HF_INFERENCE_API else 4096
        eval_max = 700 if backend == ModelBackend.HF_INFERENCE_API else 4096
        self.TASK_MODEL_MAP = {
            TaskType.CONCEPT_EXTRACTION: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.1
            ),
            TaskType.RELATIONSHIP_EXTRACTION: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.1
            ),
            TaskType.DEFINITION_MERGE: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.05
            ),
            TaskType.FLASHCARD_GENERATION: ModelConfig(
                settings.llm_model_light, backend, max_tokens=light_max, temperature=0.3
            ),
            TaskType.EXAMPLE_GENERATION: ModelConfig(
                settings.llm_model_light, backend, max_tokens=light_max, temperature=0.35
            ),
            TaskType.ORAL_QUESTION: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.4
            ),
            TaskType.ORAL_EVALUATION: ModelConfig(
                settings.llm_model, backend, max_tokens=eval_max, temperature=0.1
            ),
            TaskType.MODEL_ANSWER: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.2
            ),
            TaskType.CASE_GENERATION: ModelConfig(
                settings.llm_model, backend, max_tokens=light_max, temperature=0.35
            ),
            TaskType.EMBEDDING: ModelConfig(
                settings.embedding_model, ModelBackend.TRANSFORMERS
            ),
            TaskType.SPEECH_TO_TEXT: ModelConfig(
                settings.stt_model, ModelBackend.FASTER_WHISPER
            ),
        }

    @staticmethod
    def _llm_backend(settings: Settings) -> ModelBackend:
        value = (settings.llm_backend or "").lower().strip()
        if value in {ModelBackend.HF_INFERENCE_API, "hf", "huggingface", "inference"}:
            return ModelBackend.HF_INFERENCE_API
        if value == ModelBackend.TRANSFORMERS:
            return ModelBackend.TRANSFORMERS
        if settings.hf_inference_api_fallback and settings.hf_token:
            return ModelBackend.HF_INFERENCE_API
        return ModelBackend.LLAMA_CPP

    def resolve(self, task: TaskType) -> ModelConfig:
        config = self.TASK_MODEL_MAP.get(task)
        if not config:
            raise ValueError(f"No hay modelo configurado para la tarea: {task}")
        return config

    def list_models(self) -> dict[str, str]:
        return {
            "llm_primary": self.settings.llm_model,
            "llm_light": self.settings.llm_model_light,
            "embedding": self.settings.embedding_model,
            "stt": self.settings.stt_model,
            "backend": self.settings.llm_backend,
        }
