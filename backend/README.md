# Backend

FastAPI 后端服务，负责 API、数据库访问、外部数据源适配、量化投研服务、任务调度入口和 AI 投研编排。

## 技术栈

- Python 3.11
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- pandas / numpy
- requests
- pytest

## 模块职责

| 目录 | 说明 |
| --- | --- |
| `app/api` | API 路由层，处理请求、响应和 HTTP 异常 |
| `app/services` | ETF 数据、行情、因子、策略、风控、回测、报告、AI 投研等业务逻辑 |
| `app/models` | SQLAlchemy ORM 模型 |
| `app/schemas` | Pydantic 请求和响应模型 |
| `app/core` | 配置、数据库、日志、认证、安全和调度工具 |
| `alembic` | 数据库迁移 |
| `tests` | 后端测试 |

## 核心后端能力

- Tushare ETF 主数据、交易日历、日线行情、基金净值和基金份额同步。
- `market_data_raw` / `market_data_clean` 双层行情数据模型。
- 数据质量检查、缺失行情补齐计划和后台任务。
- 因子计算、ETF 轮动策略、目标组合生成。
- 当前持仓、定投计划、风控检查、调仓建议和回测。
- DeepSeek 多 Agent ETF 投研总结。
- 用户登录、角色权限、操作审计和敏感参数脱敏。
- Redis worker 后台任务和每日维护。

## 本地开发

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认读取项目根目录或当前目录下的 `.env`。

## 常用验证

```bash
python -m compileall -q app
python -m pytest tests -q
```

也可以在项目根目录通过 Docker Compose 运行：

```bash
docker compose build api
docker compose run --rm api pytest -q
```
