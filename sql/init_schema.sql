CREATE TABLE IF NOT EXISTS asset_master (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    exchange VARCHAR(20),
    asset_class VARCHAR(30) NOT NULL,
    asset_region VARCHAR(30),
    currency VARCHAR(10) DEFAULT 'CNY',
    is_cross_border BOOLEAN DEFAULT FALSE,
    is_leveraged BOOLEAN DEFAULT FALSE,
    is_inverse BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    risk_level INTEGER DEFAULT 3,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_data_raw (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(18, 6),
    high NUMERIC(18, 6),
    low NUMERIC(18, 6),
    close NUMERIC(18, 6),
    volume NUMERIC(24, 4),
    amount NUMERIC(24, 4),
    source VARCHAR(50) NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trade_date, source)
);

CREATE TABLE IF NOT EXISTS market_data_clean (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(18, 6),
    high NUMERIC(18, 6),
    low NUMERIC(18, 6),
    close NUMERIC(18, 6),
    volume NUMERIC(24, 4),
    amount NUMERIC(24, 4),
    is_adjusted BOOLEAN DEFAULT FALSE,
    data_status VARCHAR(30) DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS etf_nav_premium (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    trade_date DATE NOT NULL,
    nav NUMERIC(18, 6),
    market_price NUMERIC(18, 6),
    premium_rate NUMERIC(18, 6),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS trading_calendar (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    market VARCHAR(20) DEFAULT 'CN',
    is_open BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32),
    trade_date DATE,
    check_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL,
    message TEXT,
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS factor_daily (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    trade_date DATE NOT NULL,
    ma20 NUMERIC(18, 6),
    ma60 NUMERIC(18, 6),
    ma120 NUMERIC(18, 6),
    ma200 NUMERIC(18, 6),
    ret_20d NUMERIC(18, 8),
    ret_60d NUMERIC(18, 8),
    ret_120d NUMERIC(18, 8),
    ret_250d NUMERIC(18, 8),
    volatility_60d NUMERIC(18, 8),
    volatility_120d NUMERIC(18, 8),
    drawdown_120d NUMERIC(18, 8),
    drawdown_250d NUMERIC(18, 8),
    liquidity_20d NUMERIC(24, 4),
    premium_rate NUMERIC(18, 8),
    trend_score NUMERIC(10, 4),
    momentum_score NUMERIC(10, 4),
    volatility_score NUMERIC(10, 4),
    drawdown_score NUMERIC(10, 4),
    liquidity_score NUMERIC(10, 4),
    premium_score NUMERIC(10, 4),
    alpha_score NUMERIC(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS strategy_config (
    id SERIAL PRIMARY KEY,
    strategy_code VARCHAR(100) NOT NULL UNIQUE,
    strategy_name VARCHAR(100) NOT NULL,
    version VARCHAR(30) NOT NULL,
    rebalance_frequency VARCHAR(30) DEFAULT 'monthly',
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_run (
    id BIGSERIAL PRIMARY KEY,
    strategy_code VARCHAR(100) NOT NULL,
    strategy_version VARCHAR(30),
    run_date DATE NOT NULL,
    run_type VARCHAR(30) DEFAULT 'scheduled',
    status VARCHAR(30) DEFAULT 'success',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alpha_signal (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    symbol VARCHAR(32) NOT NULL,
    signal_date DATE NOT NULL,
    alpha_score NUMERIC(10, 4),
    rank_no INTEGER,
    confidence NUMERIC(10, 4),
    signal_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS target_portfolio (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    portfolio_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    raw_target_weight NUMERIC(10, 6),
    final_target_weight NUMERIC(10, 6),
    asset_class VARCHAR(30),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_position (
    id BIGSERIAL PRIMARY KEY,
    position_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    quantity NUMERIC(24, 6),
    market_value NUMERIC(24, 4),
    weight NUMERIC(10, 6),
    cost_basis NUMERIC(24, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(position_date, symbol)
);

CREATE TABLE IF NOT EXISTS risk_rule (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(100) NOT NULL UNIQUE,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50),
    threshold NUMERIC(18, 8),
    config JSONB,
    enabled BOOLEAN DEFAULT TRUE,
    severity VARCHAR(20) DEFAULT 'warning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_check_result (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    check_date DATE NOT NULL,
    rule_code VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL,
    message TEXT,
    before_value NUMERIC(18, 8),
    after_value NUMERIC(18, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rebalance_order (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    order_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    action VARCHAR(20) NOT NULL,
    current_weight NUMERIC(10, 6),
    target_weight NUMERIC(10, 6),
    weight_diff NUMERIC(10, 6),
    estimated_amount NUMERIC(24, 4),
    reason TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_run (
    id BIGSERIAL PRIMARY KEY,
    strategy_code VARCHAR(100) NOT NULL,
    strategy_version VARCHAR(30),
    name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    initial_cash NUMERIC(24, 4),
    monthly_contribution NUMERIC(24, 4),
    fee_rate NUMERIC(10, 8),
    slippage_rate NUMERIC(10, 8),
    config JSONB,
    status VARCHAR(30) DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_equity_curve (
    id BIGSERIAL PRIMARY KEY,
    backtest_id BIGINT REFERENCES backtest_run(id),
    trade_date DATE NOT NULL,
    total_equity NUMERIC(24, 4),
    cash NUMERIC(24, 4),
    drawdown NUMERIC(18, 8),
    daily_return NUMERIC(18, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_trade (
    id BIGSERIAL PRIMARY KEY,
    backtest_id BIGINT REFERENCES backtest_run(id),
    trade_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    action VARCHAR(20) NOT NULL,
    price NUMERIC(18, 6),
    quantity NUMERIC(24, 6),
    amount NUMERIC(24, 4),
    fee NUMERIC(24, 4),
    slippage NUMERIC(24, 4),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_metrics (
    id BIGSERIAL PRIMARY KEY,
    backtest_id BIGINT REFERENCES backtest_run(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(24, 8),
    metric_unit VARCHAR(20),
    sort_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_attribution (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    attribution_date DATE NOT NULL,
    period_type VARCHAR(30) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    symbol VARCHAR(32),
    asset_class VARCHAR(30),
    contribution_return NUMERIC(18, 8),
    contribution_amount NUMERIC(24, 4),
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_log (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES strategy_run(id),
    report_date DATE NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    file_path VARCHAR(500),
    content_markdown TEXT,
    status VARCHAR(30) DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asset_master_enabled ON asset_master(enabled);
CREATE INDEX IF NOT EXISTS idx_market_data_raw_symbol_date ON market_data_raw(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_market_data_clean_symbol_date ON market_data_clean(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_factor_daily_symbol_date ON factor_daily(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_strategy_run_date ON strategy_run(run_date);
CREATE INDEX IF NOT EXISTS idx_rebalance_order_date ON rebalance_order(order_date);

