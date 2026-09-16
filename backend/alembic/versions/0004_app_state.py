"""app state with initialized flag

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initialized", sa.Boolean(), nullable=False),
        sa.Column("initialized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="app_state_single_row"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO app_state (id, initialized, initialized_at)
        SELECT 1,
               EXISTS (SELECT 1 FROM users),
               CASE WHEN EXISTS (SELECT 1 FROM users) THEN CURRENT_TIMESTAMP END
        """
    )


def downgrade() -> None:
    op.drop_table("app_state")
