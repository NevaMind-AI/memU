"""Add relation_category column to gm_edges.

Revision ID: 002_relation_category
Revises: 001_add_graph
Create Date: 2026-03-28

Supports disentangled relation graphs (MAGMA 2026 pattern):
edges classified as semantic/temporal/causal/entity/synthesis.
"""

revision = "002_relation_category"
down_revision = "001_add_graph"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.execute("""
        ALTER TABLE gm_edges
        ADD COLUMN IF NOT EXISTS relation_category TEXT NOT NULL DEFAULT 'semantic'
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gm_edges_relation_category "
        "ON gm_edges (relation_category)"
    )


def downgrade() -> None:
    op.drop_index("ix_gm_edges_relation_category", table_name="gm_edges")
    op.drop_column("gm_edges", "relation_category")
