# AGENTS.md

This file guides Codex and other AI coding agents when working on ETF Systematic Portfolio Platform.

The project is a real, evolving quantitative ETF research and portfolio platform. Do not treat it as a toy demo. Read the existing code and docs before changing behavior.

## 1. Project Analysis Snapshot

### Project Background

ETF Systematic Portfolio Platform is a personal ETF systematic allocation platform for medium and long-term ETF research, portfolio construction, holding analysis, investment plans, risk control, backtesting, news-assisted research, AI research reports, and deployment operations.

Current business boundary:

- The system focuses on ETF research and portfolio decision support.
- It does not connect to real brokerage accounts.
- It does not place real orders.
- It does not directly operate user funds.
- Buy, sell, rebalance, and investment plan suggestions require human confirmation.
- News and AI output are explanatory research inputs, not direct trading signals.

### Current Main Capabilities

The current codebase includes:

- ETF universe and ETF research pool management.
- ETF profile enrichment.
- Tushare-based trading calendar and ETF daily market data sync.
- Data quality checks and cleaning.
- Factor calculation and factor ranking.
- Factor research.
- ETF screening and ETF comparison.
- ETF detail page and buy-decision helper.
- Current holdings manual entry and analysis.
- Investment plan suggestions.
- Strategy management and target portfolio generation.
- Risk checks and rebalance order generation.
- Backtesting.
- Markdown reports.
- DeepSeek-powered AI ETF research.
- Data source management.
- Juhe finance news sync and local news list.
- Workflow task execution through Redis/worker.
- Docker Compose production deployment.

### Confirmed Technical Stack

Backend:

- Python 3.11 runtime in Docker.
- FastAPI.
- SQLAlchemy 2.x ORM.
- Pydantic 2.x.
- Alembic migrations.
- PostgreSQL.
- Redis.
- pandas / numpy.
- requests.
- loguru.
- APScheduler is installed, but current scheduling details must be checked before relying on it.
- pytest exists in backend requirements.

Frontend:

- Vue 3.
- TypeScript.
- Vite.
- Element Plus.
- ECharts.
- Axios.
- Vue Router.

Deployment:

- Docker Compose.
- Nginx frontend container.
- External Caddy reverse proxy in production.
- GitHub remote deployment by pulling code on server.
- Production directory currently documented as `/opt/ETFSystematicPortfolioPlatform`.

External services currently integrated:

- Tushare Pro for ETF calendar, ETF market data, ETF universe/profile-related data.
- DeepSeek for AI research summarization.
- Juhe finance news API for low-frequency finance news sync.

Potential or legacy data sources:

- AKShare remains in dependencies and some historical docs/tests, but formal data mode has been moving toward Tushare-only for ETF market/profile data to avoid mixed data口径.
- Eastmoney appears in older docs/history. Do not re-enable it without explicit design review.
- Baostock was discussed as a possible future low-cost A-share historical data backup, but is not confirmed as implemented.

## 2. Required Reading Before Work

Before non-trivial changes, read:

- `README.md`
- `docs/00_文档导航.md`
- `docs/01_项目说明.md`
- `docs/02_系统架构.md`
- `docs/03_数据库设计.md`
- `docs/04_API接口文档.md`
- `docs/09_开发日志.md`
- `docs/10_系统流程说明.md`
- Relevant module docs:
  - Strategy: `docs/05_策略设计.md`
  - Risk: `docs/06_风控设计.md`
  - Backtest: `docs/07_回测设计.md`
  - Deployment: `docs/08_部署说明.md`, `docs/11_服务器上线清单.md`
  - Analysis period: `docs/15_分析周期口径说明.md`
  - Strategy/data source management: `docs/16_策略与数据源管理说明.md`

If docs conflict with current code, inspect the code and update docs as part of the change.

## 3. Directory Structure

Root:

- `backend/`: FastAPI backend.
- `frontend/`: Vue frontend.
- `docs/`: project documentation.
- `scripts/`: operational scripts.
- `sql/`: initial SQL used when creating a fresh database volume.
- `docker-compose.yml`: local compose file.
- `compose.production.yml`: production compose variant.
- `compose.production.external-caddy.yml`: production compose variant used behind external Caddy.
- `Caddyfile`: reverse proxy config reference.
- `.env.example`, `.env.production.example`: environment templates.

Backend:

- `backend/app/main.py`: FastAPI app factory and router registration.
- `backend/app/api/`: API routers.
- `backend/app/models/`: SQLAlchemy ORM models.
- `backend/app/schemas/`: Pydantic request/response schemas.
- `backend/app/services/`: business logic and integrations.
- `backend/app/core/`: settings, database, logging, auth/security, scheduler utilities.
- `backend/app/worker.py`: workflow worker entrypoint.
- `backend/alembic/`: database migrations.
- `backend/tests/`: backend tests.

Frontend:

- `frontend/src/main.ts`: Vue app entry.
- `frontend/src/App.vue`: shell layout and sidebar navigation.
- `frontend/src/router/index.ts`: route definitions.
- `frontend/src/api/client.ts`: typed API client.
- `frontend/src/views/`: business pages.
- `frontend/src/styles.css`: global styles.
- `frontend/src/datePresets.ts`: shared analysis-period presets.

## 4. Development Goals

Primary goals:

- Build a stable ETF research and portfolio decision-support platform.
- Prefer reliable local historical data storage over repeated external calls.
- Keep all research decisions explainable and traceable.
- Keep user-facing terminology clear for non-professional users.
- Make docs detailed enough that future AI agents and the user can understand and modify the project quickly.

Near-term direction already visible in the code:

- Improve data source management.
- Expand strategy engines while preserving traceability.
- Add news/event analysis into ETF research.
- Improve AI research and report generation.
- Improve production readiness and operational observability.

Items marked as pending/uncertain:

- Real brokerage integration: not implemented; requires explicit compliance/security design.
- Automatic trading: not implemented.
- Real-time Level-2 or minute-level data: not confirmed.
- News AI summarization and scheduled news sync: not fully implemented at the time this file was created.
- Full encrypted secret management: database can store API secrets, but encryption-at-rest strategy is待确认.

## 5. Backend Development Rules

Follow the current layering:

1. API router in `backend/app/api`.
2. Pydantic schemas in `backend/app/schemas`.
3. Business logic in `backend/app/services`.
4. ORM models in `backend/app/models`.
5. Database changes through Alembic in `backend/alembic/versions`.

API rules:

- Keep routers thin.
- Validate request/response with Pydantic schemas.
- Raise `HTTPException` with clear messages for user-facing errors.
- Wrap external provider failures as controlled 4xx/5xx errors.
- Do not leak secret values in API responses.
- Register new routers in `backend/app/main.py`.
- Update `docs/04_API接口文档.md` for every new or changed API.

Service rules:

- Put provider calls and business logic in services.
- Keep external API adapters isolated.
- Normalize external payloads before inserting into database.
- Avoid business logic in Vue components or API routers.
- For long-running operations, prefer workflow/worker patterns where applicable.

Config rules:

- Runtime config comes from `backend/app/core/config.py`, environment variables, and selected database config tables.
- Never hardcode user tokens or API keys in code, docs, tests, or commits.
- Data source records may store secrets, but API responses must return only masked values.

## 6. Frontend Development Rules

Follow existing frontend patterns:

- Use Vue 3 `<script setup lang="ts">`.
- Use Element Plus for UI.
- Use ECharts for charts.
- Use `frontend/src/api/client.ts` for API access and types.
- Use `frontend/src/router/index.ts` for routes.
- Add menu entries in `frontend/src/App.vue` when adding a top-level page.
- Reuse `frontend/src/datePresets.ts` for analysis-period controls.

UX rules:

- Main app pages should be usable tools, not marketing pages.
- Keep Chinese as the main UI language, with necessary English technical labels.
- Avoid exposing unnecessary raw technical parameters to normal users.
- For historical windows, use the term `分析周期`.
- Use `日期范围` only for custom date selection.
- Do not confuse `分析周期` with future holding period or investment plan period.
- Keep side navigation stable.
- Avoid nested cards and excessive decorative UI.
- Do not put API keys or tokens in frontend state beyond a write-only form submission.

## 7. Data Processing Rules

Data source principle:

- Official ETF market/profile mode currently prioritizes Tushare.
- Unknown/new data sources must first enter `data_source_config` as metadata.
- Only sources with implemented adapters and clear field mapping should be marked `runtime_supported`.
- Do not mix multiple providers into formal cleaned market data without explicit source/field review.

Market data rules:

- Raw external data goes into raw tables where available.
- Cleaned data used by factors, strategies, backtests, and ETF detail must be normalized.
- Preserve source information.
- Avoid repeated external calls when local data exists.
- Prefer batch sync into database over frontend-triggered direct provider calls.
- Respect API rate limits and user-shared tokens.

News rules:

- Juhe finance news is integrated as `juhe_finance_news`.
- News should be synced by backend into `news_article`.
- Frontend reads local database, not Juhe directly.
- News is research context only, not a buy/sell trigger.
- AI news summarization and event impact scoring are future enhancements unless implemented in code.

AI rules:

- DeepSeek output is explanatory.
- AI must not invent market data.
- AI should summarize evidence from local data, factors, holdings, target portfolio, and news.
- AI output must not be treated as guaranteed investment advice.

## 8. Database Design Rules

Database is PostgreSQL with SQLAlchemy models and Alembic migrations.

Rules:

- Every table/field change requires an Alembic migration.
- Update `docs/03_数据库设计.md` after schema changes.
- Do not rely only on `sql/init_schema.sql` for existing deployments. It is for fresh volumes.
- Migrations must be idempotent where practical.
- Production containers run `alembic upgrade head` on startup.
- Keep model, schema, service, and docs consistent.

Important current tables include:

- `asset_master`
- `market_data_raw`
- `market_data_clean`
- `trading_calendar`
- `etf_nav_premium`
- `data_quality_log`
- `factor_daily`
- `strategy_config`
- `strategy_run`
- `alpha_signal`
- `target_portfolio`
- `portfolio_position`
- `holding_analysis_result`
- `investment_plan`
- `risk_check_result`
- `rebalance_order`
- `backtest_run`
- `report_log`
- `agent_analysis_log`
- `workflow_task`
- `asset_sync_log`
- `data_source_config`
- `news_article`

When adding JSON fields:

- Document expected shape.
- Keep frontend type definitions aligned.
- Avoid storing highly variable external payloads as the only normalized representation; preserve useful queryable columns.

## 9. Strategy Development Rules

Current strategy system:

- Strategy configuration is stored in `strategy_config`.
- Current main engine is `factor_rotation`.
- Built-in parameterized strategies include:
  - `core_etf_rotation`
  - `aggressive_equity_rotation`
  - `defensive_all_weather`
  - `global_qdii_rotation`
- Target output is written to `target_portfolio`.
- Runs are recorded in `strategy_run`.
- Signals are recorded in `alpha_signal`.

Rules:

- New parameterized strategies can be added through strategy management when they use existing engine logic.
- New algorithmic strategy engines require explicit backend implementation in `strategy_service.py` or a new service module.
- Every strategy result must be traceable to `run_id`.
- Strategy reasons should explain why a symbol was selected or excluded.
- Respect tradability constraints.
- Do not let AI directly rewrite target weights unless a clearly designed, reviewed strategy engine supports it.
- Update `docs/05_策略设计.md` when strategy logic changes.

## 10. Backtesting Rules

Current backtest implementation is in `backend/app/services/backtest_service.py`.

Rules:

- Backtests must use local cleaned historical data.
- Avoid look-ahead bias.
- Make rebalance timing explicit.
- Include fees and slippage when supported by the request.
- Persist runs, equity curves, metrics, and trades.
- Compare new strategies against simple baselines when possible.
- Update `docs/07_回测设计.md` when changing backtest logic.

Pending/confirm before claiming:

- Minute-level backtesting is not confirmed.
- Real order execution simulation beyond current backtest fields is not confirmed.

## 11. Testing and Verification

Preferred backend tests:

```bash
docker compose build api
docker compose run --rm api pytest -q
```

If local Python dependencies are installed:

```bash
python -m pytest backend/tests -q
```

Frontend build:

```bash
cd frontend
npm run build
```

Backend syntax check:

```bash
python -m compileall -q backend/app
```

Compose validation:

```bash
docker compose config -q
```

Production health check pattern:

```bash
curl -fsS http://127.0.0.1:5174/ >/dev/null
curl -fsS http://127.0.0.1:8000/health/ready -H 'Host: localhost'
```

Rules:

- Run targeted backend tests when changing service logic.
- Run frontend build when changing frontend code.
- If a test cannot run because local environment lacks dependencies, state that clearly in final notes.
- For deployment-related changes, verify container startup and health endpoints.

## 12. Documentation Rules

Every meaningful change must update docs.

At minimum:

- Add an entry at the top of `docs/09_开发日志.md`.
- Update module-specific docs:
  - API changes: `docs/04_API接口文档.md`
  - Database changes: `docs/03_数据库设计.md`
  - Strategy changes: `docs/05_策略设计.md`
  - Risk changes: `docs/06_风控设计.md`
  - Backtest changes: `docs/07_回测设计.md`
  - Workflow/user flow changes: `docs/10_系统流程说明.md`
  - Data source changes: `docs/16_策略与数据源管理说明.md`
- Update `docs/00_文档导航.md` when adding major docs.

Docs should be detailed enough that:

- The user can understand the system later.
- Another AI can quickly continue development.
- Deployment and data-source boundaries are clear.

## 13. Git and Deployment Rules

Git:

- Do not commit secrets.
- Do not commit `.env`, `.env.production`, tokens, API keys, or passwords.
- Use concise commit messages that describe the feature/fix.
- Check `git status --short` before and after work.
- Do not revert user changes unless explicitly asked.

Common deployment path:

```bash
ssh server2 "cd /opt/ETFSystematicPortfolioPlatform; git pull --ff-only; docker compose --env-file .env.production -f compose.production.external-caddy.yml up -d --build"
```

After deployment, verify:

- Frontend is reachable.
- API `/health/ready` returns ready.
- New migrations ran successfully.
- New endpoints work behind auth or by internal service checks.

If only docs changed, deployment may not be necessary, but GitHub push is still expected when the user has asked for version syncing.

## 14. Security and Secret Handling

Forbidden:

- Do not write real tokens into source files.
- Do not write real tokens into docs.
- Do not expose token plaintext in API responses.
- Do not send secrets to frontend except as write-only user input.
- Do not log full secrets.

Allowed:

- Store secrets in `.env` / `.env.production`.
- Store secrets in `data_source_config.secret_value` only through backend-controlled paths.
- Return masked secrets such as `abcd...123456`.

Current known sensitive providers:

- Tushare token.
- DeepSeek API key.
- Juhe finance news key.
- Database credentials.
- Auth session secret and admin password hash.

## 15. Prohibited or High-Risk Actions

Do not:

- Add real brokerage trading without explicit user approval and a separate compliance/security design.
- Add automatic buy/sell execution without explicit user approval.
- Treat AI output as guaranteed investment advice.
- Mix data sources into official cleaned market data without documenting source and field口径.
- Use external APIs directly from frontend for provider data.
- Burn through shared API tokens with high-frequency sync.
- Store raw unbounded external payloads without retention or size consideration.
- Change production deployment ports or reverse proxy assumptions without checking other server projects.
- Run destructive Git commands such as `git reset --hard` unless explicitly requested.
- Remove existing user work in dirty worktrees.

## 16. When Unsure

If a requirement is unclear:

- Prefer reading current code and docs first.
- Mark uncertain items as `待确认`.
- Choose conservative, reversible implementation.
- Keep data source and strategy changes traceable.
- Ask the user only when a reasonable safe assumption would be risky.

