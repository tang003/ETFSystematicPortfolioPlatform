"""add app user

Revision ID: 20260720_0010
Revises: 20260720_0009
Create Date: 2026-07-20 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260720_0010"
down_revision: str | None = "20260720_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_user (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(300) NOT NULL,
            role VARCHAR(40) NOT NULL DEFAULT 'viewer',
            display_name VARCHAR(120),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            last_login_at TIMESTAMP WITHOUT TIME ZONE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_app_user_username ON app_user (username)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_app_user_role ON app_user (role)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_app_user_is_active ON app_user (is_active)")


def downgrade() -> None:
    op.drop_index("ix_app_user_is_active", table_name="app_user", if_exists=True)
    op.drop_index("ix_app_user_role", table_name="app_user", if_exists=True)
    op.drop_index("ix_app_user_username", table_name="app_user", if_exists=True)
    op.drop_table("app_user", if_exists=True)
