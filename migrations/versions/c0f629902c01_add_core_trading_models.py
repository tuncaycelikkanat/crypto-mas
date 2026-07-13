"""Add core trading models

Revision ID: c0f629902c01
Revises: 79d3ef2a0e4b
Create Date: 2026-07-04 18:47:58.985462

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c0f629902c01'
down_revision: str | Sequence[str] | None = '79d3ef2a0e4b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'trading_cycles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_name', sa.String(length=64), nullable=False),
        sa.Column('exchange', sa.String(length=32), nullable=False),
        sa.Column('timeframe', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('trigger', sa.String(length=16), nullable=False),
        sa.Column('symbols_processed', sa.Integer(), nullable=False),
        sa.Column('decisions_made', sa.Integer(), nullable=False),
        sa.Column('trades_executed', sa.Integer(), nullable=False),
        sa.Column('starting_equity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('ending_equity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('cycle_pnl', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_name', sa.String(length=64), nullable=False),
        sa.Column('exchange', sa.String(length=32), nullable=False),
        sa.Column('symbol', sa.String(length=64), nullable=False),
        sa.Column('side', sa.String(length=16), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('notional', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('cycle_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cycle_id'], ['trading_cycles.id'], ),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_name', sa.String(length=64), nullable=False),
        sa.Column('exchange', sa.String(length=32), nullable=False),
        sa.Column('symbol', sa.String(length=64), nullable=False),
        sa.Column('side', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('requested_quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('filled_quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('requested_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('filled_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('trade_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'execution_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_name', sa.String(length=64), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.String(length=16), nullable=False),
        sa.Column('stage', sa.String(length=32), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['cycle_id'], ['trading_cycles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('execution_logs')
    op.drop_table('orders')
    op.drop_table('trades')
    op.drop_table('trading_cycles')
