# 04 API 接口文档

当前版本：`v0.28.0-holdings-dialog-editor`

## 认证约定

服务器设置 `AUTH_ENABLED=true` 后，除 `/health` 和 `/api/auth/*` 外的全部 API 都需要登录。登录成功后服务端写入 HttpOnly Cookie，前端浏览器会自动携带，不需要把 Token 保存到 JavaScript 或 localStorage。

### GET /api/auth/status

返回鉴权是否启用、服务器是否配置完整以及当前会话是否已登录。

### POST /api/auth/login

```json
{
  "username": "admin",
  "password": "your-password"
}
```

连续失败达到限制后返回 HTTP 429。用户名或密码错误返回 HTTP 401。

### POST /api/auth/logout

删除当前登录 Cookie。退出后再次访问业务 API 将返回 HTTP 401。

## GET /health

用途：健康检查，同时验证数据库连接可用。

请求参数：无

响应示例：

```json
{
  "status": "ok",
  "service": "ETF Systematic Portfolio Platform",
  "environment": "local"
}
```

错误示例：

如果数据库不可用，接口会返回 `500 Internal Server Error`，需要检查 PostgreSQL 容器状态和 `.env` 数据库配置。

## GET /health/live

用途：进程存活检查，不访问数据库，适合判断容器进程是否仍在响应。

## GET /health/ready

用途：生产就绪检查。会验证数据库连接；当 `WORKFLOW_EXECUTION_MODE=worker` 时，还会验证 Redis 中是否存在 worker 心跳。生产 Compose 的 API healthcheck 使用该接口。

## GET /api/assets

用途：查询 ETF 主数据列表。

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| enabled | boolean | 否 | 按启用状态筛选，省略则返回全部 |

请求示例：

```bash
curl "http://localhost:8000/api/assets?enabled=true"
```

响应示例：

```json
[
  {
    "symbol": "510300",
    "name": "沪深300ETF",
    "exchange": "SH",
    "asset_class": "equity",
    "asset_region": "CN",
    "currency": "CNY",
    "is_cross_border": false,
    "is_leveraged": false,
    "is_inverse": false,
    "enabled": true,
    "risk_level": 4,
    "description": "A股大盘核心宽基 ETF",
    "created_at": "2026-07-08T00:00:00",
    "updated_at": "2026-07-08T00:00:00"
  }
]
```

说明：

- 当前内置种子数据是用于快速启动和验证流程的样本池，不等于全市场 ETF 清单。
- 如需扩展 ETF 池，可使用下方批量导入接口。

## POST /api/assets/batch-upsert

用途：批量新增或更新 ETF 主数据池。适合后续扩展完整 ETF 池、修正名称、补充风险等级和分类。

请求示例：

```json
{
  "items": [
    {
      "symbol": "510050",
      "name": "上证50ETF",
      "exchange": "SH",
      "asset_class": "equity",
      "asset_region": "CN",
      "currency": "CNY",
      "enabled": true,
      "risk_level": 4,
      "description": "A股核心蓝筹 ETF"
    }
  ]
}
```

响应示例：

```json
{
  "total": 1,
  "inserted_or_updated": 1
}
```

## PATCH /api/assets/{symbol}

用途：更新单只 ETF 主数据的研究状态或基础属性。当前前端主要用它来控制“启用 / 停用研究池”。

请求示例：

```json
{
  "enabled": false
}
```

响应：返回更新后的 ETF 主数据对象。

后续计划接口：

- `POST /api/factors/calculate`
- `POST /api/strategies/run`
- `POST /api/portfolio/generate-target`
- `POST /api/risk/check`
- `POST /api/rebalance/generate`
- `POST /api/backtest/run`
- `POST /api/reports/monthly`

## POST /api/market/sync

用途：同步 ETF 日线行情，写入 `market_data_raw`，并可同步写入 `market_data_clean` 和数据质量日志。

请求示例：

```json
{
  "symbols": ["510300"],
  "start_date": "2025-07-08",
  "end_date": "2026-07-08",
  "source": "akshare",
  "clean_after_sync": true,
  "max_symbols": 5,
  "request_interval_seconds": 0.5
}
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbols | string[] | 否 | ETF 代码列表；为空时同步全部启用 ETF |
| start_date | date | 否 | 开始日期，默认近一年 |
| end_date | date | 否 | 结束日期，默认今天 |
| source | string | 否 | 数据源，支持 `akshare`、`eastmoney`、`tushare`，默认 `akshare` |
| incremental | boolean | 否 | 是否按增量模式只补最新缺口，默认 `false` |
| clean_after_sync | boolean | 否 | 是否同步写入 clean 表并执行质量检查 |
| max_symbols | integer | 否 | 本次最多同步多少只 ETF，适合批量同步时分批执行 |
| request_interval_seconds | number | 否 | 每只 ETF 同步之间等待秒数，降低上游压力 |

响应示例：

```json
{
  "start_date": "2025-07-08",
  "end_date": "2026-07-08",
  "source": "akshare",
  "request_interval_seconds": 0.5,
  "total_symbols": 1,
  "requested_symbols": 1,
  "skipped_symbols": 0,
  "success_count": 1,
  "failed_count": 0,
  "total_raw_rows": 240,
  "total_clean_rows": 240,
  "total_quality_logs": 1,
  "results": [
    {
      "symbol": "510300",
      "raw_rows": 240,
      "clean_rows": 240,
      "quality_logs": 1,
      "status": "success",
      "message": null
    }
  ]
}
```

如果 AKShare 或上游数据源暂时不可用，接口会对单个 symbol 返回 `failed`，并把错误写入 `data_quality_log`。

当前实现中：

- `source=akshare`：先调用 AKShare；若失败，会自动 fallback 到东方财富 K 线 HTTP 接口。
- `source=eastmoney`：只使用东方财富备用源。
- `source=tushare`：调用 Tushare `fund_daily` 接口，需要在 `.env` 中配置 `TUSHARE_TOKEN`。
- `incremental=true`：系统会先检查当前 ETF 已存的最新日期，只补后续缺口；如果已经同步到 `end_date`，则返回 `up_to_date`。

注意：

- 共享 Tushare 账号建议显式传较小的 `max_symbols`，并设置 `request_interval_seconds`，避免短时间内过多请求。
- 如果 Tushare 返回权限不足，接口会保留单个 ETF 的失败原因，不会自动高频重试。

## GET /api/market/raw

用途：查询 raw 行情。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbol | string | 否 | ETF 代码 |
| limit | integer | 否 | 返回条数，默认 100，最大 1000 |

## GET /api/market/clean

用途：查询 clean 行情。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbol | string | 是 | ETF 代码 |
| start_date | date | 否 | 开始日期 |
| end_date | date | 否 | 结束日期 |

## GET /api/market/bars/{symbol}

用途：查询单只 ETF 的 clean 日线行情。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbol | string | 是 | ETF 代码，位于路径中 |
| start_date | date | 否 | 开始日期 |
| end_date | date | 否 | 结束日期 |

## POST /api/data-quality/check

用途：对已存在的 clean 行情重新执行质量检查。

请求示例：

```json
{
  "symbols": ["510300"],
  "start_date": "2025-07-08",
  "end_date": "2026-07-08"
}
```

## GET /api/data-quality/logs

用途：查询数据质量日志。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbol | string | 否 | ETF 代码 |
| limit | integer | 否 | 返回条数，默认 100，最大 1000 |

## GET /api/data-quality/status

用途：查询数据质量整体状态。

## POST /api/calendar/sync

用途：同步 A 股交易日历，写入 `trading_calendar`。

请求示例：

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "market": "CN",
  "source": "tushare"
}
```

响应示例：

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "market": "CN",
  "source": "tushare_trade_cal",
  "open_days": 242
}
```

请求参数补充：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| start_date | date | 是 | 开始日期 |
| end_date | date | 是 | 结束日期 |
| market | string | 否 | 市场，默认 `CN` |
| source | string | 否 | 数据源，支持 `akshare`、`tushare`、`weekday`，默认 `akshare` |
| incremental | boolean | 否 | 是否按增量模式只补最新缺口，默认 `false` |

说明：

- `source=tushare`：使用 Tushare `trade_cal`，适合正式交易日历同步。
- `source=akshare`：优先调用 AKShare；失败时使用 `weekday_fallback`。
- `source=weekday`：直接使用周一到周五，仅适合本地开发验证。
- `incremental=true`：系统会先看 `trading_calendar` 里该市场的最新交易日，只补后续缺口。

## GET /api/calendar/trading-days

用途：查询交易日历。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| start_date | date | 是 | 开始日期 |
| end_date | date | 是 | 结束日期 |
| market | string | 否 | 市场，默认 `CN` |

## POST /api/factors/calculate

用途：基于 `market_data_clean` 计算因子并写入 `factor_daily`。

请求示例：

```json
{
  "symbols": ["510300"],
  "start_date": "2026-07-01",
  "end_date": "2026-07-08"
}
```

响应示例：

```json
{
  "total_symbols": 1,
  "success_count": 1,
  "failed_count": 0,
  "total_factor_rows": 6,
  "results": [
    {
      "symbol": "510300",
      "factor_rows": 6,
      "status": "success",
      "message": null
    }
  ]
}
```

## GET /api/factors/{symbol}

用途：查询单只 ETF 的因子历史。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbol | string | 是 | ETF 代码，位于路径中 |
| limit | integer | 否 | 返回条数，默认 100，最大 1000 |

## GET /api/factors/ranking

用途：查询最近一个因子日期或指定日期的 ETF 综合评分排名。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| trade_date | date | 否 | 指定因子日期 |
| limit | integer | 否 | 返回条数，默认 50 |

## POST /api/factors/research

用途：运行因子研究，计算 IC、Rank IC、因子相关性和分组未来收益。

请求示例：

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-07-09",
  "forward_days": 20,
  "quantiles": 3
}
```

响应字段：

- `ic_metrics`：每个因子的平均 IC、平均 Rank IC、IC 为正比例和有效性判断。
- `correlations`：因子两两相关性矩阵。
- `quantile_returns`：按因子值分组后的平均未来收益。

## GET /api/strategies

用途：查询策略配置。

## POST /api/strategies/run

用途：运行策略，基于指定日期或最新日期的 `factor_daily.alpha_score` 生成 Alpha 信号和目标组合。

请求示例：

```json
{
  "strategy_code": "core_etf_rotation",
  "run_date": "2026-07-08",
  "run_type": "manual"
}
```

响应示例：

```json
{
  "run_id": 1,
  "strategy_code": "core_etf_rotation",
  "strategy_version": "0.1.0",
  "run_date": "2026-07-08",
  "signal_count": 1,
  "target_count": 3,
  "status": "success"
}
```

当前版本生成的是风控前目标组合，`raw_target_weight` 和 `final_target_weight` 暂时相同。后续阶段会由独立风控引擎修正 `final_target_weight`。

## GET /api/strategies/latest-signals

用途：查询最近一次策略运行生成的 Alpha 信号。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| limit | integer | 否 | 返回条数，默认 100 |

## GET /api/portfolio/target

用途：查询最近一次策略运行生成的目标组合。

## POST /api/portfolio/positions

用途：保存用户当前 ETF 持仓快照。用户最少只需提交代码、持仓数量和成本价；系统会根据资产主表补全名称/类型，根据最新清洗行情补全现价，并按本次快照总市值自动计算每只 ETF 的当前权重。

请求示例：

```json
{
  "position_date": "2026-07-09",
  "positions": [
    {
      "symbol": "513050",
      "quantity": 1700,
      "cost_price": 1.151
    },
    {
      "symbol": "000519",
      "quantity": 100,
      "cost_price": 23.34
    }
  ]
}
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| position_date | date | 是 | 持仓快照日期 |
| positions | array | 是 | 持仓列表，可包含 ETF、场内基金、股票或其他资产 |
| positions[].symbol | string | 是 | 证券代码 |
| positions[].position_name | string | 否 | 持仓名称；通常不需要传，系统会按代码从资产主表补全 |
| positions[].asset_type | string | 否 | 资产类型：`etf`、`stock`、`cash`、`other`；通常不需要传，系统会按代码推断 |
| positions[].quantity | number | 是 | 持有份额 |
| positions[].current_price | number | 否 | 当前价格；通常不需要传，系统会使用最新清洗行情收盘价 |
| positions[].cost_price | number | 是 | 成本价格；与数量一起自动计算持仓成本 |
| positions[].market_value | number | 否 | 当前市值；兼容旧录入方式 |
| positions[].cost_basis | number | 否 | 持仓成本；兼容旧录入方式 |

响应：返回保存后的持仓列表，包含系统计算出的 `market_value`、`cost_basis`、`unrealized_pnl`、`unrealized_pnl_rate` 和 `weight`。

如果某个代码不存在资产主表，或没有已清洗行情价格，接口会返回 400，并提示需要先同步资产或行情。

## GET /api/portfolio/positions

用途：查询最近一次持仓快照。

## POST /api/portfolio/positions/resolve

用途：根据代码批量预览持仓补全结果，供前端在保存前展示名称、类型、最新价格和价格日期。

请求示例：

```json
{
  "symbols": ["513050", "159928"]
}
```

响应示例：

```json
[
  {
    "symbol": "513050",
    "position_name": "中概互联",
    "asset_type": "etf",
    "current_price": 1.092,
    "price_date": "2026-07-09",
    "resolved": true,
    "message": null
  }
]
```

## POST /api/portfolio/holdings/analyze

用途：把当前持仓与目标组合做对比，生成持仓建议。建议动作包括：

- `ADD`：当前权重明显低于目标权重，建议加仓。
- `REDUCE`：当前权重明显高于目标权重，建议减仓。
- `HOLD`：当前权重接近目标权重，建议持有。
- `REDUCE_OR_EXIT`：当前持有但目标组合不再配置，建议减仓或退出。

请求示例：

```json
{
  "run_id": 1,
  "analysis_date": "2026-07-09"
}
```

响应示例：

```json
[
  {
    "run_id": 1,
    "analysis_date": "2026-07-09",
    "symbol": "510300",
    "current_weight": "0.600000",
    "target_weight": "0.400000",
    "weight_diff": "-0.200000",
    "action_suggestion": "REDUCE",
    "alpha_score": "44.4887",
    "reason": "当前权重高于目标权重 20.00%，建议考虑减仓；alpha_score=44.4887",
    "created_at": "2026-07-09T10:00:00"
  }
]
```

## GET /api/portfolio/holdings/analysis

用途：查询最近一次持仓分析结果。

## POST /api/portfolio/investment-plans

用途：创建定投计划。系统只保存计划和生成建议，不会扣款，不会下单。

请求示例：

```json
{
  "plan_name": "核心 ETF 月定投",
  "run_id": 5,
  "start_date": "2026-07-09",
  "months": 12,
  "monthly_amount": 3000,
  "note": "每月固定投入，优先补足低配 ETF"
}
```

响应：返回计划详情，包含 `id`、`total_budget` 和状态。

## GET /api/portfolio/investment-plans

用途：查询最近创建的定投计划。

## POST /api/portfolio/investment-plans/{plan_id}/analyze

用途：为某个定投计划生成某一期的投入建议。当前算法会优先把本期定投资金分配给“目标权重大于当前权重”的 ETF，并按权重缺口比例分配；如果没有低配资产，则按目标权重分配。

请求示例：

```json
{
  "period_no": 1,
  "suggestion_date": "2026-07-09"
}
```

响应示例：

```json
[
  {
    "plan_id": 1,
    "run_id": 5,
    "suggestion_date": "2026-07-09",
    "period_no": 1,
    "symbol": "511010",
    "target_weight": "0.250000",
    "current_weight": "0.000000",
    "gap_weight": "0.250000",
    "suggested_amount": "3000.0000",
    "action_suggestion": "INVEST",
    "reason": "511010 当前权重低于目标权重，优先分配本期定投资金 3000.0000 元。",
    "created_at": "2026-07-09T10:00:00"
  }
]
```

## GET /api/portfolio/investment-plans/{plan_id}/suggestions

用途：查询某个定投计划已经生成的投入建议。

## POST /api/risk/check

用途：对指定策略运行的目标组合执行独立风控检查，修正 `target_portfolio.final_target_weight`，并写入 `risk_check_result`。

请求示例：

```json
{
  "run_id": 1
}
```

响应示例：

```json
{
  "run_id": 1,
  "check_date": "2026-07-08",
  "result_count": 1,
  "adjusted_count": 0,
  "status": "success"
}
```

## GET /api/risk/results

用途：查询风控检查结果。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| run_id | integer | 否 | 策略运行 ID |
| limit | integer | 否 | 返回条数，默认 100 |

## POST /api/rebalance/generate

用途：根据风控后的目标组合生成调仓建议单。

请求示例：

```json
{
  "run_id": 1,
  "portfolio_value": 100000
}
```

如果已经通过 `/api/portfolio/positions` 保存当前持仓，系统会使用持仓快照中的真实 `current_weight` 计算差额和建议金额；如果没有持仓快照，则当前权重按 0 处理。

## GET /api/rebalance/orders

用途：查询调仓建议单。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| run_id | integer | 否 | 策略运行 ID |
| limit | integer | 否 | 返回条数，默认 100 |

## POST /api/backtest/run

用途：运行回测。当前支持两种模式：

- `equal_weight_buy_and_hold`：等权买入持有基线回测。
- `core_etf_rotation_monthly`：策略月度调仓回测，每月第一个可交易日根据最近 Alpha 排名生成目标权重并调仓。

请求示例：

```json
{
  "strategy_code": "equal_weight_buy_and_hold",
  "name": "510300 baseline",
  "symbols": ["510300"],
  "start_date": "2026-07-01",
  "end_date": "2026-07-08",
  "initial_cash": 10000,
  "monthly_contribution": 2000,
  "fee_rate": 0.001,
  "slippage_rate": 0.001
}
```

策略月度调仓示例：

```json
{
  "strategy_code": "core_etf_rotation_monthly",
  "name": "core rotation monthly",
  "symbols": ["510300", "510500", "159915", "511010", "511880"],
  "start_date": "2026-01-01",
  "end_date": "2026-07-09",
  "initial_cash": 100000,
  "monthly_contribution": 3000,
  "fee_rate": 0.001,
  "slippage_rate": 0.001
}
```

## GET /api/backtest/runs

用途：查询回测运行记录。

## GET /api/backtest/{backtest_id}

用途：查询单个回测运行配置。

## GET /api/backtest/{backtest_id}/equity-curve

用途：查询回测净值曲线。

## GET /api/backtest/{backtest_id}/trades

用途：查询回测交易记录。

## GET /api/backtest/{backtest_id}/metrics

用途：查询回测绩效指标。

## POST /api/reports/monthly

用途：生成月度调仓 Markdown 报告，并保存到 `report_log`。

请求示例：

```json
{
  "run_id": 1,
  "report_date": "2026-07-08"
}
```

如果不传 `run_id`，默认使用最近一次策略运行。

## GET /api/reports

用途：查询报告列表。

## GET /api/reports/{report_id}

用途：查询单份报告详情，包括 `content_markdown`。

## POST /api/workflows/run

用途：创建后台全流程任务，由后端异步串联交易日历、行情、数据质量、因子、策略、风控、调仓和报告步骤。

请求示例：

```json
{
  "symbols": ["510300", "159915"],
  "start_date": "2026-01-01",
  "end_date": "2026-07-09",
  "max_symbols": 5,
  "calendar_source": "tushare",
  "market_source": "tushare",
  "incremental_sync": true,
  "request_interval_seconds": 1.5,
  "strict_data_validation": true,
  "minimum_history_bars": 200,
  "strategy_code": "core_etf_rotation",
  "portfolio_value": 100000,
  "generate_report": true
}
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbols | string[] | 否 | ETF 代码列表；为空时使用全部启用 ETF |
| start_date | date | 是 | 开始日期 |
| end_date | date | 是 | 结束日期 |
| max_symbols | integer | 否 | 本次后台任务最多同步多少只 ETF |
| calendar_source | string | 否 | 日历源，支持 `tushare`、`akshare`、`weekday` |
| market_source | string | 否 | 行情源，支持 `tushare`、`akshare`、`eastmoney` |
| incremental_sync | boolean | 否 | 是否按增量模式同步交易日历和行情，默认 `true` |
| request_interval_seconds | number | 否 | 每只 ETF 同步之间等待秒数，Tushare 建议 `1.5` 或更高 |
| strict_data_validation | boolean | 否 | 严格数据门禁，默认 `true`；任一标的失败或不新鲜时停止后续建议生成 |
| minimum_history_bars | integer | 否 | 每只 ETF 最少历史日线数量，默认 `200`，范围 20~1000 |
| strategy_code | string | 否 | 策略代码，默认 `core_etf_rotation` |
| portfolio_value | number | 否 | 组合市值，用于生成调仓建议金额 |
| generate_report | boolean | 否 | 是否在流程末尾生成月度报告 |

说明：

- `calendar_source` 和 `market_source` 允许前端控制真实数据源与备用数据源。
- 使用共享 Tushare 账号时，建议同时控制 `max_symbols` 和 `request_interval_seconds`。
- 全流程会先固定本次 ETF 范围，行情、质量检查和因子计算始终使用同一批代码。
- 严格门禁会检查批量失败数量、最近交易日和历史样本数；失败详情保存在对应任务步骤的 `result_payload` 中，可补齐数据后重试。
