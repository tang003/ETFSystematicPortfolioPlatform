"""position broker fields

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10 00:02:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260710_0002"
down_revision: Union[str, Sequence[str], None] = "20260710_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS position_name VARCHAR(100)")
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS asset_type VARCHAR(30)")
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS current_price NUMERIC(24, 6)")
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS cost_price NUMERIC(24, 6)")
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS unrealized_pnl NUMERIC(24, 4)")
    op.execute("ALTER TABLE portfolio_position ADD COLUMN IF NOT EXISTS unrealized_pnl_rate NUMERIC(10, 6)")


def downgrade() -> None:
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS unrealized_pnl_rate")
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS unrealized_pnl")
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS cost_price")
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS current_price")
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS asset_type")
    op.execute("ALTER TABLE portfolio_position DROP COLUMN IF EXISTS position_name")
