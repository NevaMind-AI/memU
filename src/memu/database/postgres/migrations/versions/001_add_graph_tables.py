"""Add graph tables (gm_nodes, gm_edges, gm_communities).

Revision ID: 001_add_graph
Revises:
Create Date: 2026-03-27

Uses IF NOT EXISTS to safely adopt pre-existing tables created outside Alembic.
"""

revision = "001_add_graph"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


def upgrade() -> None:
    # gm_nodes — graph knowledge nodes
    op.execute("""
        CREATE TABLE IF NOT EXISTS gm_nodes (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            validated_count INTEGER DEFAULT 1,
            source_sessions TEXT[] DEFAULT '{}',
            community_id TEXT,
            pagerank REAL DEFAULT 0,
            embedding vector,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # gm_edges — directed graph edges
    op.execute("""
        CREATE TABLE IF NOT EXISTS gm_edges (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            type TEXT NOT NULL,
            instruction TEXT NOT NULL,
            condition TEXT,
            session_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # gm_communities — LPA community aggregates
    op.execute("""
        CREATE TABLE IF NOT EXISTS gm_communities (
            id TEXT PRIMARY KEY,
            summary TEXT,
            node_count INTEGER DEFAULT 0,
            embedding vector,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # Scope column for multi-user support (added to pre-existing tables safely)
    for table in ("gm_nodes", "gm_edges", "gm_communities"):
        op.execute(f"""
            DO $$ BEGIN
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT '';
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

    # Indexes (IF NOT EXISTS for safety)
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_nodes_status ON gm_nodes (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_nodes_community ON gm_nodes (community_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_edges_from ON gm_edges (from_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_edges_to ON gm_edges (to_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_nodes__scope ON gm_nodes (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_edges__scope ON gm_edges (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gm_communities__scope ON gm_communities (user_id)")


def downgrade() -> None:
    op.drop_table("gm_communities")
    op.drop_table("gm_edges")
    op.drop_table("gm_nodes")
