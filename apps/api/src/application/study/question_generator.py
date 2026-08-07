"""Generador de preguntas basado en plantillas (sin LLM)."""

import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.knowledge_models import ConceptModel
from src.infrastructure.persistence.postgres.study_models import ExamQuestionModel


ORAL_TEMPLATES = [
    "Defina el concepto de «{title}» y explique sus elementos esenciales.",
    "¿Qué entiende por «{title}» en el Derecho Civil chileno?",
    "Explique «{title}» y mencione su importancia en el examen de grado.",
    "Profundice en el concepto de «{title}» y distíngalo de conceptos relacionados.",
    "El examinador le pregunta sobre «{title}». ¿Cómo respondería en 30 segundos?",
]


class QuestionGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_questions_for_subject(self, subject_id: UUID, limit: int = 500) -> int:
        concepts = list(
            (
                await self.session.execute(
                    select(ConceptModel)
                    .where(ConceptModel.subject_id == subject_id)
                    .order_by(ConceptModel.title)
                    .limit(limit)
                )
            ).scalars().all()
        )
        if not concepts:
            return 0

        existing_ids = set(
            (
                await self.session.execute(
                    select(ExamQuestionModel.concept_id).where(
                        ExamQuestionModel.subject_id == subject_id,
                        ExamQuestionModel.question_type == "ORAL",
                    )
                )
            ).scalars().all()
        )

        created = 0
        for concept in concepts:
            if concept.id in existing_ids:
                continue
            template = random.choice(ORAL_TEMPLATES)
            question_text = template.replace("{title}", concept.title or "")
            self.session.add(
                ExamQuestionModel(
                    subject_id=subject_id,
                    concept_id=concept.id,
                    question_text=question_text,
                    model_answer_hint=concept.definition,
                    question_type="ORAL",
                    difficulty=concept.difficulty or 3,
                    source_type="TEMPLATE",
                    metadata_={"concept_slug": concept.slug},
                )
            )
            created += 1

        if created:
            await self.session.flush()
        return created

    async def get_random_question(self, subject_id: UUID, exclude_ids: list[UUID] | None = None):
        query = (
            select(ExamQuestionModel, ConceptModel)
            .join(ConceptModel, ExamQuestionModel.concept_id == ConceptModel.id)
            .where(
                ExamQuestionModel.subject_id == subject_id,
                ExamQuestionModel.question_type == "ORAL",
            )
        )
        if exclude_ids:
            query = query.where(ExamQuestionModel.concept_id.notin_(exclude_ids))
        result = await self.session.execute(query)
        rows = list(result.all())
        if not rows:
            return None
        q_model, concept = random.choice(rows)
        return q_model, concept
