"""current schema baseline

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10 00:01:00
"""

from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401

revision: str = "20260710_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    pass
