"""add asset sync log

Revision ID: 20260713_0006
Revises: 20260713_0005
Create Date: 2026-07-13 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0006"
down_revision: str | None = "20260713_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_sync_log (
            id SERIAL PRIMARY KEY,
            sync_type VARCHAR(50) NOT NULL,
            source VARCHAR(50) NOT NULL,
            status VARCHAR(30) NOT NULL,
            total INTEGER DEFAULT 0,
            updated INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            message TEXT,
            details JSON,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_sync_log_sync_type ON asset_sync_log (sync_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_sync_log_status ON asset_sync_log (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_sync_log_created_at ON asset_sync_log (created_at)")


def downgrade() -> None:
    op.drop_index("ix_asset_sync_log_created_at", table_name="asset_sync_log", if_exists=True)
    op.drop_index("ix_asset_sync_log_status", table_name="asset_sync_log", if_exists=True)
    op.drop_index("ix_asset_sync_log_sync_type", table_name="asset_sync_log", if_exists=True)
    op.drop_table("asset_sync_log", if_exists=True)
