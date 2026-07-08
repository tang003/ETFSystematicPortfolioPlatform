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

- `POST /api/market/sync`
- `POST /api/data-quality/check`
- `POST /api/factors/calculate`
- `POST /api/strategies/run`
- `POST /api/portfolio/generate-target`
- `POST /api/risk/check`
- `POST /api/rebalance/generate`
- `POST /api/backtest/run`
- `POST /api/reports/monthly`

