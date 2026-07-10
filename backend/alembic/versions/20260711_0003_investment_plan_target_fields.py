"""investment plan target fields

Revision ID: 20260711_0003
Revises: 20260710_0002
Create Date: 2026-07-11 00:03:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260711_0003"
down_revision: Union[str, Sequence[str], None] = "20260710_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE investment_plan ADD COLUMN IF NOT EXISTS target_annual_return NUMERIC(10, 6)")
    op.execute("ALTER TABLE investment_plan ADD COLUMN IF NOT EXISTS investment_mode VARCHAR(30) NOT NULL DEFAULT 'scheduled_dca'")


def downgrade() -> None:
    op.execute("ALTER TABLE investment_plan DROP COLUMN IF EXISTS investment_mode")
    op.execute("ALTER TABLE investment_plan DROP COLUMN IF EXISTS target_annual_return")
