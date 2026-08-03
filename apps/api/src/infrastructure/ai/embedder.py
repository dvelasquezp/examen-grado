"""Servicio de embeddings BGE-M3."""

from uuid import UUID

from src.config.settings import Settings


class EmbeddingService:
    _model = None

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    @property
    def enabled(self) -> bool:
        return self.settings.embedding_enabled

    def _load_model(self):
        if EmbeddingService._model is not None:
            return EmbeddingService._model
        from sentence_transformers import SentenceTransformer

        EmbeddingService._model = SentenceTransformer(self.model_name)
        return EmbeddingService._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.enabled:
            return [[0.0] * self.dimensions for _ in texts]

        try:
            model = self._load_model()
            vectors = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                truncate_dim=self.dimensions,
            )
            return [v.tolist() for v in vectors]
        except ImportError:
            return [[0.0] * self.dimensions for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        prefixed = f"Representa esta consulta legal para buscar: {query}"
        result = self.embed_texts([prefixed])
        return result[0] if result else [0.0] * self.dimensions

    def embed_chunk(self, heading_path: list[str] | None, content: str) -> list[float]:
        prefix = ""
        if heading_path:
            prefix = f"[{' > '.join(heading_path)}] "
        return self.embed_texts([f"{prefix}{content}"])[0]
