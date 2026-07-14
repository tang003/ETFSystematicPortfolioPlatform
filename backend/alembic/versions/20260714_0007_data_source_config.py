"""add data source config

Revision ID: 20260714_0007
Revises: 20260713_0006
Create Date: 2026-07-14 15:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260714_0007"
down_revision: str | None = "20260713_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS data_source_config (
            id SERIAL PRIMARY KEY,
            provider_code VARCHAR(80) NOT NULL UNIQUE,
            provider_name VARCHAR(120) NOT NULL,
            provider_type VARCHAR(40) DEFAULT 'market',
            enabled BOOLEAN DEFAULT TRUE,
            base_url VARCHAR(500),
            auth_type VARCHAR(40) DEFAULT 'token',
            secret_value TEXT,
            request_interval_seconds DOUBLE PRECISION,
            quota_per_minute INTEGER,
            quota_per_day INTEGER,
            supported_usages JSON DEFAULT '[]',
            adapter_status VARCHAR(40) DEFAULT 'metadata_only',
            notes JSON DEFAULT '[]',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_source_config_provider_code ON data_source_config (provider_code)")
    op.execute(
        """
        INSERT INTO data_source_config (
            provider_code, provider_name, provider_type, enabled, base_url, auth_type,
            request_interval_seconds, quota_per_minute, supported_usages, adapter_status, notes
        )
        VALUES
            (
                'tushare', 'Tushare Pro', 'market', TRUE, 'https://api.tushare.pro', 'token',
                1.5, 40,
                '["calendar","market_daily","asset_universe","asset_profile"]',
                'runtime_supported',
                '["正式行情、交易日历和 ETF 资料默认使用该源。","Token 可由环境变量或本表密钥字段提供，前端不回显明文。"]'
            ),
            (
                'deepseek', 'DeepSeek', 'ai', TRUE, 'https://api.deepseek.com', 'bearer',
                NULL, NULL,
                '["ai_research","report_enhancement"]',
                'runtime_supported',
                '["AI 投研解释源，不直接生成行情或交易信号。","Key 可由环境变量或本表密钥字段提供，前端不回显明文。"]'
            )
        ON CONFLICT (provider_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_data_source_config_provider_code", table_name="data_source_config", if_exists=True)
    op.drop_table("data_source_config", if_exists=True)

