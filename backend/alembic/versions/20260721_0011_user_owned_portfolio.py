"""add owner fields for user portfolio data

Revision ID: 20260721_0011
Revises: 20260720_0010
Create Date: 2026-07-21 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260721_0011"
down_revision: str | None = "20260720_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OWNER_TABLES = (
    "portfolio_position",
    "holding_analysis_result",
    "investment_plan",
    "investment_plan_suggestion",
    "report_log",
    "agent_analysis_log",
)


def upgrade() -> None:
    for table_name in OWNER_TABLES:
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS owner_username VARCHAR(100)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_owner_username ON {table_name} (owner_username)")

    op.execute("ALTER TABLE portfolio_position DROP CONSTRAINT IF EXISTS uq_portfolio_position_date_symbol")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_portfolio_position_owner_date_symbol'
            ) THEN
                ALTER TABLE portfolio_position
                ADD CONSTRAINT uq_portfolio_position_owner_date_symbol
                UNIQUE (owner_username, position_date, symbol);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE portfolio_position DROP CONSTRAINT IF EXISTS uq_portfolio_position_owner_date_symbol")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_portfolio_position_date_symbol'
            ) THEN
                ALTER TABLE portfolio_position
                ADD CONSTRAINT uq_portfolio_position_date_symbol
                UNIQUE (position_date, symbol);
            END IF;
        END
        $$;
        """
    )
    for table_name in reversed(OWNER_TABLES):
        op.execute(f"DROP INDEX IF EXISTS ix_{table_name}_owner_username")
        op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS owner_username")
