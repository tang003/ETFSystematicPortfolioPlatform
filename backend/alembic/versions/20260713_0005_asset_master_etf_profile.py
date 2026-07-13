"""asset master etf profile fields

Revision ID: 20260713_0005
Revises: 20260713_0004
Create Date: 2026-07-13 13:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0005"
down_revision: Union[str, Sequence[str], None] = "20260713_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset_master", sa.Column("fund_company", sa.String(length=100), nullable=True))
    op.add_column("asset_master", sa.Column("tracking_index", sa.String(length=100), nullable=True))
    op.add_column("asset_master", sa.Column("listing_date", sa.Date(), nullable=True))
    op.add_column("asset_master", sa.Column("fund_size", sa.Numeric(24, 4), nullable=True))
    op.add_column("asset_master", sa.Column("management_fee", sa.Numeric(10, 6), nullable=True))
    op.add_column("asset_master", sa.Column("custody_fee", sa.Numeric(10, 6), nullable=True))
    op.add_column("asset_master", sa.Column("expense_ratio", sa.Numeric(10, 6), nullable=True))
    op.add_column("asset_master", sa.Column("tracking_error", sa.Numeric(10, 6), nullable=True))
    op.add_column("asset_master", sa.Column("latest_premium_rate", sa.Numeric(10, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_master", "latest_premium_rate")
    op.drop_column("asset_master", "tracking_error")
    op.drop_column("asset_master", "expense_ratio")
    op.drop_column("asset_master", "custody_fee")
    op.drop_column("asset_master", "management_fee")
    op.drop_column("asset_master", "fund_size")
    op.drop_column("asset_master", "listing_date")
    op.drop_column("asset_master", "tracking_index")
    op.drop_column("asset_master", "fund_company")
