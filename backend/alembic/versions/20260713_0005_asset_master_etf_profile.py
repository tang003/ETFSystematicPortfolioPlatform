"""asset master etf profile fields

Revision ID: 20260713_0005
Revises: 20260713_0004
Create Date: 2026-07-13 13:30:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260713_0005"
down_revision: Union[str, Sequence[str], None] = "20260713_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS fund_company VARCHAR(100)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS tracking_index VARCHAR(100)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS listing_date DATE")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS fund_size NUMERIC(24, 4)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS management_fee NUMERIC(10, 6)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS custody_fee NUMERIC(10, 6)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS expense_ratio NUMERIC(10, 6)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS tracking_error NUMERIC(10, 6)")
    op.execute("ALTER TABLE asset_master ADD COLUMN IF NOT EXISTS latest_premium_rate NUMERIC(10, 6)")


def downgrade() -> None:
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS latest_premium_rate")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS tracking_error")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS expense_ratio")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS custody_fee")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS management_fee")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS fund_size")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS listing_date")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS tracking_index")
    op.execute("ALTER TABLE asset_master DROP COLUMN IF EXISTS fund_company")
