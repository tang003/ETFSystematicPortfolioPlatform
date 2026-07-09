INSERT INTO asset_master (
    symbol, name, exchange, asset_class, asset_region, currency,
    is_cross_border, is_leveraged, is_inverse, enabled, risk_level, description
) VALUES
('510300', '沪深300ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, 'A股大盘核心宽基 ETF'),
('510050', '上证50ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, 'A股核心蓝筹 ETF'),
('510500', '中证500ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, 'A股中盘宽基 ETF'),
('159915', '创业板ETF', 'SZ', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 5, 'A股成长风格 ETF'),
('159919', '沪深300ETF', 'SZ', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, '深市沪深300 ETF 备选'),
('159928', '消费ETF', 'SZ', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, 'A股消费行业 ETF'),
('510880', '红利ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 3, '高股息红利 ETF'),
('512170', '医疗ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 5, 'A股医疗行业 ETF'),
('512660', '军工ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 5, 'A股军工行业 ETF'),
('513100', '纳指ETF', 'SH', 'equity', 'US', 'CNY', TRUE, FALSE, FALSE, TRUE, 5, '跨境美国科技成长 ETF'),
('513500', '标普500ETF', 'SH', 'equity', 'US', 'CNY', TRUE, FALSE, FALSE, TRUE, 4, '跨境美国宽基 ETF'),
('513050', '中概互联网ETF', 'SH', 'equity', 'CN_HK_US', 'CNY', TRUE, FALSE, FALSE, TRUE, 5, '中概互联网主题 ETF'),
('159920', '恒生ETF', 'SZ', 'equity', 'HK', 'CNY', TRUE, FALSE, FALSE, TRUE, 4, '港股宽基 ETF'),
('518880', '黄金ETF', 'SH', 'gold', 'GLOBAL', 'CNY', FALSE, FALSE, FALSE, TRUE, 2, '黄金防御资产 ETF'),
('511010', '国债ETF', 'SH', 'bond', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 1, '国债防御资产 ETF'),
('511880', '银华日利ETF', 'SH', 'cash', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 1, '货币现金管理 ETF'),
('512880', '证券ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 5, 'A股券商行业 ETF'),
('512800', '银行ETF', 'SH', 'equity', 'CN', 'CNY', FALSE, FALSE, FALSE, TRUE, 4, 'A股金融行业 ETF')
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    exchange = EXCLUDED.exchange,
    asset_class = EXCLUDED.asset_class,
    asset_region = EXCLUDED.asset_region,
    currency = EXCLUDED.currency,
    is_cross_border = EXCLUDED.is_cross_border,
    is_leveraged = EXCLUDED.is_leveraged,
    is_inverse = EXCLUDED.is_inverse,
    enabled = EXCLUDED.enabled,
    risk_level = EXCLUDED.risk_level,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO strategy_config (
    strategy_code, strategy_name, version, rebalance_frequency, config, enabled
) VALUES (
    'core_etf_rotation',
    '核心 ETF 月度轮动配置策略',
    '0.1.0',
    'monthly',
    '{
      "factor_weights": {
        "trend": 0.35,
        "momentum": 0.30,
        "volatility": 0.15,
        "drawdown": 0.10,
        "liquidity": 0.05,
        "premium": 0.05
      },
      "max_single_weight": 0.50,
      "max_equity_weight": 0.80,
      "min_defense_weight": 0.20,
      "min_rebalance_diff": 0.05,
      "premium_buy_limit": 0.03,
      "premium_reduce_limit": 0.05
    }'::jsonb,
    TRUE
)
ON CONFLICT (strategy_code) DO UPDATE SET
    strategy_name = EXCLUDED.strategy_name,
    version = EXCLUDED.version,
    rebalance_frequency = EXCLUDED.rebalance_frequency,
    config = EXCLUDED.config,
    enabled = EXCLUDED.enabled,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO risk_rule (rule_code, rule_name, rule_type, threshold, config, enabled, severity) VALUES
('max_single_weight', '单一 ETF 最大仓位', 'position', 0.50000000, NULL, TRUE, 'warning'),
('max_equity_weight', '权益资产最大仓位', 'position', 0.80000000, NULL, TRUE, 'warning'),
('min_defense_weight', '防御资产最低仓位', 'position', 0.20000000, NULL, TRUE, 'warning'),
('min_cash_weight', '现金最低仓位', 'position', 0.05000000, NULL, TRUE, 'warning'),
('premium_buy_limit', '跨境 ETF 新增买入溢价限制', 'premium', 0.03000000, NULL, TRUE, 'warning')
ON CONFLICT (rule_code) DO UPDATE SET
    rule_name = EXCLUDED.rule_name,
    rule_type = EXCLUDED.rule_type,
    threshold = EXCLUDED.threshold,
    config = EXCLUDED.config,
    enabled = EXCLUDED.enabled,
    severity = EXCLUDED.severity;
