# 04 API 接口文档

当前版本：`v0.61.0-tushare-only-data-mode`

默认 API 前缀：`/api`

生产环境开启鉴权后，除 `/health` 和 `/api/auth/*` 外，业务 API 都需要登录。

## 健康检查

### GET /health

返回服务基础状态。

### GET /health/live

用于存活检查。

### GET /health/ready

用于就绪检查。生产环境会检查 API、数据库、worker 等关键状态。

## 鉴权

### GET /api/auth/status

返回是否启用鉴权、是否已登录。

### POST /api/auth/login

请求：

```json
{
  "username": "admin",
  "password": "password"
}
```

登录成功后服务端写入 HttpOnly Cookie。

### POST /api/auth/logout

退出登录。

## ETF 池

### GET /api/assets

查询 ETF 主数据。

可选参数：

- `enabled=true|false`
- `q`：按代码、名称、跟踪指数或基金公司模糊搜索
- `limit`：限制返回数量，最大 5000

### POST /api/assets/batch-upsert

批量导入或更新 ETF 主数据。

### POST /api/assets/seed-curated

启用后端内置精选 ETF 研究池。

说明：
- 当前内置 50 支左右 ETF，覆盖宽基、行业主题、债券、货币、黄金和 QDII。
- 如果全市场基础库已有真实资料，会优先使用数据库资料；否则使用内置保底资料。
- 该接口会把精选 ETF 设置为 `enabled=true`，使其进入研究池、行情同步、因子、策略和回测流程。

返回：
```json
{
  "total": 50,
  "inserted_or_updated": 50
}
```

### POST /api/assets/sync-universe

同步 ETF 基础池。

请求：

```json
{
  "source": "auto",
  "limit": 100
}
```

说明：

- 当前正式模式只支持 `auto`、`tushare`，且 `auto` 等同 Tushare。
- AKShare/东方财富入口已暂时停用，避免公开源字段口径污染 ETF 主数据。
- Tushare `fund_basic` 只同步 ETF 档案基础信息，不同步历史行情。
- 同步进来的 ETF 默认不启用研究。
- 该接口只同步 ETF 档案列表，不同步历史行情。
- 外部源失败时不会清空本地已有 ETF 池。

### POST /api/assets/sync-profiles

按 ETF 代码批量补全主资料。

请求：

```json
{
  "source": "auto",
  "symbols": ["510300", "159915"],
  "limit": 100,
  "preserve_existing": true
}
```

返回：

```json
{
  "source": "tushare",
  "total": 2,
  "updated": 2,
  "skipped": 0,
  "failed": 0,
  "results": [
    {
      "symbol": "510300",
      "status": "updated",
      "updated_fields": ["fund_company", "tracking_index"],
      "message": "已补全 ETF 主资料"
    }
  ]
}
```

说明：

- 当前正式模式只支持 `auto`、`tushare`，且 `auto` 等同 Tushare。
- `auto` 会优先使用 Tushare `fund_basic` 补基金公司、上市日期、管理费、托管费、业绩基准/跟踪指数，再使用 Tushare `fund_nav`、`fund_share` 补日频单位净值、基金份额和估算基金规模。
- 基金规模估算口径：`单位净值 × 基金份额 × 10000`，其中 Tushare `fund_share.fd_share` 为万份口径。
- 如果库里已有对应 ETF 的收盘行情，系统会用 `收盘价 / 单位净值 - 1` 计算日频折溢价率，并写入 `etf_nav_premium`。
- 如果 ETF 已有跟踪指数且能匹配到指数代码，系统会用 Tushare `index_daily` 补指数日线，并按 `ETF 日收益 - 指数日收益` 的年化标准差计算跟踪误差。
- 指数行情复用 `market_data_clean`，代码使用 `IDX:` 前缀，例如 `IDX:000300.SH`。
- 费率保护：单项管理费/托管费超过 2%、综合费率超过 3% 的字段不会写入，避免异常口径导致 5% 这类不合理 ETF 费率。
- `preserve_existing=true` 时只补空字段，不覆盖手工维护的数据。
- 不传 `symbols` 时按 ETF 池顺序补全，受 `limit` 限制。

### GET /api/assets/sync-logs

查询 ETF 池同步日志。

参数：

- `sync_type`：可选，例如 `profile`
- `limit`：默认 20，最大 100

返回字段：

- `sync_type`：同步类型，当前主资料补全为 `profile`
- `source`：数据源
- `status`：`success`、`partial` 或 `failed`
- `total`、`updated`、`skipped`、`failed`
- `message`
- `created_at`

### PATCH /api/assets/{symbol}

更新单只 ETF 的启用状态、风险等级或说明。

可更新字段包括：

- `enabled`
- `risk_level`
- `fund_company`
- `tracking_index`
- `listing_date`
- `fund_size`
- `management_fee`
- `custody_fee`
- `expense_ratio`
- `tracking_error`
- `latest_premium_rate`
- `description`

请求示例：

```json
{
  "fund_company": "华泰柏瑞基金",
  "tracking_index": "沪深300",
  "fund_size": 89000000000,
  "management_fee": 0.005,
  "custody_fee": 0.001,
  "expense_ratio": 0.006,
  "description": "A股核心宽基 ETF"
}
```

## 行情与数据质量

### GET /api/market/sync-plan

预览某个同步范围会同步哪些 ETF。

参数：

- `sync_scope`：`core`、`positions`、`target`、`plans`、`enabled`、`all`

### POST /api/market/sync

同步行情。

请求示例：

```json
{
  "symbols": ["510300"],
  "sync_scope": "core",
  "start_date": "2025-07-13",
  "end_date": "2026-07-13",
  "source": "tushare",
  "incremental": true,
  "clean_after_sync": true,
  "max_symbols": 30,
  "request_interval_seconds": 1.5
}
```

说明：

- 指定 `symbols` 时只同步这些代码。
- 不指定 `symbols` 时按 `sync_scope` 解析。
- 共享 Tushare token 时建议设置请求间隔和最大数量。

### POST /api/calendar/sync

同步交易日历。

### POST /api/data-quality/check

检查行情质量。

### GET /api/data-quality/status

数据质量概览。

说明：

- `total_logs`、`error_logs`、`warning_logs` 表示最近一次检查批次的统计，适合页面判断当前状态。
- `history_total_logs`、`history_error_logs`、`history_warning_logs` 表示历史累计日志，只用于排查长期数据问题。
- 每次对同一 ETF、同一区间重新检查前，会清理旧的同区间质量日志，避免重复检查导致告警数无限累加。

### GET /api/data-quality/logs

最近数据质量日志。

## ETF 对比与详情

### POST /api/etf-compare

对比多只 ETF。

请求：

```json
{
  "symbols": ["510300", "159915"],
  "start_date": "2025-07-13",
  "end_date": "2026-07-13",
  "auto_sync_missing": false,
  "max_auto_sync_symbols": 5
}
```

返回包含：

- 收益
- 年化波动
- 下行波动
- 最大回撤
- 夏普、Sortino、卡玛
- 胜率和估算缺口率
- 日均成交额
- 可交易性评分
- 买入评分和候选等级
- 标准化净值曲线
- 相关性矩阵

说明：

- `auto_sync_missing` 默认关闭；开启后会用 Tushare 尝试补齐本次对比中样本不足的少量 ETF。
- `max_auto_sync_symbols` 用于限制自动补数数量，避免共享数据源被批量消耗。

### POST /api/etf-compare/screener

批量筛选 ETF 候选，适合作为普通用户寻找“哪些 ETF 值得进一步研究”的第一入口。

请求：

```json
{
  "scope": "enabled",
  "start_date": "2023-07-13",
  "end_date": "2026-07-13",
  "limit": 50,
  "min_bars": 120,
  "min_tradability_score": 50,
  "min_buy_score": 45,
  "asset_class": "equity",
  "auto_sync_missing": false,
  "max_auto_sync_symbols": 5
}
```

字段：

- `scope`：支持 `enabled`、`core`、`positions`、`target`、`plans`、`all`、`custom`。
- `symbols`：`scope=custom` 时传入 ETF 代码列表。
- `min_bars`：最低历史样本数。
- `min_tradability_score`：最低可交易性评分。
- `min_buy_score`：最低买入评分。
- `asset_class` / `asset_region`：可选过滤。
- `auto_sync_missing`：是否对样本不足 ETF 自动补行情，默认关闭。
- `max_auto_sync_symbols`：自动补行情数量上限。

返回：

- `total_candidates`：筛选前候选数量。
- `returned`：返回数量。
- `metrics`：按买入评分、交易性、夏普和年化收益排序后的 ETF 指标。

### POST /api/etf-compare/tradability

批量计算可交易性评分。

### GET /api/etf-detail/{symbol}

查询单只 ETF 详情。

参数：

- `start_date`
- `end_date`

说明：

- 详情页默认读取本地 `market_data_clean`。
- 如果没有曲线，通常表示该区间尚未同步清洗行情。
- 返回 `decision` 买入决策摘要，包括 `action`、`score`、`confidence`、`position_hint`、`entry_plan`、`stop_loss_hint`、`reasons`、`risks` 和 `next_steps`。
- 返回 `alternatives` 同指数 ETF 候选，用于比较同跟踪指数下的规模、费率、交易性和替代优先级。
- `decision` 用于普通用户快速判断“是否值得买、适合什么仓位、风险在哪里”，不代表自动交易或收益承诺。

## 因子和策略

### POST /api/factors/calculate

计算因子。

### GET /api/factors/ranking

获取 Alpha 排名。

### POST /api/factors/research

因子研究，查看 IC、Rank IC、因子相关性、分组收益。

### POST /api/strategies/run

运行策略。

请求：

```json
{
  "strategy_code": "core_etf_rotation",
  "run_date": "2026-07-13",
  "run_type": "manual"
}
```

### GET /api/strategies

查询策略配置列表。系统会自动补齐内置策略配置。

返回字段：

- `strategy_code`
- `strategy_name`
- `version`
- `rebalance_frequency`
- `config`
- `enabled`

### POST /api/strategies

新增策略配置。

请求：

```json
{
  "strategy_code": "low_volatility_rotation",
  "strategy_name": "低波动 ETF 轮动策略",
  "version": "0.1.0",
  "rebalance_frequency": "monthly",
  "enabled": true,
  "config": {
    "engine": "factor_rotation",
    "risk_profile": "defensive",
    "target_weights": {
      "equity_primary": 0.3,
      "equity_secondary": 0.2,
      "defense": 0.35,
      "cash": 0.15
    }
  }
}
```

### PATCH /api/strategies/{strategy_code}

更新策略配置、启用状态或参数。

请求：

```json
{
  "enabled": false
}
```

### GET /api/settings/data-sources

查询数据源配置状态。该接口只返回脱敏信息，不返回 Token 明文。

返回内容包括：

- 默认日历源。
- 默认行情源。
- 默认 ETF 资料源。
- 默认 AI 源。
- Tushare 配置状态、API 地址、脱敏 Token、请求间隔。
- DeepSeek 配置状态、API 地址、脱敏 Token、模型说明。

### POST /api/settings/data-sources

新增数据源配置。新增数据源默认只是配置登记，是否能用于正式同步取决于后端是否开发了对应适配器。

请求：

```json
{
  "provider_code": "my_news_api",
  "provider_name": "自定义新闻源",
  "provider_type": "news",
  "enabled": true,
  "base_url": "https://api.example.com",
  "auth_type": "bearer",
  "secret_value": "只写入不回显",
  "request_interval_seconds": 1.5,
  "quota_per_minute": 60,
  "quota_per_day": 10000,
  "supported_usages": ["news"],
  "adapter_status": "metadata_only",
  "notes": ["仅登记配置，尚未接入业务运行时"]
}
```

### PATCH /api/settings/data-sources/{provider_code}

更新数据源配置。

请求：

```json
{
  "base_url": "http://140.143.171.60:38765",
  "secret_value": "新的 token",
  "request_interval_seconds": 0.3,
  "quota_per_minute": 500
}
```

清空数据库中保存的密钥：

```json
{
  "clear_secret": true
}
```

说明：

- `secret_value` 只允许写入或替换，接口响应不会返回明文。
- `tushare` 的数据库配置会覆盖 `TUSHARE_TOKEN` 和 `TUSHARE_API_URL`。
- `deepseek` 的数据库配置会覆盖 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL`。
- 未适配的数据源应保持 `adapter_status=metadata_only` 或 `planned`。

## 新闻资讯

### POST /api/news/sync

同步财经新闻到本地数据库。

请求：

```json
{
  "source": "juhe_finance_news",
  "num": 50,
  "page": 1
}
```

说明：

- 当前新闻适配器支持 `juhe_finance_news`。
- `num` 最大 50。
- 接口会按 `source + external_id` 去重。
- 新闻源 Key 从数据源管理的 `juhe_finance_news.secret_value` 读取，不写入代码。

### GET /api/news

查询本地新闻列表。

参数：

- `q`：按标题或摘要搜索。
- `symbol`：只看关联某只 ETF 的新闻。
- `limit`：返回数量，默认 50。

### GET /api/news/related/{symbol}

查询某只 ETF 的相关新闻。

说明：

- 第一版关联逻辑基于标题关键词、ETF 代码、ETF 名称和跟踪指数。
- 后续可以加入 AI 摘要、情绪分数和事件影响等级。

### GET /api/portfolio/target

查询最新目标组合。

## 当前持仓

### POST /api/portfolio/positions/resolve

按代码补全持仓名称、类型和现价。

请求：

```json
{
  "symbols": ["513050", "159928"],
  "auto_sync": true,
  "source": "akshare"
}
```

说明：

- `auto_sync=true` 时会尝试补全 ETF 主数据和最近行情。
- 用户通常只需要输入代码、持仓数量、成本价。

### POST /api/portfolio/positions

保存当前持仓快照。

请求：

```json
{
  "position_date": "2026-07-13",
  "positions": [
    {
      "symbol": "513050",
      "quantity": 1700,
      "cost_price": 1.151
    }
  ]
}
```

系统会计算：

- 现价
- 市值
- 成本金额
- 浮盈亏
- 权重

### GET /api/portfolio/positions

查询最新持仓快照。

### POST /api/portfolio/holdings/analyze

运行当前持仓分析。

请求：

```json
{
  "run_id": 1,
  "analysis_date": "2026-07-13"
}
```

说明：

- 需要先有目标组合。
- 如果不传 `run_id`，默认使用最新目标组合。
- 返回 `alternatives` 同指数 ETF 替代候选，用于观察是否存在规模更大、费率更低或交易性更好的同指数 ETF。
- 替代候选动态计算，不写入持仓分析表，不触发自动交易。

### GET /api/portfolio/holdings/analysis

查询最近持仓分析结果。

说明：

- 返回结构同样包含 `alternatives`。
- 页面会展示最佳同指数候选和主要原因。

### GET /api/portfolio/xray

组合暴露和策略前检查。

## 定投计划

### POST /api/portfolio/investment-plans

创建定投计划。

请求：

```json
{
  "plan_name": "一年 ETF 定投",
  "start_date": "2026-07-13",
  "months": 12,
  "total_budget": 10000,
  "target_annual_return": 0.1,
  "investment_mode": "scheduled_dca"
}
```

说明：

- `target_annual_return` 是策略目标参数，不是收益承诺。
- 当前只生成建议，不自动扣款或下单。

### GET /api/portfolio/investment-plans

查询定投计划。

### POST /api/portfolio/investment-plans/{plan_id}/analyze

生成某一期定投建议。

### GET /api/portfolio/investment-plans/{plan_id}/suggestions

查询定投建议历史。

## 风控和调仓

### POST /api/risk/check

执行风控检查。

### GET /api/risk/results

查询风控结果。

### POST /api/rebalance/generate

生成调仓建议单。

### GET /api/rebalance/orders

查询调仓建议单。

## 回测

### POST /api/backtest/run

运行回测。

### GET /api/backtest/runs

查询回测列表。

### GET /api/backtest/{id}/equity-curve

查询净值曲线。

### GET /api/backtest/{id}/metrics

查询回测指标。

### GET /api/backtest/{id}/trades

查询模拟交易记录。

## 报告

### POST /api/reports/monthly

生成月度报告。

### GET /api/reports

查询报告列表。

### GET /api/reports/{id}

查询报告详情。

## 工作流

### POST /api/workflows/run

创建全流程任务。

请求重点字段：

- `symbols`
- `start_date`
- `end_date`
- `max_symbols`
- `calendar_source`
- `market_source`
- `incremental_sync`
- `request_interval_seconds`
- `strict_data_validation`
- `minimum_history_bars`
- `strategy_code`
- `portfolio_value`
- `generate_report`

### POST /api/workflows/historical-init

创建历史行情初始化任务，适合首次部署后为精选 ETF 或指定 ETF 批量补齐长期日线行情。

请求示例：

```json
{
  "scope": "curated",
  "years": 10,
  "source": "tushare",
  "calendar_source": "tushare",
  "incremental_sync": false,
  "clean_after_sync": true,
  "request_interval_seconds": 0.2
}
```

字段：

- `scope`：同步范围，支持 `curated`、`enabled`、`core`、`positions`、`custom`。
- `symbols`：`scope=custom` 时传入 ETF 代码列表。
- `years`：默认 10 年，范围 1-15 年。
- `start_date` / `end_date`：可选；不填时按 `years` 自动推导。
- `source`：行情数据源，当前推荐 `tushare`。
- `calendar_source`：交易日历数据源，当前推荐 `tushare`。
- `incremental_sync`：是否增量同步；历史初始化默认关闭，用于完整回填目标日期区间。
- `clean_after_sync`：同步后是否自动清洗入 `market_data_clean`。
- `request_interval_seconds`：单只 ETF 请求后的等待秒数，用于控制共享 token 频率。
- `max_symbols`：可选，用于测试时限制同步数量。

说明：

- 默认 `scope=curated` 会同步后端内置精选 50 支 ETF。
- 该接口同步的是日线历史行情，不包含分钟线、实时盘口和 Level-2。
- 行情落库到 `market_data_raw` 和 `market_data_clean`，供数据健康、ETF 详情、因子、策略、回测、AI 投研使用。

### GET /api/workflows/{task_id}

查询任务详情。

### GET /api/workflows

查询最近任务。

### POST /api/workflows/{task_id}/cancel

取消任务。

### POST /api/workflows/{task_id}/retry-failed

重试失败任务。

## AI 投研

### POST /api/agent-analysis/etf

用途：运行单只 ETF 的 AI 投研委员会分析。系统会读取本地 ETF 详情、因子、当前持仓、目标组合和持仓分析结果，生成多 Agent 观点，并在配置 DeepSeek 后生成中文综合结论。

v0.44.0 起，AI 投研包含“执行替代 Agent”，并把同指数 ETF 候选作为 `same_index_alternatives` 传入 DeepSeek 上下文。

请求：

```json
{
  "symbol": "510300",
  "start_date": "2025-07-13",
  "end_date": "2026-07-13",
  "use_llm": true,
  "auto_sync": true
}
```

字段：

- `symbol`：ETF 代码，必填。
- `start_date` / `end_date`：分析区间，不填默认最近一年。
- `use_llm`：是否启用 DeepSeek 总结。
- `auto_sync`：是否在分析前自动补齐 ETF 主数据和最近行情。

返回重点：

- `final_action`：最终建议。
- `final_score`：综合评分。
- `final_summary`：最终结论。
- `manager_commentary`：复合经理说明。
- `agents`：各 Agent 的观点、证据、风险和建议。
- `warnings`：数据缺失或限制提示。

说明：

- 执行替代 Agent 只做同指数 ETF 观察，不会建议无条件换仓。
- 当前系统仍不连接券商交易，不自动下单。

### GET /api/agent-analysis/etf/history

查询最近 AI 投研记录。

参数：

- `symbol`：可选。
- `limit`：默认 20，最大 100。

示例：

```text
GET /api/agent-analysis/etf/history?symbol=510300&limit=20
```

## 安全注意

- 不要把 `TUSHARE_TOKEN`、`DEEPSEEK_API_KEY`、数据库密码写进 Git。
- 生产环境必须开启 `AUTH_ENABLED=true`。
- 当前所有交易相关接口只生成建议，不应直接调用券商交易。
