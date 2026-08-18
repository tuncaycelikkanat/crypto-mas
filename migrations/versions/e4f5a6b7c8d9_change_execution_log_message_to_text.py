"""Change execution log message column to text

Revision ID: e4f5a6b7c8d9
Revises: dbc2b9377763
Create Date: 2026-08-18 21:22:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: str | Sequence[str] | None = 'dbc2b9377763'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('execution_logs') as batch_op:
        batch_op.alter_column('message',
                   existing_type=sa.String(length=255),
                   type_=sa.Text(),
                   existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('execution_logs') as batch_op:
        batch_op.alter_column('message',
                   existing_type=sa.Text(),
                   type_=sa.String(length=255),
                   existing_nullable=False)
