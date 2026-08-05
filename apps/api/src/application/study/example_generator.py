"""Genera ejemplos cortos y casos prácticos con Qwen + materiales doctrinales."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.study.content_context import ContentContextService
from src.config.settings import Settings, get_settings
from src.infrastructure.ai.hf_inference_client import HFInferenceError
from src.infrastructure.ai.llm_service import LLMService
from src.infrastructure.ai.model_router import TaskType
from src.infrastructure.persistence.postgres.knowledge_models import ConceptModel
from src.infrastructure.persistence.postgres.models import SubjectModel

SYSTEM_PROMPT = """Eres un ayudante de preparación para el Examen de Grado Oral de Derecho Civil chileno.
Usa ÚNICAMENTE el material doctrinal entregado como fuente de verdad.
No inventes artículos ni doctrinas no respaldadas por el contexto.
Responde SOLO JSON válido, sin markdown."""


@dataclass
class ExampleGenerationResult:
    subject_slug: str
    requested: int
    generated: int
    failed: int
    examples: list[dict]


class ExampleGenerator:
    def __init__(self, session: AsyncSession, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.llm = LLMService(self.settings)
        self.context = ContentContextService(session)

    async def generate_for_subject(
        self,
        subject_slug: str,
        *,
        limit: int = 20,
        force: bool = False,
    ) -> ExampleGenerationResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        concepts = await self._select_concepts(subject.id, limit=limit, force=force)
        generated = 0
        failed = 0
        examples: list[dict] = []

        for concept in concepts:
            try:
                payload = await self._generate_one(concept)
            except HFInferenceError:
                failed += 1
                continue
            except Exception:
                failed += 1
                continue

            meta = dict(concept.metadata_ or {})
            meta["practical_case"] = payload.get("practical_case")
            meta["short_example"] = payload.get("short_example")
            meta["examples_source"] = "QWEN3_HF"
            concept.metadata_ = meta
            if payload.get("short_example"):
                concept.simple_explanation = payload["short_example"]
            generated += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "title": concept.title,
                        "short_example": payload.get("short_example"),
                        "practical_case": payload.get("practical_case"),
                    }
                )

        await self.session.flush()
        return ExampleGenerationResult(
            subject_slug=subject_slug,
            requested=len(concepts),
            generated=generated,
            failed=failed,
            examples=examples,
        )

    async def generate_for_concept(self, concept_id: UUID) -> dict:
        concept = await self.session.get(ConceptModel, concept_id)
        if not concept:
            raise ValueError("Concepto no encontrado")
        payload = await self._generate_one(concept)
        meta = dict(concept.metadata_ or {})
        meta["practical_case"] = payload.get("practical_case")
        meta["short_example"] = payload.get("short_example")
        meta["examples_source"] = "QWEN3_HF"
        concept.metadata_ = meta
        if payload.get("short_example"):
            concept.simple_explanation = payload["short_example"]
        await self.session.flush()
        return {
            "concept_id": str(concept.id),
            "title": concept.title,
            **payload,
        }

    async def _generate_one(self, concept: ConceptModel) -> dict:
        context = await self.context.for_concept(concept)
        user = f"""Concepto: {concept.title}

Material doctrinal (fuente de verdad):
{context}

Genera:
1) short_example: 1-2 frases, ejemplo concreto y didáctico del concepto.
2) practical_case: caso práctico breve (3-6 oraciones) tipo pregunta oral de grado, con hechos y la pregunta al final.

JSON exacto:
{{
  "short_example": "...",
  "practical_case": "..."
}}"""
        data = self.llm.generate_json(TaskType.EXAMPLE_GENERATION, SYSTEM_PROMPT, user)
        short = str(data.get("short_example") or "").strip()
        case = str(data.get("practical_case") or "").strip()
        if not short and not case:
            raise HFInferenceError("El modelo no generó ejemplos útiles")
        return {"short_example": short, "practical_case": case}

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _select_concepts(
        self, subject_id: UUID, *, limit: int, force: bool
    ) -> list[ConceptModel]:
        query = (
            select(ConceptModel)
            .where(ConceptModel.subject_id == subject_id)
            .order_by(ConceptModel.title)
            .limit(limit)
        )
        concepts = list((await self.session.execute(query)).scalars().all())
        if force:
            return concepts
        return [
            c
            for c in concepts
            if not (c.metadata_ or {}).get("short_example") and not c.simple_explanation
        ]
