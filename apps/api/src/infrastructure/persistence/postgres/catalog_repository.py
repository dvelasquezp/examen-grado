"""Repositorio de catálogo (materias y documentos)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog.document import Document
from src.domain.catalog.enums import DocumentType, IngestionStatus, SourceRole
from src.domain.catalog.subject import Subject
from src.infrastructure.persistence.postgres.models import DocumentModel, SubjectModel


class CatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_subject(self, subject: Subject) -> Subject:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == subject.slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = subject.name
            existing.folder_path = subject.folder_path
            existing.is_active = subject.is_active
            model = existing
        else:
            model = SubjectModel(
                slug=subject.slug,
                name=subject.name,
                folder_path=subject.folder_path,
                is_active=subject.is_active,
                metadata_=subject.metadata,
            )
            self.session.add(model)

        await self.session.flush()
        return Subject(
            id=model.id,
            slug=model.slug,
            name=model.name,
            folder_path=model.folder_path,
            is_active=model.is_active,
            discovered_at=model.discovered_at,
            metadata=model.metadata_ or {},
        )

    async def get_subject_by_slug(self, slug: str) -> Subject | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return Subject(
            id=model.id,
            slug=model.slug,
            name=model.name,
            folder_path=model.folder_path,
            is_active=model.is_active,
            discovered_at=model.discovered_at,
            metadata=model.metadata_ or {},
        )

    async def list_subjects(self) -> list[Subject]:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.is_active.is_(True)).order_by(SubjectModel.name)
        )
        return [
            Subject(
                id=m.id,
                slug=m.slug,
                name=m.name,
                folder_path=m.folder_path,
                is_active=m.is_active,
                discovered_at=m.discovered_at,
                metadata=m.metadata_ or {},
            )
            for m in result.scalars().all()
        ]

    async def upsert_document(self, document: Document, subject_id: UUID | None) -> Document:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.filepath == document.filepath)
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.file_hash != document.file_hash:
                existing.file_hash = document.file_hash
                existing.file_size = document.file_size
                existing.ingestion_status = IngestionStatus.PENDING
            existing.filename = document.filename
            existing.document_type = document.document_type
            existing.source_role = document.source_role
            existing.subject_id = subject_id
            model = existing
        else:
            model = DocumentModel(
                subject_id=subject_id,
                filename=document.filename,
                filepath=document.filepath,
                document_type=document.document_type,
                source_role=document.source_role,
                file_hash=document.file_hash,
                file_size=document.file_size,
                page_count=document.page_count,
                ingestion_status=document.ingestion_status,
                metadata_=document.metadata,
            )
            self.session.add(model)

        await self.session.flush()
        return Document(
            id=model.id,
            subject_id=model.subject_id,
            filename=model.filename,
            filepath=model.filepath,
            document_type=DocumentType(model.document_type),
            source_role=SourceRole(model.source_role),
            file_hash=model.file_hash,
            file_size=model.file_size,
            page_count=model.page_count,
            ingestion_status=IngestionStatus(model.ingestion_status),
            last_ingested_at=model.last_ingested_at,
            metadata=model.metadata_ or {},
        )

    async def list_documents(self, subject_slug: str | None = None) -> list[Document]:
        query = select(DocumentModel).order_by(DocumentModel.filename)
        if subject_slug:
            subj_result = await self.session.execute(
                select(SubjectModel).where(SubjectModel.slug == subject_slug)
            )
            subject = subj_result.scalar_one_or_none()
            if subject:
                query = query.where(DocumentModel.subject_id == subject.id)

        result = await self.session.execute(query)
        return [
            Document(
                id=m.id,
                subject_id=m.subject_id,
                filename=m.filename,
                filepath=m.filepath,
                document_type=DocumentType(m.document_type),
                source_role=SourceRole(m.source_role),
                file_hash=m.file_hash,
                file_size=m.file_size,
                page_count=m.page_count,
                ingestion_status=IngestionStatus(m.ingestion_status),
                last_ingested_at=m.last_ingested_at,
                metadata=m.metadata_ or {},
            )
            for m in result.scalars().all()
        ]

    async def count_documents_by_status(self) -> dict[str, int]:
        result = await self.session.execute(select(DocumentModel))
        counts: dict[str, int] = {}
        for doc in result.scalars().all():
            counts[doc.ingestion_status] = counts.get(doc.ingestion_status, 0) + 1
        return counts
