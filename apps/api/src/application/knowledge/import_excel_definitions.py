"""Importa definiciones canónicas desde Excel de flashcards."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.concept import Concept, ConceptDefinition
from src.domain.knowledge.provenance import build_provenance
from src.infrastructure.knowledge.excel_flashcards_loader import (
    ExcelFlashcard,
    ExcelFlashcardsLoader,
    normalize_title,
    title_base,
)
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptDefinitionModel,
    ConceptModel,
)
from src.infrastructure.persistence.postgres.models import SubjectModel
from src.infrastructure.persistence.postgres.study_models import (
    ExamQuestionModel,
    OralExamSessionModel,
    UserConceptProgressModel,
)


@dataclass
class ImportExcelResult:
    subject_slug: str
    excel_rows: int
    updated: int
    created: int
    unchanged: int
    unmatched: int
    pruned: int
    examples: list[str]


class ImportExcelDefinitionsUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.loader = ExcelFlashcardsLoader()
        self.concept_repo = ConceptRepository(session)

    async def execute(
        self,
        subject_slug: str,
        file_bytes: bytes,
        *,
        create_missing: bool = True,
        prune_missing: bool = False,
        source_filename: str = "Flashcards_Derecho_Civil.xlsx",
    ) -> ImportExcelResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        cards = self.loader.load_bytes(file_bytes)
        if not cards:
            raise ValueError("El Excel no contiene filas concepto/definición válidas")

        concepts = await self._list_concepts(subject.id)
        updated = 0
        created = 0
        unchanged = 0
        unmatched = 0
        pruned = 0
        examples: list[str] = []
        used_ids: set[UUID] = set()

        for card in cards:
            match = self._find_match(card, concepts, used_ids)
            if match:
                used_ids.add(match.id)
                changed = await self._apply_card(match, card, source_filename)
                if changed:
                    updated += 1
                    if len(examples) < 5:
                        examples.append(f"↻ {match.title} → {card.title}")
                else:
                    unchanged += 1
                continue

            if not create_missing:
                unmatched += 1
                continue

            new_concept = await self._create_from_card(subject.id, card, source_filename)
            concepts.append(new_concept)
            used_ids.add(new_concept.id)
            created += 1
            if len(examples) < 8:
                examples.append(f"+ {card.title}")

        if prune_missing:
            orphan_ids = [c.id for c in concepts if c.id not in used_ids]
            if orphan_ids:
                titles = {c.id: c.title for c in concepts if c.id in set(orphan_ids)}
                await self.session.execute(
                    update(OralExamSessionModel)
                    .where(OralExamSessionModel.current_concept_id.in_(orphan_ids))
                    .values(current_concept_id=None)
                )
                await self.session.execute(
                    delete(UserConceptProgressModel).where(
                        UserConceptProgressModel.concept_id.in_(orphan_ids)
                    )
                )
                await self.session.execute(
                    delete(ExamQuestionModel).where(
                        ExamQuestionModel.concept_id.in_(orphan_ids)
                    )
                )
                await self.session.execute(
                    delete(ConceptChunkLinkModel).where(
                        ConceptChunkLinkModel.concept_id.in_(orphan_ids)
                    )
                )
                await self.session.execute(
                    delete(ConceptDefinitionModel).where(
                        ConceptDefinitionModel.concept_id.in_(orphan_ids)
                    )
                )
                await self.session.execute(
                    delete(ConceptModel).where(ConceptModel.id.in_(orphan_ids))
                )
                pruned = len(orphan_ids)
                for concept_id in orphan_ids[:5]:
                    examples.append(f"✕ {titles.get(concept_id, concept_id)}")

        return ImportExcelResult(
            subject_slug=subject_slug,
            excel_rows=len(cards),
            updated=updated,
            created=created,
            unchanged=unchanged,
            unmatched=unmatched,
            pruned=pruned,
            examples=examples,
        )

    async def _apply_card(
        self, concept: ConceptModel, card: ExcelFlashcard, source_filename: str
    ) -> bool:
        definition_changed = (concept.definition or "").strip() != card.definition.strip()
        title_changed = (concept.title or "").strip() != card.title.strip()
        # Siempre alinear categoría con la Materia del Excel cuando viene informada.
        subtopic_changed = bool(card.materia) and (concept.subtopic or "") != card.materia

        if not definition_changed and not title_changed and not subtopic_changed:
            return False

        if title_changed:
            concept.title = card.title
            # Mantener slug estable para no romper URLs/flashcards existentes.
        if definition_changed:
            concept.definition = card.definition
            concept.confidence_score = max(concept.confidence_score or 0.0, 0.98)
            await self._upsert_primary_definition(concept.id, card.definition, source_filename)
        if subtopic_changed and card.materia:
            concept.subtopic = card.materia
        return True

    async def _create_from_card(
        self, subject_id: UUID, card: ExcelFlashcard, source_filename: str
    ) -> ConceptModel:
        slug = Concept.slugify(card.title)
        existing = await self.session.execute(
            select(ConceptModel).where(
                ConceptModel.subject_id == subject_id,
                ConceptModel.slug == slug,
            )
        )
        model = existing.scalar_one_or_none()
        if model:
            await self._apply_card(model, card, source_filename)
            return model

        concept = Concept(
            id=None,
            subject_id=subject_id,
            slug=slug,
            title=card.title,
            definition=card.definition,
            subtopic=card.materia,
            confidence_score=0.98,
            metadata={"source": "EXCEL_FLASHCARDS"},
        )
        saved = await self.concept_repo.upsert_concept(concept)
        await self._upsert_primary_definition(saved.id, card.definition, source_filename)  # type: ignore[arg-type]
        result = await self.session.get(ConceptModel, saved.id)
        assert result is not None
        return result

    async def _upsert_primary_definition(
        self, concept_id: UUID, definition: str, source_filename: str
    ) -> None:
        result = await self.session.execute(
            select(ConceptDefinitionModel)
            .where(
                ConceptDefinitionModel.concept_id == concept_id,
                ConceptDefinitionModel.is_primary.is_(True),
            )
            .order_by(ConceptDefinitionModel.confidence.desc())
        )
        primaries = list(result.scalars().all())
        primary = primaries[0] if primaries else None
        for duplicate in primaries[1:]:
            duplicate.is_primary = False

        provenance = build_provenance(
            text=definition,
            source_document=source_filename,
            document_type=DocumentType.FLASHCARDS,
            source_role=SourceRole.DOCTRINE,
            page=None,
            chunk_id=None,
            extraction_method="EXCEL",
            confidence=0.98,
        )

        if primary:
            primary.text = definition
            primary.source_type = "EXCEL"
            primary.confidence = 0.98
            primary.provenance = provenance
            return

        await self.concept_repo.add_definition(
            concept_id,
            ConceptDefinition(
                text=definition,
                is_primary=True,
                source_type="EXCEL",
                document_id=None,
                page_number=None,
                chunk_id=None,
                confidence=0.98,
                provenance=provenance,
                display_label="Definición en Excel (flashcards)",
            ),
        )

    def _find_match(
        self,
        card: ExcelFlashcard,
        concepts: list[ConceptModel],
        used_ids: set[UUID],
    ) -> ConceptModel | None:
        target = normalize_title(card.title)
        target_base = title_base(card.title)
        # 1) Exacto
        for concept in concepts:
            if concept.id in used_ids:
                continue
            if normalize_title(concept.title) == target:
                return concept
        # 2) Sin paréntesis
        for concept in concepts:
            if concept.id in used_ids:
                continue
            if title_base(concept.title) == target_base and target_base:
                return concept
        # 3) Contención conservadora
        best: ConceptModel | None = None
        best_ratio = 0.0
        for concept in concepts:
            if concept.id in used_ids:
                continue
            candidate = title_base(concept.title)
            if not candidate or not target_base:
                continue
            shorter, longer = sorted((candidate, target_base), key=len)
            if shorter not in longer:
                continue
            ratio = len(shorter) / len(longer)
            if ratio >= 0.75 and ratio > best_ratio:
                best = concept
                best_ratio = ratio
        return best

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _list_concepts(self, subject_id: UUID) -> list[ConceptModel]:
        result = await self.session.execute(
            select(ConceptModel).where(ConceptModel.subject_id == subject_id)
        )
        return list(result.scalars().all())
