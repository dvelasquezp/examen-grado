"""Router de conceptos."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.knowledge.classify_areas import ClassifyAreasUseCase
from src.application.knowledge.enrich_definitions import EnrichDefinitionsUseCase
from src.application.knowledge.extract_concepts import ExtractConceptsUseCase
from src.application.knowledge.import_excel_definitions import ImportExcelDefinitionsUseCase
from src.application.knowledge.link_notes import LinkNotesUseCase
from src.application.knowledge.reset_concepts import ResetConceptsUseCase
from src.config.settings import Settings, get_settings
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.database import get_db_session
from src.infrastructure.persistence.postgres.models import SubjectModel
from src.presentation.v1.knowledge_schemas import (
    ClassifyAreasResponse,
    ConceptDefinitionResponse,
    ConceptDetailResponse,
    ConceptNoteReferenceResponse,
    ConceptSummaryResponse,
    EnrichDefinitionsResponse,
    ExtractConceptsResponse,
    ImportExcelDefinitionsResponse,
    LinkNotesResponse,
    ResetConceptsResponse,
)
from sqlalchemy import select

router = APIRouter(tags=["Conceptos"])


@router.post("/subjects/{slug}/concepts/extract", response_model=ExtractConceptsResponse)
async def extract_concepts(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    use_case = ExtractConceptsUseCase(session, settings)
    try:
        result = await use_case.execute(slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ExtractConceptsResponse(
        subject_slug=result.subject_slug,
        candidates_found=result.candidates_found,
        concepts_created=result.concepts_created,
        concepts_updated=result.concepts_updated,
        definitions_added=result.definitions_added,
    )


@router.post("/subjects/{slug}/concepts/reset", response_model=ResetConceptsResponse)
async def reset_concepts(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    use_case = ResetConceptsUseCase(session)
    try:
        result = await use_case.execute(slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ResetConceptsResponse(
        subject_slug=result.subject_slug,
        concepts_deleted=result.concepts_deleted,
        definitions_deleted=result.definitions_deleted,
        links_deleted=result.links_deleted,
    )


@router.post("/subjects/{slug}/concepts/link-notes", response_model=LinkNotesResponse)
async def link_notes_to_concepts(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    use_case = LinkNotesUseCase(session)
    try:
        result = await use_case.execute(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LinkNotesResponse(
        subject_slug=result.subject_slug,
        concepts_total=result.concepts_total,
        chunks_scanned=result.chunks_scanned,
        links_found=result.links_found,
        links_created=result.links_created,
        links_skipped=result.links_skipped,
    )


@router.post(
    "/subjects/{slug}/concepts/classify-areas", response_model=ClassifyAreasResponse
)
async def classify_concept_areas(
    slug: str,
    force: bool = Query(
        False,
        description="Si es false, no sobrescribe categorías ya asignadas (p. ej. desde Excel)",
    ),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        result = await ClassifyAreasUseCase(session).execute(slug, force=force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ClassifyAreasResponse(
        subject_slug=result.subject_slug,
        concepts_total=result.concepts_total,
        with_evidence=result.with_evidence,
        unassigned=result.unassigned,
        areas=result.areas,
    )


@router.post(
    "/subjects/{slug}/concepts/enrich-definitions",
    response_model=EnrichDefinitionsResponse,
)
async def enrich_concept_definitions(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        result = await EnrichDefinitionsUseCase(session).execute(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return EnrichDefinitionsResponse(
        subject_slug=result.subject_slug,
        concepts_total=result.concepts_total,
        memorizador_path=result.memorizador_path,
        entries_scanned=result.entries_scanned,
        enriched=result.enriched,
        titles_fixed=result.titles_fixed,
        unchanged=result.unchanged,
        examples=result.examples,
    )


@router.post(
    "/subjects/{slug}/concepts/import-excel",
    response_model=ImportExcelDefinitionsResponse,
)
async def import_excel_definitions(
    slug: str,
    file: UploadFile = File(..., description="Excel de flashcards (concepto/definición)"),
    create_missing: bool = Query(True),
    prune_missing: bool = Query(
        False,
        description="Elimina conceptos que no estén en el Excel (basura OCR)",
    ),
    session: AsyncSession = Depends(get_db_session),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Excel demasiado grande (máx. 20 MB)")
    try:
        result = await ImportExcelDefinitionsUseCase(session).execute(
            slug,
            data,
            create_missing=create_missing,
            prune_missing=prune_missing,
            source_filename=file.filename or "Flashcards_Derecho_Civil.xlsx",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ImportExcelDefinitionsResponse(
        subject_slug=result.subject_slug,
        excel_rows=result.excel_rows,
        updated=result.updated,
        created=result.created,
        unchanged=result.unchanged,
        unmatched=result.unmatched,
        pruned=result.pruned,
        examples=result.examples,
    )


@router.get("/subjects/{slug}/concepts", response_model=list[ConceptSummaryResponse])
async def list_concepts(
    slug: str,
    q: str | None = None,
    limit: int = Query(500, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    subject = await _get_subject(session, slug)
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    repo = ConceptRepository(session)
    concepts = await repo.list_by_subject(subject.id, limit=limit, offset=offset, q=q)
    return [
        ConceptSummaryResponse(
            id=c.id,  # type: ignore[arg-type]
            slug=c.slug,
            title=c.title,
            definition=c.definition,
            subtopic=c.subtopic,
            difficulty=c.difficulty,
            confidence_score=c.confidence_score,
            definition_count=len(c.definitions),
        )
        for c in concepts
    ]


@router.get("/concepts/{concept_id}", response_model=ConceptDetailResponse)
async def get_concept(concept_id: UUID, session: AsyncSession = Depends(get_db_session)):
    repo = ConceptRepository(session)
    concept = await repo.get_by_id(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")

    note_links = await repo.list_chunk_links(concept_id)

    meta = concept.metadata or {}
    return ConceptDetailResponse(
        id=concept.id,  # type: ignore[arg-type]
        slug=concept.slug,
        title=concept.title,
        definition=concept.definition,
        simple_explanation=concept.simple_explanation or meta.get("short_example"),
        practical_case=meta.get("practical_case"),
        subtopic=concept.subtopic,
        difficulty=concept.difficulty,
        importance_score=concept.importance_score,
        confidence_score=concept.confidence_score,
        definitions=[
            ConceptDefinitionResponse(
                text=d.text,
                is_primary=d.is_primary,
                source_type=d.source_type,
                page_number=d.page_number,
                confidence=d.confidence,
                provenance=d.provenance,
                display_label=d.display_label,
            )
            for d in concept.definitions
        ],
        note_references=[
            ConceptNoteReferenceResponse(
                chunk_id=link.chunk_id,
                document_id=link.document_id,
                document_filename=link.document_filename or "",
                page_number=link.page_number,
                match_type=link.match_type,
                relevance_score=link.relevance_score,
                excerpt=link.excerpt,
                display_label=(link.provenance or {})
                .get("statements", [{}])[0]
                .get("display_label", "Mención en Apuntes"),
            )
            for link in note_links
        ],
        created_at=concept.created_at,
    )


async def _get_subject(session: AsyncSession, slug: str) -> SubjectModel | None:
    result = await session.execute(select(SubjectModel).where(SubjectModel.slug == slug))
    return result.scalar_one_or_none()
