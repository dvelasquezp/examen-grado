"""Caso de uso: completar definiciones de flashcards desde el MEMORIZADOR CIVIL."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.concept import ConceptDefinition
from src.domain.knowledge.provenance import build_provenance
from src.infrastructure.knowledge.memorizador_matcher import MemorizadorMatcher
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptDefinitionModel,
    ConceptModel,
)
from src.infrastructure.persistence.postgres.models import SubjectModel


@dataclass
class EnrichDefinitionsResult:
    subject_slug: str
    concepts_total: int
    memorizador_path: str
    entries_scanned: int
    enriched: int
    titles_fixed: int
    unchanged: int
    examples: list[str]


class EnrichDefinitionsUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.matcher = MemorizadorMatcher()
        self.concept_repo = ConceptRepository(session)
        self.content_root = Path(get_settings().content_path).resolve()

    async def execute(self, subject_slug: str) -> EnrichDefinitionsResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        memorizador = self.matcher.find_pdf(self.content_root)
        if not memorizador or not memorizador.exists():
            raise ValueError(
                "No se encontró MEMORIZADOR CIVIL.pdf. "
                "Colócalo junto a la materia (p. ej. DERECHO CIVIL 2/)."
            )

        concepts = await self._get_concepts(subject.id)
        if not concepts:
            raise ValueError("No hay conceptos. Extrae primero desde Flashcards.")

        entries = self.matcher.load_entries(memorizador)
        enriched = 0
        titles_fixed = 0
        unchanged = 0
        examples: list[str] = []

        for concept in concepts:
            match = self.matcher.match(concept.title, concept.definition, entries)
            if not match:
                unchanged += 1
                continue

            previous = concept.definition or ""
            canonical_title = self.matcher.canonical_title(match.label)
            definition_changed = match.definition.strip().lower() != previous.strip().lower()
            title_changed = (
                canonical_title
                and canonical_title.strip().upper() != (concept.title or "").strip().upper()
            )

            if not definition_changed and not title_changed:
                unchanged += 1
                continue

            model = await self.session.get(ConceptModel, concept.id)
            if not model:
                unchanged += 1
                continue

            if definition_changed:
                model.definition = match.definition
                await self._upsert_memorizador_definition(model.id, match.definition, memorizador.name)
                enriched += 1

            if title_changed:
                model.title = canonical_title
                titles_fixed += 1

            if len(examples) < 5 and (definition_changed or title_changed):
                detail = []
                if title_changed:
                    detail.append(f"título «{concept.title}» → «{canonical_title}»")
                if definition_changed:
                    detail.append(f"def «{previous[:50]}…» → «{match.definition[:60]}…»")
                examples.append(f"{concept.title}: {'; '.join(detail)}")

        return EnrichDefinitionsResult(
            subject_slug=subject_slug,
            concepts_total=len(concepts),
            memorizador_path=str(memorizador),
            entries_scanned=len(entries),
            enriched=enriched,
            titles_fixed=titles_fixed,
            unchanged=unchanged,
            examples=examples,
        )

    async def _upsert_memorizador_definition(
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
            extraction_method="MEMORIZADOR",
            confidence=0.95,
        )

        if primary:
            primary.text = definition
            primary.source_type = "MEMORIZADOR"
            primary.confidence = 0.95
            primary.provenance = provenance
            return

        await self.concept_repo.add_definition(
            concept_id,
            ConceptDefinition(
                text=definition,
                is_primary=True,
                source_type="MEMORIZADOR",
                document_id=None,
                page_number=None,
                chunk_id=None,
                confidence=0.95,
                provenance=provenance,
                display_label="Definición en Memorizador",
            ),
        )

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _get_concepts(self, subject_id: UUID) -> list[ConceptModel]:
        result = await self.session.execute(
            select(ConceptModel).where(ConceptModel.subject_id == subject_id)
        )
        return list(result.scalars().all())
