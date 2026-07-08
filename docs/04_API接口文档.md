# 04 API 接口文档

当前版本：`v0.1.0-phase1`

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

后续计划接口：

- `POST /api/factors/calculate`
- `POST /api/strategies/run`
- `POST /api/portfolio/generate-target`
- `POST /api/risk/check`
- `POST /api/rebalance/generate`
- `POST /api/backtest/run`
- `POST /api/reports/monthly`

## POST /api/market/sync

用途：从 AKShare 同步 ETF 日线行情，写入 `market_data_raw`，并可同步写入 `market_data_clean` 和数据质量日志。

请求示例：

```json
{
  "symbols": ["510300"],
  "start_date": "2025-07-08",
  "end_date": "2026-07-08",
  "source": "akshare",
  "clean_after_sync": true
}
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| symbols | string[] | 否 | ETF 代码列表；为空时同步全部启用 ETF |
| start_date | date | 否 | 开始日期，默认近一年 |
| end_date | date | 否 | 结束日期，默认今天 |
| source | string | 否 | 数据源，默认 `akshare` |
| clean_after_sync | boolean | 否 | 是否同步写入 clean 表并执行质量检查 |

响应示例：

```json
{
  "start_date": "2025-07-08",
  "end_date": "2026-07-08",
  "source": "akshare",
  "total_symbols": 1,
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

当前实现中，`source=akshare` 会先调用 AKShare；若 AKShare ETF 日线接口失败，会自动 fallback 到东方财富 K 线 HTTP 接口。也可以显式传入 `source=eastmoney` 只使用备用源。

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
  "market": "CN"
}
```

响应示例：

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "market": "CN",
  "source": "akshare_sina",
  "open_days": 242
}
```

如果 AKShare 交易日历不可用，系统会使用周一到周五作为本地 fallback，响应中的 `source` 为 `weekday_fallback`。这只适合开发验证，正式数据质量检查应优先使用真实交易日历。

## GET /api/calendar/trading-days

用途：查询交易日历。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| start_date | date | 是 | 开始日期 |
| end_date | date | 是 | 结束日期 |
| market | string | 否 | 市场，默认 `CN` |
