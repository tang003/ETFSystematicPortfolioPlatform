"""position broker fields

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260710_0002"
down_revision: Union[str, Sequence[str], None] = "20260710_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("portfolio_position", sa.Column("position_name", sa.String(length=100), nullable=True))
    op.add_column("portfolio_position", sa.Column("asset_type", sa.String(length=30), nullable=True))
    op.add_column("portfolio_position", sa.Column("current_price", sa.Numeric(24, 6), nullable=True))
    op.add_column("portfolio_position", sa.Column("cost_price", sa.Numeric(24, 6), nullable=True))
    op.add_column("portfolio_position", sa.Column("unrealized_pnl", sa.Numeric(24, 4), nullable=True))
    op.add_column("portfolio_position", sa.Column("unrealized_pnl_rate", sa.Numeric(10, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("portfolio_position", "unrealized_pnl_rate")
    op.drop_column("portfolio_position", "unrealized_pnl")
    op.drop_column("portfolio_position", "cost_price")
    op.drop_column("portfolio_position", "current_price")
    op.drop_column("portfolio_position", "asset_type")
    op.drop_column("portfolio_position", "position_name")
