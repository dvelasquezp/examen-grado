"""Modelos SQLAlchemy — conceptos."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.postgres.models import Base


class ConceptModel(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("subject_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text)
    simple_explanation: Mapped[str | None] = mapped_column(Text)
    subtopic: Mapped[str | None] = mapped_column(String(512))
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=3)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    exam_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True)
    neo4j_node_id: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    definitions: Mapped[list["ConceptDefinitionModel"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class ConceptDefinitionModel(Base):
    __tablename__ = "concept_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source_type: Mapped[str] = mapped_column(String(32), default="EXTRACTED")
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_chunks.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    concept: Mapped[ConceptModel] = relationship(back_populates="definitions")


class ConceptChunkLinkModel(Base):
    __tablename__ = "concept_chunk_links"
    __table_args__ = (UniqueConstraint("concept_id", "chunk_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    match_type: Mapped[str] = mapped_column(String(32), default="TITLE_MENTION")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    excerpt: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
