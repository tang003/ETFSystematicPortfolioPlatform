"""add news article

Revision ID: 20260714_0008
Revises: 20260714_0007
Create Date: 2026-07-14 16:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260714_0008"
down_revision: str | None = "20260714_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_article (
            id BIGSERIAL PRIMARY KEY,
            source VARCHAR(80) NOT NULL,
            external_id VARCHAR(160) NOT NULL,
            title VARCHAR(500) NOT NULL,
            source_name VARCHAR(120),
            url VARCHAR(1000),
            image_url VARCHAR(1000),
            publish_time TIMESTAMP WITHOUT TIME ZONE,
            summary TEXT,
            content TEXT,
            keywords JSON DEFAULT '[]',
            related_symbols JSON DEFAULT '[]',
            related_asset_class JSON DEFAULT '[]',
            related_region JSON DEFAULT '[]',
            sentiment_score DOUBLE PRECISION,
            impact_level VARCHAR(40),
            raw_payload JSON DEFAULT '{}',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            CONSTRAINT uq_news_article_source_external_id UNIQUE (source, external_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_article_source ON news_article (source)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_article_title ON news_article (title)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_article_publish_time ON news_article (publish_time)")
    op.execute(
        """
        INSERT INTO data_source_config (
            provider_code, provider_name, provider_type, enabled, base_url, auth_type,
            request_interval_seconds, quota_per_minute, quota_per_day,
            supported_usages, adapter_status, notes
        )
        VALUES (
            'juhe_finance_news',
            '聚合数据财经新闻',
            'news',
            TRUE,
            'https://apis.juhe.cn/fapigx/caijing/query',
            'token',
            7200,
            1,
            50,
            '["news"]',
            'runtime_supported',
            '["财经新闻源，第一版用于低频同步和 ETF 关键词关联。","免费/低配额度通常较低，建议后端定时批量同步，不让前端直接请求外部接口。"]'
        )
        ON CONFLICT (provider_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_news_article_publish_time", table_name="news_article", if_exists=True)
    op.drop_index("ix_news_article_title", table_name="news_article", if_exists=True)
    op.drop_index("ix_news_article_source", table_name="news_article", if_exists=True)
    op.drop_table("news_article", if_exists=True)

