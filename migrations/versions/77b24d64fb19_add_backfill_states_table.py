"""Add backfill_states table

Revision ID: 77b24d64fb19
Revises: c0f629902c01
Create Date: 2026-07-04 18:57:43.487927

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '77b24d64fb19'
down_revision: str | Sequence[str] | None = 'c0f629902c01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'backfill_states',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exchange', sa.String(length=32), nullable=False),
        sa.Column('symbol', sa.String(length=64), nullable=False),
        sa.Column('timeframe', sa.String(length=16), nullable=False),
        sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exchange', 'symbol', 'timeframe', name='uq_backfill_state')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('backfill_states')
