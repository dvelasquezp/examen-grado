"""Router de fuentes y lectura de chunks."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.chunk_repository import ChunkRepository
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.database import get_db_session
from src.presentation.v1.knowledge_schemas import ChunkDetailResponse

router = APIRouter(tags=["Fuentes"])


@router.get("/chunks/{chunk_id}", response_model=ChunkDetailResponse)
async def get_chunk_detail(
    chunk_id: UUID,
    concept_id: UUID | None = Query(None, description="Resalta el término del concepto"),
    session: AsyncSession = Depends(get_db_session),
):
    repo = ChunkRepository(session)
    detail = await repo.get_chunk_detail(chunk_id, concept_id=concept_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Fragmento no encontrado")

    highlight_term = None
    concept_title = None
    concept_slug = None
    if concept_id:
        concept_repo = ConceptRepository(session)
        concept = await concept_repo.get_by_id(concept_id)
        if concept:
            highlight_term = concept.title
            concept_title = concept.title
            concept_slug = concept.slug

    return ChunkDetailResponse(
        chunk_id=detail["chunk_id"],
        content=detail["content"],
        page_start=detail["page_start"],
        page_end=detail["page_end"],
        chapter=detail["chapter"],
        section=detail["section"],
        heading_path=detail["heading_path"],
        chunk_type=detail["chunk_type"],
        document_id=detail["document_id"],
        document_filename=detail["document_filename"],
        document_filepath=detail["document_filepath"],
        document_type=detail["document_type"],
        page_count=detail["page_count"],
        excerpt=detail["excerpt"],
        relevance_score=detail["relevance_score"],
        match_type=detail["match_type"],
        highlight_term=highlight_term,
        concept_id=concept_id,
        concept_title=concept_title,
        concept_slug=concept_slug,
    )
