from __future__ import annotations

import sqlalchemy as sa
from alembic import op

try:  # Optional pgvector support
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Vector = None

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _embedding_type(context) -> sa.types.TypeEngine:
    use_vector = context.config.attributes.get("use_vector", True)
    if use_vector and Vector is not None:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        return Vector()
    return sa.ARRAY(sa.Float())


def upgrade() -> None:
    ctx = op.get_context()
    emb_type = _embedding_type(ctx)

    op.create_table(
        "resources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope_key", sa.String(), nullable=False, index=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("modality", sa.String(), nullable=False),
        sa.Column("local_path", sa.String(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("embedding", emb_type, nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
        sa.Column("updated_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
    )

    op.create_table(
        "memory_categories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope_key", sa.String(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", emb_type, nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
        sa.Column("updated_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
    )
    op.create_index(
        "idx_categories_scope_name",
        "memory_categories",
        ["scope_key", sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "memory_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope_key", sa.String(), nullable=False, index=True),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("embedding", emb_type, nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
        sa.Column("updated_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
    )

    op.create_table(
        "category_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scope_key", sa.String(), nullable=False, index=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "category_id", sa.String(), sa.ForeignKey("memory_categories.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
        sa.Column("updated_at", sa.Float(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())")),
    )
    op.create_index(
        "idx_category_items_unique",
        "category_items",
        ["scope_key", "item_id", "category_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_category_items_unique", table_name="category_items")
    op.drop_table("category_items")
    op.drop_table("memory_items")
    op.drop_index("idx_categories_scope_name", table_name="memory_categories")
    op.drop_table("memory_categories")
    op.drop_table("resources")
