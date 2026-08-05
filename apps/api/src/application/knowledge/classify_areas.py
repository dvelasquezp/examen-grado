"""Caso de uso: asignar a cada concepto el área del temario a la que pertenece.

Los conceptos se extraen del PDF consolidado de flashcards, que no declara el
área a la que pertenece cada tarjeta. Se reconstruye combinando dos hechos:

- Cada concepto se desarrolla en uno de los apuntes. Se mide como proporción del
  apunte y no en menciones absolutas, porque si no los apuntes largos se llevan
  todo. La señal es directa pero ruidosa: los términos transversales abundan
  fuera de su área (`COMPENSACIÓN` aparece en Familia por la compensación
  económica, aunque se define en Obligaciones) y los títulos que el OCR dañó no
  se enlazan con ningún apunte.
- El mazo está ordenado por área, en bloques contiguos.

Por eso no se decide tarjeta a tarjeta, sino sobre la secuencia completa: se
busca la partición en bloques que mejor explica la evidencia, penalizando cada
cambio de área. Así una tarjeta aislada con evidencia dudosa se mantiene en el
bloque de sus vecinas, y el área sólo cambia cuando varias tarjetas seguidas lo
respaldan.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog.enums import DocumentType
from src.domain.knowledge.area import SubjectArea, parse_area
from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptDefinitionModel,
    ConceptModel,
)
from src.infrastructure.persistence.postgres.models import (
    DocumentChunkModel,
    DocumentModel,
    SubjectModel,
)

# Coste de empezar un bloque nuevo. Como la evidencia de cada tarjeta aporta
# entre 0 y 1, exigir este coste evita bloques de una sola tarjeta salvo que su
# evidencia sea muy superior a la de sus vecinas.
BLOCK_CHANGE_PENALTY = 0.45


@dataclass
class ClassifyAreasResult:
    subject_slug: str
    concepts_total: int
    with_evidence: int
    unassigned: int
    areas: dict[str, int]


class ClassifyAreasUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, subject_slug: str, *, force: bool = False) -> ClassifyAreasResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        areas_by_document = await self._areas_by_document(subject.id)
        if not areas_by_document:
            raise ValueError(
                "No hay apuntes con el patrón '(N) Nombre.pdf' para derivar áreas."
            )

        concepts = await self._get_concepts(subject.id)
        existing_subtopics = await self._existing_subtopics(concepts)
        mentions = await self._mentions_per_document(subject.id)
        sizes = await self._document_sizes(subject.id)
        order = await self._deck_order(subject.id)

        evidence = {
            concept_id: self._evidence_shares(
                mentions.get(concept_id, {}), areas_by_document, sizes
            )
            for concept_id in concepts
        }

        sequence = sorted(
            (concept_id for concept_id in concepts if concept_id in order),
            key=lambda concept_id: order[concept_id],
        )
        areas = sorted(set(areas_by_document.values()), key=lambda area: area.order)
        assignments = self._segment(sequence, evidence, areas)

        # Las tarjetas fuera del mazo no tienen vecinas: sólo cabe la evidencia.
        for concept_id in concepts:
            if concept_id in assignments or not evidence[concept_id]:
                continue
            assignments[concept_id] = max(
                evidence[concept_id].items(), key=lambda item: item[1]
            )[0]

        await self._persist(concepts, assignments, existing_subtopics, force=force)

        # Contar categorías finales en BD (incluye las que se preservaron del Excel).
        final_topics = await self._existing_subtopics(concepts)
        counts = Counter(name for name in final_topics.values() if name)
        unassigned = sum(1 for concept_id in concepts if not final_topics.get(concept_id))
        return ClassifyAreasResult(
            subject_slug=subject_slug,
            concepts_total=len(concepts),
            with_evidence=sum(1 for shares in evidence.values() if shares),
            unassigned=unassigned,
            areas=dict(counts.most_common()),
        )

    def _segment(
        self,
        sequence: list[UUID],
        evidence: dict[UUID, dict[SubjectArea, float]],
        areas: list[SubjectArea],
    ) -> dict[UUID, SubjectArea]:
        """Viterbi sobre el mazo: maximiza evidencia menos cambios de área."""
        if not sequence or not areas:
            return {}

        scores = {area: evidence[sequence[0]].get(area, 0.0) for area in areas}
        backpointers: list[dict[SubjectArea, SubjectArea]] = []

        for concept_id in sequence[1:]:
            best_area = max(scores, key=lambda area: scores[area])
            switch_score = scores[best_area] - BLOCK_CHANGE_PENALTY
            step_scores: dict[SubjectArea, float] = {}
            step_pointers: dict[SubjectArea, SubjectArea] = {}

            for area in areas:
                if scores[area] >= switch_score:
                    step_pointers[area] = area
                    base = scores[area]
                else:
                    step_pointers[area] = best_area
                    base = switch_score
                step_scores[area] = base + evidence[concept_id].get(area, 0.0)

            scores = step_scores
            backpointers.append(step_pointers)

        area = max(scores, key=lambda candidate: scores[candidate])
        assignments: dict[UUID, SubjectArea] = {sequence[-1]: area}
        for concept_id, pointers in zip(reversed(sequence[:-1]), reversed(backpointers)):
            area = pointers[area]
            assignments[concept_id] = area
        return assignments

    def _evidence_shares(
        self,
        mentions: dict[UUID, int],
        areas_by_document: dict[UUID, SubjectArea],
        sizes: dict[UUID, int],
    ) -> dict[SubjectArea, float]:
        densities: dict[SubjectArea, float] = defaultdict(float)
        for document_id, chunks in mentions.items():
            area = areas_by_document.get(document_id)
            size = sizes.get(document_id)
            if area and size:
                densities[area] += chunks / size
        total = sum(densities.values())
        if not total:
            return {}
        return {area: density / total for area, density in densities.items()}

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _areas_by_document(self, subject_id: UUID) -> dict[UUID, SubjectArea]:
        result = await self.session.execute(
            select(DocumentModel).where(
                DocumentModel.subject_id == subject_id,
                DocumentModel.document_type == DocumentType.LECTURE_NOTES,
            )
        )
        areas: dict[UUID, SubjectArea] = {}
        for document in result.scalars().all():
            area = parse_area(document.filename)
            if area:
                areas[document.id] = area
        return areas

    async def _get_concepts(self, subject_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(ConceptModel.id).where(ConceptModel.subject_id == subject_id)
        )
        return list(result.scalars().all())

    async def _mentions_per_document(self, subject_id: UUID) -> dict[UUID, dict[UUID, int]]:
        result = await self.session.execute(
            select(
                ConceptChunkLinkModel.concept_id,
                ConceptChunkLinkModel.document_id,
                func.count().label("chunks"),
            )
            .join(ConceptModel, ConceptModel.id == ConceptChunkLinkModel.concept_id)
            .where(ConceptModel.subject_id == subject_id)
            .group_by(ConceptChunkLinkModel.concept_id, ConceptChunkLinkModel.document_id)
        )
        mentions: dict[UUID, dict[UUID, int]] = defaultdict(dict)
        for concept_id, document_id, chunks in result.all():
            mentions[concept_id][document_id] = chunks
        return mentions

    async def _document_sizes(self, subject_id: UUID) -> dict[UUID, int]:
        result = await self.session.execute(
            select(DocumentChunkModel.document_id, func.count())
            .join(DocumentModel, DocumentModel.id == DocumentChunkModel.document_id)
            .where(DocumentModel.subject_id == subject_id)
            .group_by(DocumentChunkModel.document_id)
        )
        return {document_id: total for document_id, total in result.all()}

    async def _deck_order(self, subject_id: UUID) -> dict[UUID, tuple[int, int]]:
        """Orden de lectura de cada concepto dentro del PDF de flashcards."""
        result = await self.session.execute(
            select(
                ConceptDefinitionModel.concept_id,
                ConceptDefinitionModel.page_number,
                DocumentChunkModel.chunk_index,
            )
            .join(ConceptModel, ConceptModel.id == ConceptDefinitionModel.concept_id)
            .outerjoin(
                DocumentChunkModel, DocumentChunkModel.id == ConceptDefinitionModel.chunk_id
            )
            .where(
                ConceptModel.subject_id == subject_id,
                ConceptDefinitionModel.page_number.is_not(None),
            )
        )
        order: dict[UUID, tuple[int, int]] = {}
        for concept_id, page_number, chunk_index in result.all():
            order.setdefault(concept_id, (page_number, chunk_index or 0))
        return order

    async def _existing_subtopics(self, concept_ids: list[UUID]) -> dict[UUID, str | None]:
        if not concept_ids:
            return {}
        result = await self.session.execute(
            select(ConceptModel.id, ConceptModel.subtopic).where(
                ConceptModel.id.in_(concept_ids)
            )
        )
        return {row.id: row.subtopic for row in result.all()}

    async def _persist(
        self,
        concepts: list[UUID],
        assignments: dict[UUID, SubjectArea],
        existing_subtopics: dict[UUID, str | None],
        *,
        force: bool,
    ) -> None:
        result = await self.session.execute(
            select(ConceptModel).where(ConceptModel.id.in_(concepts))
        )
        for model in result.scalars().all():
            # No pisar categorías canónicas (Excel) salvo force=true.
            if not force and existing_subtopics.get(model.id):
                continue
            area = assignments.get(model.id)
            if area:
                model.subtopic = area.name
        await self.session.flush()
