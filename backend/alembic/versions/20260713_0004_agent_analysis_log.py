"""agent analysis log

Revision ID: 20260713_0004
Revises: 20260711_0003
Create Date: 2026-07-13 13:05:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0004"
down_revision: Union[str, Sequence[str], None] = "20260711_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_analysis_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("data_status", sa.String(length=40), nullable=False),
        sa.Column("llm_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("llm_model", sa.String(length=80), nullable=True),
        sa.Column("final_action", sa.String(length=80), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
        sa.Column("final_summary", sa.Text(), nullable=False),
        sa.Column("manager_commentary", sa.Text(), nullable=False),
        sa.Column("agents_payload", sa.JSON(), nullable=False),
        sa.Column("warnings_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_analysis_log_symbol", "agent_analysis_log", ["symbol"])
    op.create_index("ix_agent_analysis_log_created_at", "agent_analysis_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_analysis_log_created_at", table_name="agent_analysis_log")
    op.drop_index("ix_agent_analysis_log_symbol", table_name="agent_analysis_log")
    op.drop_table("agent_analysis_log")
