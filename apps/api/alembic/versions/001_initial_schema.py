"""Initial schema: subjects, documents, chunks, embeddings, user profile."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "subjects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("folder_path", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), default={}),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    document_type = sa.Enum(
        "OFFICIAL_SYLLABUS", "FLASHCARDS", "LECTURE_NOTES", "EXAM_GUIDE",
        name="document_type",
    )
    source_role = sa.Enum("DOCTRINE", "EXAM_PATTERN_ONLY", name="source_role")

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("filepath", sa.String(1024), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("source_role", source_role, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger()),
        sa.Column("page_count", sa.Integer()),
        sa.Column("ingestion_status", sa.String(32), default="pending"),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filepath"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id", ondelete="CASCADE")),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_normalized", sa.Text()),
        sa.Column("chapter", sa.String(512)),
        sa.Column("section", sa.String(512)),
        sa.Column("heading_path", sa.dialects.postgresql.JSONB()),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("chunk_type", sa.String(64)),
        sa.Column("token_count", sa.Integer()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("fts_vector", sa.dialects.postgresql.TSVECTOR()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index"),
    )

    op.create_table(
        "user_profile",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(255), default="Estudiante"),
        sa.Column("pin_hash", sa.String(255)),
        sa.Column("preferences", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("stats", sa.dialects.postgresql.JSONB()),
        sa.Column("errors", sa.dialects.postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", Vector(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "model"),
    )

    op.execute(
        "CREATE INDEX idx_chunks_fts ON document_chunks USING GIN(fts_vector)"
    )
    op.execute(
        "CREATE INDEX idx_embeddings_hnsw ON embeddings USING hnsw (vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("embeddings")
    op.drop_table("ingestion_runs")
    op.drop_table("user_profile")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("subjects")
    op.execute("DROP TYPE IF EXISTS document_type")
    op.execute("DROP TYPE IF EXISTS source_role")
