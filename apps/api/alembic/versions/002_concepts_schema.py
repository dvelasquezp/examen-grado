"""Migración: tablas de conceptos."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_concepts"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("definition", sa.Text()),
        sa.Column("simple_explanation", sa.Text()),
        sa.Column("subtopic", sa.String(512)),
        sa.Column("difficulty", sa.SmallInteger(), default=3),
        sa.Column("importance_score", sa.Float(), default=0.5),
        sa.Column("exam_frequency", sa.Float(), default=0.0),
        sa.Column("confidence_score", sa.Float(), default=0.0),
        sa.Column("is_canonical", sa.Boolean(), default=True),
        sa.Column("neo4j_node_id", sa.String(128)),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "slug"),
    )
    op.create_index("idx_concepts_subject", "concepts", ["subject_id"])
    op.create_index("idx_concepts_title", "concepts", ["title"])

    op.create_table(
        "concept_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), default=False),
        sa.Column("source_type", sa.String(32), default="EXTRACTED"),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id")),
        sa.Column("page_number", sa.Integer()),
        sa.Column("chunk_id", sa.UUID(), sa.ForeignKey("document_chunks.id")),
        sa.Column("confidence", sa.Float(), default=0.0),
        sa.Column("provenance", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_concept_definitions_concept", "concept_definitions", ["concept_id"])


def downgrade() -> None:
    op.drop_table("concept_definitions")
    op.drop_table("concepts")
