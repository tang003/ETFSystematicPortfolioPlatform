# AGENTS.md

本文件用于指导 Codex 或其他 AI 编程助手继续开发 ETF Systematic Portfolio Platform。

这是一个持续迭代中的量化 ETF 投研和资产配置项目，不是一次性演示项目。修改代码前必须先阅读现有代码和文档，不能凭空假设系统能力。

## 1. 项目背景

ETF Systematic Portfolio Platform 是一个面向个人用户的 ETF 系统化资产配置平台，用于中长期 ETF 投研、组合构建、持仓分析、定投计划、风险控制、回测复盘、新闻辅助研究、AI 投研报告和部署运维。

当前业务边界：

- 系统聚焦 ETF 投研和组合决策辅助。
- 当前不连接真实券商账户。
- 当前不自动下单。
- 当前不直接操作用户资金。
- 所有买入、卖出、调仓、定投建议都需要用户人工确认。
- 新闻和 AI 输出只作为投研解释材料，不是直接交易信号。

## 2. 当前已确认能力

当前代码中已经包含：

- ETF 基础池和研究池管理。
- ETF 主资料补全。
- 基于 Tushare 的交易日历和 ETF 日线行情同步。
- 数据质量检查和行情清洗。
- 因子计算和因子排名。
- 因子研究。
- ETF 筛选和 ETF 对比。
- ETF 详情页和买入决策辅助。
- 当前持仓手动录入和持仓分析。
- 定投计划建议。
- 策略管理和目标组合生成。
- 风控检查和调仓建议单。
- 回测。
- Markdown 报告。
- DeepSeek 驱动的 AI ETF 投研。
- 数据源管理。
- 聚合数据财经新闻同步和本地新闻列表。
- Redis / worker 后台任务执行。
- Docker Compose 生产部署。

## 3. 已确认技术栈

后端：

- Python 3.11 Docker 运行环境。
- FastAPI。
- SQLAlchemy 2.x ORM。
- Pydantic 2.x。
- Alembic 数据库迁移。
- PostgreSQL。
- Redis。
- pandas / numpy。
- requests。
- loguru。
- APScheduler 已安装，但具体调度使用方式需要看代码后确认。
- pytest 存在于后端依赖中。

前端：

- Vue 3。
- TypeScript。
- Vite。
- Element Plus。
- ECharts。
- Axios。
- Vue Router。

部署：

- Docker Compose。
- Nginx 前端容器。
- 生产环境使用外部 Caddy 反向代理。
- 服务器通过 GitHub 拉取代码部署。
- 当前生产目录文档记录为 `/opt/ETFSystematicPortfolioPlatform`。

当前已接入外部服务：

- Tushare Pro：ETF 交易日历、ETF 行情、ETF 基础池和 ETF 资料相关数据。
- DeepSeek：AI 投研总结和解释。
- 聚合数据财经新闻：低频财经新闻同步。

潜在或历史数据源：

- AKShare 仍在依赖和部分历史测试/文档中出现，但正式 ETF 行情和资料模式正在转向 Tushare-only，避免多源口径混用。
- Eastmoney 出现在历史文档中，未经明确设计评审不要重新启用。
- Baostock 曾被讨论为未来 A 股历史行情备用源，但当前未确认已实现。

## 4. 修改前必读文档

非简单修改前必须阅读：

- `README.md`
- `docs/00_文档导航.md`
- `docs/01_项目说明.md`
- `docs/02_系统架构.md`
- `docs/03_数据库设计.md`
- `docs/04_API接口文档.md`
- `docs/09_开发日志.md`
- `docs/10_系统流程说明.md`

按任务补充阅读：

- 策略：`docs/05_策略设计.md`
- 风控：`docs/06_风控设计.md`
- 回测：`docs/07_回测设计.md`
- 部署：`docs/08_部署说明.md`、`docs/11_服务器上线清单.md`
- 分析周期：`docs/15_分析周期口径说明.md`
- 策略和数据源管理：`docs/16_策略与数据源管理说明.md`

如果文档和当前代码冲突，以当前代码为准，并在本次修改中同步修正文档。

## 5. 目录结构说明

根目录：

- `backend/`：FastAPI 后端。
- `frontend/`：Vue 前端。
- `docs/`：项目文档。
- `scripts/`：运维脚本。
- `sql/`：新数据库 volume 首次初始化 SQL。
- `docker-compose.yml`：本地 Docker Compose。
- `compose.production.yml`：生产 Compose 变体。
- `compose.production.external-caddy.yml`：外部 Caddy 反代下的生产 Compose。
- `Caddyfile`：反向代理配置参考。
- `.env.example`、`.env.production.example`：环境变量模板。

后端：

- `backend/app/main.py`：FastAPI 应用工厂和路由注册。
- `backend/app/api/`：API 路由。
- `backend/app/models/`：SQLAlchemy ORM 模型。
- `backend/app/schemas/`：Pydantic 请求和响应模型。
- `backend/app/services/`：业务逻辑和外部服务适配。
- `backend/app/core/`：配置、数据库、日志、认证安全、调度相关工具。
- `backend/app/worker.py`：后台 worker 入口。
- `backend/alembic/`：数据库迁移。
- `backend/tests/`：后端测试。

前端：

- `frontend/src/main.ts`：Vue 应用入口。
- `frontend/src/App.vue`：整体布局和左侧菜单。
- `frontend/src/router/index.ts`：路由定义。
- `frontend/src/api/client.ts`：前端 API 客户端和类型定义。
- `frontend/src/views/`：业务页面。
- `frontend/src/styles.css`：全局样式。
- `frontend/src/datePresets.ts`：统一分析周期选项。

## 6. 开发目标

主要目标：

- 构建稳定的 ETF 投研和组合决策辅助平台。
- 优先使用本地历史数据，减少重复外部接口调用。
- 保持所有投研建议可解释、可追溯。
- 面向普通用户保持概念清晰。
- 文档必须详细，方便用户或后续 AI 快速接手。

当前可见的近期方向：

- 完善数据源管理。
- 扩展策略引擎。
- 将新闻和事件分析接入 ETF 投研。
- 提升 AI 投研和报告质量。
- 提升生产可用性和运维可观测性。

待确认或未实现：

- 真实券商接入：未实现，需要独立合规和安全设计。
- 自动交易：未实现。
- 分钟级或实时 Level-2 数据：未确认。
- 新闻 AI 摘要和定时新闻同步：当前不是完整能力，需看代码确认。
- 密钥完整加密存储方案：待确认。

## 7. 后端开发规范

遵循现有分层：

1. API 路由放在 `backend/app/api`。
2. Pydantic schema 放在 `backend/app/schemas`。
3. 业务逻辑放在 `backend/app/services`。
4. ORM 模型放在 `backend/app/models`。
5. 数据库变化必须通过 `backend/alembic/versions` 迁移。

API 规范：

- Router 保持轻量。
- 请求和响应必须使用 Pydantic schema。
- 面向用户的错误使用清晰的 `HTTPException`。
- 外部数据源错误必须被包装成受控的 4xx / 5xx。
- API 响应不得泄漏密钥明文。
- 新增路由必须在 `backend/app/main.py` 注册。
- 新增或修改 API 必须更新 `docs/04_API接口文档.md`。

Service 规范：

- 外部 API 调用和业务逻辑放在 service 层。
- 外部数据源适配器要隔离。
- 外部 payload 入库前必须标准化。
- 不要把业务逻辑写进 Vue 组件或 API router。
- 长任务优先考虑 workflow / worker 模式。

配置规范：

- 运行时配置来自 `backend/app/core/config.py`、环境变量和部分数据库配置表。
- 不得在代码、文档、测试和提交中硬编码真实 token 或 key。
- `data_source_config` 可以保存密钥，但 API 只能返回脱敏值。

## 8. 前端开发规范

遵循现有模式：

- 使用 Vue 3 `<script setup lang="ts">`。
- UI 使用 Element Plus。
- 图表使用 ECharts。
- API 请求和类型统一写在 `frontend/src/api/client.ts`。
- 路由写在 `frontend/src/router/index.ts`。
- 顶层页面需要在 `frontend/src/App.vue` 增加菜单入口。
- 分析周期控件优先复用 `frontend/src/datePresets.ts`。

交互规范：

- 主应用页面应该是可用工具，不做营销页。
- UI 主语言使用中文，必要技术字段保留英文。
- 不要把普通用户不需要理解的原始参数暴露出来。
- 历史回看窗口统一叫 `分析周期`。
- 只有自定义日期时才使用 `日期范围`。
- 不要混淆 `分析周期`、未来持有周期和定投周期。
- 左侧菜单保持稳定。
- 避免卡片套卡片和过度装饰。
- API key / token 只能作为写入型表单提交，不应在前端长期保存或回显。

## 9. 数据处理规范

数据源原则：

- ETF 正式行情和资料当前优先使用 Tushare。
- 新数据源先进入 `data_source_config` 登记。
- 只有完成字段映射和业务适配的数据源才能标记为 `runtime_supported`。
- 不要在未评审的情况下把多个数据源混入正式清洗行情。

行情数据规范：

- 外部原始数据尽量保留来源。
- 策略、因子、回测、ETF 详情优先使用清洗后的本地行情。
- 避免本地已有数据时重复调用外部接口。
- 优先后端批量同步入库，不要前端直接调用外部数据商。
- 尊重接口限频和共享 token 使用成本。

新闻数据规范：

- 聚合财经新闻源代码为 `juhe_finance_news`。
- 新闻应由后端同步入 `news_article`。
- 前端读取本地数据库，不直接请求聚合数据。
- 新闻只作为研究上下文，不是买卖信号。
- AI 新闻摘要、情绪分数和事件影响评分属于后续增强，是否已实现必须看代码确认。

AI 规范：

- DeepSeek 输出用于解释和总结。
- AI 不得编造行情数据。
- AI 应基于本地行情、因子、持仓、目标组合、新闻等证据总结。
- AI 输出不能作为收益保证或确定性投资建议。

## 10. 数据库设计规范

数据库为 PostgreSQL，使用 SQLAlchemy 模型和 Alembic 迁移。

规则：

- 表结构或字段变化必须新增 Alembic 迁移。
- 修改表结构后必须更新 `docs/03_数据库设计.md`。
- 不要只修改 `sql/init_schema.sql` 来影响已部署数据库；该 SQL 主要用于新 volume 初始化。
- 迁移尽量写成可重复执行或具备兼容性。
- 生产容器启动时会执行 `alembic upgrade head`。
- model、schema、service、docs 必须保持一致。

当前重要表包括：

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

JSON 字段规范：

- 必须在文档中说明预期结构。
- 前端类型定义要同步。
- 不要只保存难以查询的 raw payload；关键字段应拆成可查询列。

## 11. 策略开发规范

当前策略系统：

- 策略配置保存在 `strategy_config`。
- 当前主引擎是 `factor_rotation`。
- 内置参数型策略包括：
  - `core_etf_rotation`
  - `aggressive_equity_rotation`
  - `defensive_all_weather`
  - `global_qdii_rotation`
- 策略结果写入 `target_portfolio`。
- 策略运行记录写入 `strategy_run`。
- 信号写入 `alpha_signal`。

规则：

- 使用现有引擎的参数型策略可以通过策略管理新增。
- 新算法型策略必须实现后端策略引擎或明确分发逻辑。
- 每次策略结果必须能追溯到 `run_id`。
- 策略原因要解释入选或排除逻辑。
- 必须尊重可交易性约束。
- 不要让 AI 直接改写目标权重，除非有明确设计和评审后的策略引擎。
- 策略逻辑变化必须更新 `docs/05_策略设计.md`。

## 12. 回测规范

当前回测逻辑位于 `backend/app/services/backtest_service.py`。

规则：

- 回测必须使用本地清洗后的历史数据。
- 避免未来函数。
- 调仓时间必须明确。
- 支持手续费和滑点时，必须纳入计算。
- 回测结果应保存 run、净值曲线、指标和交易记录。
- 新策略尽量和简单基准对比。
- 修改回测逻辑必须更新 `docs/07_回测设计.md`。

待确认：

- 分钟级回测未确认。
- 更复杂的真实订单撮合模拟未确认。

## 13. 测试和验证要求

后端推荐测试：

```bash
docker compose build api
docker compose run --rm api pytest -q
```

如果本地 Python 依赖齐全：

```bash
python -m pytest backend/tests -q
```

前端构建：

```bash
cd frontend
npm run build
```

后端语法检查：

```bash
python -m compileall -q backend/app
```

Compose 校验：

```bash
docker compose config -q
```

生产健康检查示例：

```bash
curl -fsS http://127.0.0.1:5174/ >/dev/null
curl -fsS http://127.0.0.1:8000/health/ready -H 'Host: localhost'
```

规则：

- 修改后端 service 逻辑时，优先跑相关测试。
- 修改前端时，必须跑 `npm run build`。
- 如果测试因本地环境缺依赖无法运行，最终回复必须明确说明。
- 涉及部署的修改，需要确认容器启动和健康检查。

## 14. 文档同步规则

每个有意义的修改都必须更新文档。

至少：

- 在 `docs/09_开发日志.md` 顶部增加版本记录。
- 根据模块更新对应文档：
  - API：`docs/04_API接口文档.md`
  - 数据库：`docs/03_数据库设计.md`
  - 策略：`docs/05_策略设计.md`
  - 风控：`docs/06_风控设计.md`
  - 回测：`docs/07_回测设计.md`
  - 系统流程：`docs/10_系统流程说明.md`
  - 数据源：`docs/16_策略与数据源管理说明.md`
- 新增重要文档时更新 `docs/00_文档导航.md`。

文档目标：

- 用户自己能看懂。
- 后续 AI 能快速接手。
- 部署、数据源、策略边界清晰。

## 15. Git 和部署规范

Git：

- 不要提交密钥。
- 不要提交 `.env`、`.env.production`、token、API key、数据库密码。
- commit message 简洁描述本次功能或修复。
- 修改前后查看 `git status --short`。
- 不要回滚用户已有改动，除非用户明确要求。

常用生产部署命令：

```bash
ssh server2 "cd /opt/ETFSystematicPortfolioPlatform; git pull --ff-only; docker compose --env-file .env.production -f compose.production.external-caddy.yml up -d --build"
```

部署后验证：

- 前端可访问。
- API `/health/ready` 返回 ready。
- 新迁移已执行成功。
- 新接口通过认证后可用，或通过容器内部服务检查验证。

如果只改文档，通常不需要重建部署，但在用户要求每版同步时仍应提交并推送 GitHub。

## 16. 密钥安全规范

禁止：

- 把真实 token 写进源码。
- 把真实 token 写进文档。
- API 返回密钥明文。
- 把密钥发给前端做长期保存。
- 日志打印完整密钥。

允许：

- 密钥保存在 `.env` / `.env.production`。
- 密钥通过后端保存到 `data_source_config.secret_value`。
- API 返回脱敏值，例如 `abcd...123456`。

当前敏感信息包括：

- Tushare token。
- DeepSeek API key。
- 聚合数据财经新闻 key。
- 数据库密码。
- 登录会话 secret 和管理员密码 hash。

## 17. 禁止事项

不要：

- 在没有明确审批和安全设计的情况下接入真实券商交易。
- 在没有明确审批的情况下实现自动买卖。
- 把 AI 输出当成确定性投资建议。
- 未说明字段口径就混用多个行情数据源。
- 让前端直接调用外部数据商接口。
- 高频消耗共享 API token。
- 无限制保存巨大 raw payload。
- 未确认服务器其他项目时修改生产端口或反向代理假设。
- 执行 `git reset --hard` 等破坏性命令，除非用户明确要求。
- 删除用户工作区中已有但无关的改动。

## 18. 不确定时怎么做

如果需求不清楚：

- 先读当前代码和文档。
- 不确定内容标记为 `待确认`。
- 选择保守、可回滚的实现。
- 数据源和策略变化必须可追溯。
- 只有在安全假设风险较高时才询问用户。

