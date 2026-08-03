"""Routers de catálogo."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.catalog.discover_subjects import DiscoverSubjectsUseCase
from src.config.settings import Settings, get_settings
from src.infrastructure.persistence.postgres.catalog_repository import CatalogRepository
from src.infrastructure.persistence.postgres.database import get_db_session
from src.infrastructure.persistence.postgres.models import DocumentModel, SubjectModel
from src.presentation.v1.schemas import (
    DiscoverResponse,
    DocumentResponse,
    MaintenanceStatusResponse,
    SubjectResponse,
)

router = APIRouter(prefix="/catalog", tags=["Catálogo"])


@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(session: AsyncSession = Depends(get_db_session)):
    repo = CatalogRepository(session)
    subjects = await repo.list_subjects()

    counts_result = await session.execute(
        select(DocumentModel.subject_id, func.count(DocumentModel.id))
        .group_by(DocumentModel.subject_id)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    return [
        SubjectResponse(
            id=s.id,  # type: ignore[arg-type]
            slug=s.slug,
            name=s.name,
            folder_path=s.folder_path,
            is_active=s.is_active,
            discovered_at=s.discovered_at,
            document_count=counts.get(s.id, 0),
        )
        for s in subjects
    ]


@router.get("/subjects/{slug}", response_model=SubjectResponse)
async def get_subject(slug: str, session: AsyncSession = Depends(get_db_session)):
    repo = CatalogRepository(session)
    subject = await repo.get_subject_by_slug(slug)
    if not subject:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    count_result = await session.execute(
        select(func.count(DocumentModel.id)).where(DocumentModel.subject_id == subject.id)
    )
    count = count_result.scalar() or 0

    return SubjectResponse(
        id=subject.id,  # type: ignore[arg-type]
        slug=subject.slug,
        name=subject.name,
        folder_path=subject.folder_path,
        is_active=subject.is_active,
        discovered_at=subject.discovered_at,
        document_count=count,
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    subject: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    repo = CatalogRepository(session)
    documents = await repo.list_documents(subject_slug=subject)
    return [
        DocumentResponse(
            id=d.id,  # type: ignore[arg-type]
            subject_id=d.subject_id,
            filename=d.filename,
            filepath=d.filepath,
            document_type=d.document_type,
            source_role=d.source_role,
            file_hash=d.file_hash,
            file_size=d.file_size,
            page_count=d.page_count,
            ingestion_status=d.ingestion_status,
            last_ingested_at=d.last_ingested_at,
        )
        for d in documents
    ]


@router.post("/discover", response_model=DiscoverResponse)
async def discover_subjects(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = CatalogRepository(session)
    use_case = DiscoverSubjectsUseCase(settings, repo)
    result = await use_case.execute()
    return DiscoverResponse(
        subjects_found=result.subjects_found,
        documents_found=result.documents_found,
        documents_new=result.documents_new,
        documents_updated=result.documents_updated,
        scanned_paths=result.scanned_paths,
        skipped_paths=result.skipped_paths,
    )


@router.get("/maintenance/status", response_model=MaintenanceStatusResponse)
async def maintenance_status(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = CatalogRepository(session)
    subjects = await repo.list_subjects()
    documents = await repo.list_documents()
    by_status = await repo.count_documents_by_status()

    return MaintenanceStatusResponse(
        subjects=len(subjects),
        documents=len(documents),
        documents_by_status=by_status,
        content_path=settings.content_path,
    )
