"""track the active embedding space

Revision ID: 20260901_0002
Revises: 20260703_0001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0002"
down_revision: str | Sequence[str] | None = "20260703_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memu_embedding_space",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identity", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_memu_embedding_space_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("memu_embedding_space")
