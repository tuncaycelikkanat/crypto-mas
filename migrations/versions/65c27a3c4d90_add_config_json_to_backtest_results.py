"""add config_json to backtest_results

Revision ID: 65c27a3c4d90
Revises: 20260714_indexes
Create Date: 2026-07-14 17:15:59.402178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '65c27a3c4d90'
down_revision: Union[str, Sequence[str], None] = '20260714_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtest_results', sa.Column('config_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('backtest_results', 'config_json')
