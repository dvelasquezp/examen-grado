"""Caso de uso: eliminar conceptos de una materia para reconstruir el catálogo."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptDefinitionModel,
    ConceptModel,
)
from src.infrastructure.persistence.postgres.models import SubjectModel


@dataclass
class ResetConceptsResult:
    subject_slug: str
    concepts_deleted: int
    definitions_deleted: int
    links_deleted: int


class ResetConceptsUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, subject_slug: str) -> ResetConceptsResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        concept_ids = await self._concept_ids(subject.id)
        if not concept_ids:
            return ResetConceptsResult(
                subject_slug=subject_slug,
                concepts_deleted=0,
                definitions_deleted=0,
                links_deleted=0,
            )

        links_result = await self.session.execute(
            delete(ConceptChunkLinkModel).where(
                ConceptChunkLinkModel.concept_id.in_(concept_ids)
            )
        )
        defs_result = await self.session.execute(
            delete(ConceptDefinitionModel).where(
                ConceptDefinitionModel.concept_id.in_(concept_ids)
            )
        )
        concepts_result = await self.session.execute(
            delete(ConceptModel).where(ConceptModel.subject_id == subject.id)
        )

        return ResetConceptsResult(
            subject_slug=subject_slug,
            concepts_deleted=concepts_result.rowcount or 0,
            definitions_deleted=defs_result.rowcount or 0,
            links_deleted=links_result.rowcount or 0,
        )

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _concept_ids(self, subject_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(ConceptModel.id).where(ConceptModel.subject_id == subject_id)
        )
        return list(result.scalars().all())
