"""Add performance indexes for feature_snapshots and candles.

Revision ID: 20260714_indexes
Revises: b10a044a6543
Create Date: 2026-07-14
"""
from alembic import op

# revision identifiers
revision = "20260714_indexes"
down_revision = "b10a044a6543"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for feature_snapshots lookups (most common query pattern)
    op.create_index(
        "idx_feature_snapshots_lookup",
        "feature_snapshots",
        ["exchange", "symbol", "timeframe", "timestamp"],
        postgresql_ops={"timestamp": "DESC"},
    )

    # Composite index for candles lookups
    op.create_index(
        "idx_candles_lookup",
        "candles",
        ["exchange", "symbol", "timeframe", "open_time"],
        postgresql_ops={"open_time": "DESC"},
    )

    # Index for positions (hot path: open position lookup)
    op.create_index(
        "idx_positions_open_lookup",
        "positions",
        ["account_name", "exchange", "symbol", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_feature_snapshots_lookup", table_name="feature_snapshots")
    op.drop_index("idx_candles_lookup", table_name="candles")
    op.drop_index("idx_positions_open_lookup", table_name="positions")
