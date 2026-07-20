"""add audit log

Revision ID: 20260720_0009
Revises: 20260714_0008
Create Date: 2026-07-20 09:40:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260720_0009"
down_revision: str | None = "20260714_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id BIGSERIAL PRIMARY KEY,
            actor_username VARCHAR(100),
            actor_role VARCHAR(40),
            method VARCHAR(12) NOT NULL,
            path VARCHAR(500) NOT NULL,
            action VARCHAR(120) NOT NULL,
            status_code INTEGER,
            duration_ms INTEGER,
            client_ip VARCHAR(80),
            request_id VARCHAR(80),
            detail JSON,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_actor_username ON audit_log (actor_username)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_actor_role ON audit_log (actor_role)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_path ON audit_log (path)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_request_id ON audit_log (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log (created_at)")


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at", table_name="audit_log", if_exists=True)
    op.drop_index("ix_audit_log_request_id", table_name="audit_log", if_exists=True)
    op.drop_index("ix_audit_log_action", table_name="audit_log", if_exists=True)
    op.drop_index("ix_audit_log_path", table_name="audit_log", if_exists=True)
    op.drop_index("ix_audit_log_actor_role", table_name="audit_log", if_exists=True)
    op.drop_index("ix_audit_log_actor_username", table_name="audit_log", if_exists=True)
    op.drop_table("audit_log", if_exists=True)
