"""usernames for login

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

users = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("email", sa.String),
    sa.column("username", sa.String),
)


def _derive(email: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())[:28] or "user"
    if len(base) < 3:
        base = f"{base}user"
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    bind = op.get_bind()
    taken: set[str] = set()
    for user_id, email in bind.execute(sa.select(users.c.id, users.c.email).order_by(users.c.id)):
        bind.execute(
            users.update().where(users.c.id == user_id).values(username=_derive(email, taken))
        )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("username", existing_type=sa.String(length=32), nullable=False)
        batch.create_index(op.f("ix_users_username"), ["username"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index(op.f("ix_users_username"))
        batch.drop_column("username")
