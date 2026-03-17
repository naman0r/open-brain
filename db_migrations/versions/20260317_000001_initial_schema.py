"""initial schema

Revision ID: 20260317_000001
Revises:
Create Date: 2026-03-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "20260317_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("create extension if not exists vector")

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("embedding_model", sa.String(length=128), nullable=False, server_default="local-deterministic-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.create_index("ix_memories_content_hash", "memories", ["content_hash"], unique=False)
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"], unique=False)
    op.create_index("ix_memories_source", "memories", ["source"], unique=False)
    op.create_index("ix_memories_created_at", "memories", ["created_at"], unique=False)
    op.execute(
        "create index if not exists ix_memories_embedding_cosine "
        "on memories using ivfflat (embedding vector_cosine_ops) with (lists = 100)"
    )

    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_entities_name", "entities", ["name"], unique=False)

    op.create_table(
        "memory_entity_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("memory_id", "entity_id", name="uq_memory_entity_link"),
    )
    op.create_index("ix_memory_entity_links_memory_id", "memory_entity_links", ["memory_id"], unique=False)
    op.create_index("ix_memory_entity_links_entity_id", "memory_entity_links", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_memory_entity_links_entity_id", table_name="memory_entity_links")
    op.drop_index("ix_memory_entity_links_memory_id", table_name="memory_entity_links")
    op.drop_table("memory_entity_links")
    op.drop_index("ix_entities_name", table_name="entities")
    op.drop_table("entities")
    op.execute("drop index if exists ix_memories_embedding_cosine")
    op.drop_index("ix_memories_created_at", table_name="memories")
    op.drop_index("ix_memories_source", table_name="memories")
    op.drop_index("ix_memories_memory_type", table_name="memories")
    op.drop_index("ix_memories_content_hash", table_name="memories")
    op.drop_table("memories")

