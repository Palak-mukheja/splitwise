"""add timestamp defaults

Revision ID: 37ddb741055d
Revises: e9db480655e2
Create Date: 2026-10-07 16:04:46.854178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37ddb741055d'
down_revision: Union[str, Sequence[str], None] = 'e9db480655e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS created_at
        TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP
        NOT NULL
    """)

    op.execute("""
        ALTER TABLE groups
        ADD COLUMN IF NOT EXISTS created_at
        TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP
        NOT NULL
    """)

    op.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS created_at
        TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP
        NOT NULL
    """)

    op.execute("""
        ALTER TABLE settlements
        ADD COLUMN IF NOT EXISTS created_at
        TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP
        NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("settlements", "created_at")
    op.drop_column("expenses", "created_at")
    op.drop_column("groups", "created_at")
    op.drop_column("users", "created_at")
