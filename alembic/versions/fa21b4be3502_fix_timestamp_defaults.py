"""fix timestamp defaults

Revision ID: fa21b4be3502
Revises: 37ddb741055d
Create Date: 2026-10-07 16:18:53.656950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa21b4be3502'
down_revision: Union[str, Sequence[str], None] = '37ddb741055d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )

    op.alter_column(
        "groups",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )

    op.alter_column(
        "expenses",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )

    op.alter_column(
        "settlements",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )


def downgrade() -> None:
    op.alter_column("users", "created_at", server_default=None)
    op.alter_column("groups", "created_at", server_default=None)
    op.alter_column("expenses", "created_at", server_default=None)
    op.alter_column("settlements", "created_at", server_default=None)