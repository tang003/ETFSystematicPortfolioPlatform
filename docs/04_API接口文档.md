# 04 API 接口文档

当前版本：`v0.46.0-etf-universe-tushare-fallback`

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

### POST /api/assets/batch-upsert

批量导入或更新 ETF 主数据。

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

- 支持 `auto`、`eastmoney`、`tushare`、`akshare`。
- `auto` 会先尝试东方财富分页源，失败后切换 Tushare `fund_basic`，最后再尝试 AKShare。
- Tushare 兜底只同步 ETF 档案基础信息，不同步历史行情，通常只消耗一次基础资料查询。
- 同步进来的 ETF 默认不启用研究。
- 该接口只同步 ETF 档案列表，不同步历史行情。
- 外部源失败时不会清空本地已有 ETF 池。

### POST /api/assets/sync-profiles

按 ETF 代码批量补全主资料。

请求：

```json
{
  "source": "akshare",
  "symbols": ["510300", "159915"],
  "limit": 100,
  "preserve_existing": true
}
```

返回：

```json
{
  "source": "akshare",
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

- 当前只支持 `akshare`，不消耗 Tushare token。
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
  "source": "akshare",
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
  "end_date": "2026-07-13"
}
```

返回包含：

- 收益
- 年化波动
- 最大回撤
- 日均成交额
- 可交易性评分
- 标准化净值曲线
- 相关性矩阵

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
- 返回 `alternatives` 同指数 ETF 候选，用于比较同跟踪指数下的规模、费率、交易性和替代优先级。

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
