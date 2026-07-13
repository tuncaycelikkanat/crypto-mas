"""add_sl_tp_mode_to_positions

Revision ID: b10a044a6543
Revises: 77b24d64fb19
Create Date: 2026-07-05 01:01:43.053362

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b10a044a6543'
down_revision: str | Sequence[str] | None = '77b24d64fb19'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add stop_loss_price, take_profit_price, strategy_mode and close_reason to positions."""
    op.add_column('positions', sa.Column('stop_loss_price', sa.Numeric(20, 8), nullable=True))
    op.add_column('positions', sa.Column('take_profit_price', sa.Numeric(20, 8), nullable=True))
    op.add_column('positions', sa.Column('strategy_mode', sa.String(32), nullable=True))
    op.add_column('positions', sa.Column('close_reason', sa.String(64), nullable=True))


def downgrade() -> None:
    """Remove SL/TP/mode/close_reason columns from positions."""
    op.drop_column('positions', 'close_reason')
    op.drop_column('positions', 'strategy_mode')
    op.drop_column('positions', 'take_profit_price')
    op.drop_column('positions', 'stop_loss_price')
