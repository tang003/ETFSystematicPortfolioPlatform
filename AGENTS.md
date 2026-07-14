# AGENTS.md

本文件用于指导 Codex 或其他 AI 编程助手继续开发 ETF Systematic Portfolio Platform。

这是一个持续迭代中的 ETF 量化投研和资产配置项目，不是一次性演示项目。任何修改前都必须先阅读现有代码和相关文档，不能凭空假设系统能力。

## 0. 当前审查结论

本文件已根据当前代码、`README.md` 和 `docs/` 下核心设计文档重新审查。

总体判断：

- 项目真实定位是个人 ETF 投研、组合构建、持仓分析、定投、风控、回测、报告、AI 投研和部署运维平台。
- 当前不连接真实券商账户，不自动下单，不直接操作资金。
- 当前正式 ETF 行情、交易日历、ETF 档案和主资料应以 Tushare 为主。
- AKShare、Eastmoney 在早期文档、依赖和部分历史代码中仍存在，但正式数据口径已经转向 Tushare-only。除非用户明确要求并完成字段口径评审，不要重新启用它们进入正式 `market_data_clean`。
- 部分文档的“当前版本号”和早期数据源描述可能滞后。遇到冲突时，优先级为：当前代码 > 最新开发日志和 API 文档 > 专题设计文档 > README 中早期描述。
- 每次有意义的修改都必须同步文档和开发日志，并提交推送 GitHub。

## 1. 项目背景

ETF Systematic Portfolio Platform 是面向个人用户的 ETF 系统化资产配置平台，用于中长期 ETF 投研、组合构建、持仓分析、定投计划、风险控制、回测复盘、新闻辅助研究、AI 投研报告和部署运维。

当前业务边界：

- 系统聚焦 ETF，不是完整股票交易平台。
- 当前不连接真实券商账户。
- 当前不自动下单。
- 当前不直接操作用户资金。
- 所有买入、卖出、调仓、定投建议都需要用户人工确认。
- 新闻和 AI 输出只作为投研解释材料，不是直接交易信号。
- 后续如接入券商或自动交易，必须先做独立的权限、审计、风控、人工确认和异常暂停设计。

## 2. 当前已确认能力

当前代码中已经包含：

- ETF 基础池、精选池和研究池管理。
- ETF 主资料补全。
- 基于 Tushare 的交易日历、ETF 日线行情、ETF 档案、基金净值、基金份额和部分指数行情同步。
- 数据质量检查、行情清洗和质量日志。
- 历史行情初始化工作流。
- 因子计算、因子排名和因子研究。
- ETF 筛选、ETF 对比、ETF 详情和买入决策辅助。
- 当前持仓手动录入、自动补全、补仓和持仓分析。
- 组合 X-Ray、定投计划和每期建议。
- 策略管理、目标组合生成和多套参数型内置策略。
- 风控检查和调仓建议单。
- 回测、净值曲线、模拟交易和指标落库。
- Markdown 报告。
- DeepSeek 驱动的 AI ETF 投研委员会。
- 数据源管理，支持 Tushare、DeepSeek、聚合数据财经新闻的运行时配置。
- 聚合数据财经新闻同步和本地新闻列表。
- Redis / worker 后台任务执行。
- Docker Compose 生产部署，外部 Caddy 反向代理。

待确认或未完成：

- 多用户独立数据隔离。
- 券商只读持仓同步。
- 自动交易和真实订单执行。
- 分钟级行情、实时行情、Level-2 深度行情。
- ETF 成分、行业暴露、估值、完整份额规模历史、分红复权细节。
- 完整操作审计、用户权限分层、数据源调用统计和任务告警。
- 密钥完整加密存储方案。

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
- APScheduler 已安装，具体调度使用方式修改前需看代码确认。
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

- Tushare Pro：正式 ETF 交易日历、日线行情、ETF 基础池、ETF 主资料、基金净值、基金份额、指数日线。
- DeepSeek：AI 投研总结和解释。
- 聚合数据财经新闻：低频财经新闻同步。

历史或潜在数据源：

- AKShare：依赖和旧代码仍存在，正式行情入口已停用。
- Eastmoney：旧兜底逻辑仍在部分代码中存在，正式 ETF 行情和资料模式不应使用它污染清洗行情。
- Baostock：曾被讨论为未来备用源，当前未确认已实现。

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

- 策略：`docs/05_策略设计.md`、`docs/16_策略与数据源管理说明.md`
- 风控：`docs/06_风控设计.md`
- 回测：`docs/07_回测设计.md`
- 部署：`docs/08_部署说明.md`、`docs/11_服务器上线清单.md`
- 上线审计和路线：`docs/12_ETF功能优化路线图.md`、`docs/13_上线终局审计.md`
- 用户案例：`docs/14_普通用户标普500评估报告.md`
- 分析周期：`docs/15_分析周期口径说明.md`

如果文档和当前代码冲突，以当前代码为准，并在本次修改中同步修正文档。

## 5. 目录结构说明

根目录：

- `backend/`：FastAPI 后端。
- `frontend/`：Vue 前端。
- `docs/`：项目文档。
- `scripts/`：部署、备份、恢复、数据同步等运维脚本。
- `sql/`：新数据库 volume 首次初始化 SQL。
- `docker-compose.yml`：本地 Docker Compose。
- `compose.production.yml`：生产 Compose 变体。
- `compose.production.external-caddy.yml`：外部 Caddy 反代下的生产 Compose。
- `Caddyfile`：反向代理配置参考。
- `.env.example`、`.env.production.example`：环境变量模板。

后端：

- `backend/app/main.py`：FastAPI 应用和路由注册。
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

## 6. 总体数据流规范

标准数据流：

```text
ETF 基础池 asset_master
 -> 交易日历 trading_calendar
 -> 原始行情 market_data_raw
 -> 清洗行情 market_data_clean
 -> 数据质量 data_quality_log
 -> 因子 factor_daily
 -> 策略 strategy_run / alpha_signal
 -> 目标组合 target_portfolio
 -> 当前持仓 portfolio_position
 -> 持仓分析 / 定投 / 风控 / 调仓
 -> 回测 / 报告 / AI 投研
```

硬性规则：

- 策略、因子、回测、ETF 详情、AI 投研默认读取 `market_data_clean`，不要直接拿外部 API 响应做计算。
- `market_data_raw` 保存外部来源和原始 payload，`market_data_clean` 保存统一口径后的行情。
- 外部数据源入库前必须经过字段映射、日期、价格、成交量、成交额和来源标准化。
- 不要让前端直接调用 Tushare、DeepSeek、聚合数据或其他外部数据商。
- 不要在本地已有足够数据时重复消耗外部接口。
- 共享 token 或中转 token 必须尊重限频、间隔和批量上限。
- 全市场基础池只代表系统知道哪些 ETF，不代表所有 ETF 都进入策略。只有 `enabled=true` 的 ETF 才进入日常研究池。
- 当前持仓里的 ETF 可以自动登记和启用，但仍需要同步行情后才能参与分析。

## 7. 数据源规范

正式 ETF 数据源：

- ETF 行情、交易日历、ETF 档案和主资料当前以 Tushare 为正式口径。
- `source=auto` 在正式语义上应等同 Tushare 或优先 Tushare；不要悄悄回退到字段口径不一致的数据源。
- AKShare / Eastmoney 如需重新启用，必须先完成字段映射、异常值保护、质量检查和文档评审。

Tushare 当前用途：

- `trade_cal`：交易日历。
- `fund_daily`：ETF 日线行情。
- `fund_basic`：ETF 基础档案。
- `fund_nav`：基金净值。
- `fund_share`：基金份额。
- `index_daily`：指数日线，用于跟踪误差等扩展。

新闻数据：

- 当前运行时新闻源为 `juhe_finance_news`。
- 新闻必须由后端同步入 `news_article`。
- 前端读取本地数据库，不直接请求聚合数据。
- 新闻只作为研究上下文，不是买卖信号。

AI 数据：

- DeepSeek 输出用于解释和总结。
- AI 不得编造行情、费率、规模、收益或回撤。
- AI 结论必须基于本地行情、因子、持仓、目标组合、新闻或报告上下文。
- AI 输出不能作为收益保证或确定性投资建议。

## 8. 数据库设计规范

数据库为 PostgreSQL，使用 SQLAlchemy 模型和 Alembic 迁移。

规则：

- 表结构或字段变化必须新增 Alembic 迁移。
- 修改表结构后必须同步更新 `docs/03_数据库设计.md`。
- 不要只修改 `sql/init_schema.sql` 来影响已部署数据库；该 SQL 主要用于新 volume 初始化。
- 迁移必须考虑生产已有数据，尽量提供默认值、可空过渡或兼容逻辑。
- 生产容器启动时会执行 `alembic upgrade head`。
- model、schema、service、API 文档、前端类型和数据库文档必须保持一致。
- 新增唯一约束、索引或 JSON 字段时，必须说明查询场景和数据结构。
- 不要把关键业务字段只塞进 JSON；可筛选、可排序、可关联的字段应拆成列。
- 不要在迁移中写入真实 token、密码或用户私密数据。

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
- `investment_plan_suggestion`
- `risk_rule`
- `risk_check_result`
- `rebalance_order`
- `backtest_run`
- `backtest_equity_curve`
- `backtest_trade`
- `backtest_metrics`
- `report_log`
- `agent_analysis_log`
- `workflow_task`
- `workflow_task_step`
- `asset_sync_log`
- `data_source_config`
- `news_article`

## 9. API 开发规范

遵循现有分层：

1. API 路由放在 `backend/app/api`。
2. Pydantic schema 放在 `backend/app/schemas`。
3. 业务逻辑放在 `backend/app/services`。
4. ORM 模型放在 `backend/app/models`。
5. 数据库变化通过 `backend/alembic/versions` 迁移。

API 规则：

- Router 保持轻量，只处理请求、响应和 HTTP 异常。
- 请求和响应必须使用 Pydantic schema。
- 面向用户的错误使用清晰中文或可理解的 `HTTPException`。
- 外部数据源错误必须被包装成受控错误，不能让内部堆栈直接暴露给前端。
- API 响应不得泄漏密钥明文。
- 新增路由必须在 `backend/app/main.py` 注册。
- 新增或修改 API 必须更新 `docs/04_API接口文档.md` 和 `frontend/src/api/client.ts`。
- 生产环境除 `/health` 和 `/api/auth/*` 外，业务 API 默认需要登录。
- 长任务不要阻塞前端等待，优先使用 `workflow_task` / worker 模式。

响应设计：

- 返回结果应包含足够的状态字段、错误原因和用户下一步操作提示。
- 批量同步接口应返回每个 symbol 的成功、跳过、失败和原因。
- 涉及 run 的接口必须返回 `run_id` 或可追溯任务 ID。

## 10. 前端开发规范

遵循现有模式：

- 使用 Vue 3 `<script setup lang="ts">`。
- UI 使用 Element Plus。
- 图表使用 ECharts。
- API 请求和类型统一写在 `frontend/src/api/client.ts`。
- 路由写在 `frontend/src/router/index.ts`。
- 顶层页面需要在 `frontend/src/App.vue` 增加菜单入口。
- 分析周期控件优先复用 `frontend/src/datePresets.ts`。

交互规则：

- 主应用页面应该是可用工具，不做营销页。
- UI 主语言使用中文，必要技术字段保留英文。
- 不要把普通用户不需要理解的原始参数暴露出来。
- 历史回看窗口统一叫 `分析周期`。
- 只有自定义日期时才显示 `日期范围`。
- 不要混淆 `分析周期`、未来持有周期和定投周期。
- 左侧菜单保持稳定，页面滚动不应带走导航。
- API key / token 只能作为写入型表单提交，不应在前端长期保存或回显。
- 数据缺失时必须告诉用户原因和下一步，例如“先同步该 ETF 近 1 年行情”。

## 11. 分析周期规范

统一定义：

- `分析周期` 是历史回看窗口。
- `定投周期` 是未来准备投入多久。
- `持有周期` 是用户计划持有多久。

固定分析周期：

- 半年。
- 1 年。
- 3 年。
- 5 年。
- 成立以来。
- 自定义。

维护规则：

- 历史分析类页面统一叫 `分析周期`。
- 只在选择 `自定义` 时显示起止日期。
- 全流程、数据健康、因子、ETF 对比、ETF 筛选、ETF 详情、AI 投研、回测应尽量复用 `frontend/src/datePresets.ts`。
- 不要把未来预测写成历史测算；系统不能推测未来确定收益。

## 12. 策略开发规范

当前策略系统：

- 策略配置保存在 `strategy_config`。
- 当前正式引擎是 `factor_rotation`。
- 默认策略代码为 `core_etf_rotation`。
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
- 新算法型策略必须在后端实现引擎或明确分发逻辑。
- 每次策略结果必须能追溯到 `run_id`、`strategy_code`、`strategy_version` 和 `run_date`。
- 策略必须说明入选、排除、降权和现金缓冲原因。
- 策略必须尊重可交易性约束。
- 权重合计应归一到 100%，并处理无候选 ETF、无现金 ETF、缺因子等异常场景。
- 不要让 AI 直接改写目标权重，除非有明确设计和评审后的策略引擎。
- 策略逻辑变化必须更新 `docs/05_策略设计.md` 和相关测试。

禁止：

- 在没有因子数据时生成看似正常的目标组合。
- 用未来日期行情或未来因子参与当日策略。
- 把新闻情绪直接当成买卖信号绕过量化规则。

## 13. 风控规范

当前风控输入：

- `target_portfolio`
- `portfolio_position`
- `asset_master`
- `market_data_clean`
- `factor_daily`
- `holding_analysis_result`

当前风控输出：

- `risk_check_result`
- `rebalance_order`
- 报告模块。
- 组合工作台。

规则：

- 风控只生成检查结果和建议单，不自动交易。
- 风控调整必须写入 `risk_check_result`，并保留调整前后数值。
- 调仓建议必须能追溯 `run_id`。
- 单 ETF 权重、权益仓位、防守资产、现金、跨境、高风险 ETF、可交易性、数据缺失和行情过旧都应纳入风控思路。
- 新增风控规则优先配置化，避免硬编码散落在多个服务。
- 如果目标组合没有现金或防守资产，需要明确异常处理，不要悄悄把权重分配给第一只 ETF。
- 修改风控逻辑必须更新 `docs/06_风控设计.md` 和 `backend/tests/test_risk_service.py`。

## 14. 回测规范

当前回测逻辑位于 `backend/app/services/backtest_service.py`。

规则：

- 回测必须使用本地 `market_data_clean`。
- 回测不得使用未来函数。
- 调仓日、因子取值日、交易执行日必须口径清晰。
- 手续费和滑点参数必须进入交易成本计算。
- 回测结果应保存 run、净值曲线、指标和交易记录。
- 策略回测应尽量与买入持有、等权或基准对比。
- 月度追加资金需要区分累计投入本金和净值收益。
- 缺行情、停牌、样本不足必须给出明确错误或警告。
- 修改回测逻辑必须更新 `docs/07_回测设计.md` 和 `backend/tests/test_backtest_service.py`。

禁止：

- 用调参后的未来最优结果覆盖历史过程。
- 隐藏失败交易或缺失价格。
- 把回测收益描述成未来收益承诺。

待确认：

- 分钟级回测未实现。
- 更复杂的真实订单撮合模拟未实现。
- 分红、拆分、复权全细节仍需增强。

## 15. 持仓和定投规范

当前持仓：

- 用户主要填写 ETF 代码、持仓数量、成本价。
- 名称、类型、现价、市值、权重、成本金额、浮盈亏由系统补全或计算。
- 推荐手动录入，不直接同步东方财富、同花顺或券商账户。

规则：

- 当前持仓新增或编辑后应保存到数据库。
- 如果代码不在 ETF 池，应自动登记候选 ETF，并尝试补全主数据和最近行情。
- 缺少行情时不能假装有现价，应提示用户同步行情。
- 持仓分析必须以目标组合作为参照；没有目标组合时应提示先运行策略或全流程。

定投：

- `total_budget` 是准备投入的总资金。
- `months` 是未来投入周期。
- `target_annual_return` 是策略目标参数，不是收益承诺。
- 当前只生成建议，不自动扣款、不自动下单。

## 16. 报告和 AI 投研规范

报告：

- Markdown 报告中文为主，保留必要英文术语。
- 报告应包含数据区间、数据质量、核心结论、风险提示和下一步建议。
- 报告不能写成收益承诺。

AI 投研：

- Agent 结论必须引用系统已有数据或明确说明数据缺失。
- DeepSeek 只做总结、解释和表达增强。
- 如果 DeepSeek 不可用，应返回规则型结论和错误提示。
- AI 投研记录写入 `agent_analysis_log`。
- 新闻数据进入 AI 前应说明来源、发布时间和关联逻辑。

## 17. 数据源管理和密钥安全规范

禁止：

- 把真实 token 写进源码。
- 把真实 token 写进文档。
- API 返回密钥明文。
- 把密钥发给前端做长期保存。
- 日志打印完整密钥。
- 在测试、截图、开发日志中保留完整密钥。

允许：

- 密钥保存在 `.env` / `.env.production`。
- 密钥通过后端保存到 `data_source_config.secret_value`。
- API 返回脱敏值，例如 `abcd...123456`。

运行时覆盖：

- `tushare` 的数据库配置可以覆盖 `TUSHARE_TOKEN` 和 `TUSHARE_API_URL`。
- `deepseek` 的数据库配置可以覆盖 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL`。
- `juhe_finance_news` 的数据库配置可以覆盖新闻同步 Key 和接口地址。

新增数据源：

- 默认 `adapter_status` 应为 `metadata_only` 或 `planned`。
- 只有完成后端适配器、字段映射、限频、错误处理、清洗和测试后，才能标记为 `runtime_supported`。

## 18. Docker 和部署规范

本地开发：

```bash
cp .env.example .env
docker compose up --build
```

常用验证：

```bash
docker compose config -q
docker compose build api
docker compose run --rm api pytest -q
cd frontend
npm run build
```

生产部署推荐使用脚本：

```bash
cd /opt/ETFSystematicPortfolioPlatform
git pull --ff-only
python3 scripts/deploy_production.py --compose-file compose.production.external-caddy.yml --env-file .env.production
```

生产环境说明：

- 使用 `compose.production.external-caddy.yml`。
- 外部 Caddy 接管 80/443。
- 前端容器只绑定 `127.0.0.1:5174`，避免影响服务器其他项目。
- PostgreSQL、Redis、API 和 worker 不应直接暴露公网。
- 生产环境必须开启 `AUTH_ENABLED=true`。
- 部署前应备份数据库；部署后检查 `/health/ready`。

如果只改文档，通常不需要重建部署，但仍应提交并推送 GitHub。

## 19. 测试和验证要求

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

规则：

- 修改后端 service 逻辑时，优先跑相关测试。
- 修改前端时，必须跑 `npm run build`。
- 修改数据库迁移时，必须验证 Alembic 能升级。
- 修改部署配置时，必须跑 Compose 校验。
- 如果测试因本地环境缺依赖无法运行，最终回复必须明确说明。
- 涉及生产部署的修改，需要确认容器启动和健康检查。

## 20. 文档同步规则

每个有意义的修改都必须更新文档。

至少：

- 在 `docs/09_开发日志.md` 顶部增加版本记录。
- 根据模块更新对应文档：
  - API：`docs/04_API接口文档.md`
  - 数据库：`docs/03_数据库设计.md`
  - 策略：`docs/05_策略设计.md`
  - 风控：`docs/06_风控设计.md`
  - 回测：`docs/07_回测设计.md`
  - 部署：`docs/08_部署说明.md`
  - 系统流程：`docs/10_系统流程说明.md`
  - 分析周期：`docs/15_分析周期口径说明.md`
  - 策略和数据源：`docs/16_策略与数据源管理说明.md`
- 新增重要文档时更新 `docs/00_文档导航.md`。

文档目标：

- 用户自己能看懂。
- 后续 AI 能快速接手。
- 部署、数据源、策略边界清晰。
- 清楚说明哪些能力已实现，哪些是待确认或规划中。

## 21. Git 开发流程

规则：

- 修改前后查看 `git status --short`。
- 不要提交密钥、`.env`、`.env.production`、token、API key、数据库密码。
- commit message 简洁描述本次功能或修复。
- 用户要求每版上传 GitHub 时，完成后必须提交并推送。
- 当前工作树可能是 detached HEAD，推送通常使用 `git push origin HEAD:main`。
- 不要回滚用户已有改动，除非用户明确要求。
- 不要执行 `git reset --hard` 等破坏性命令，除非用户明确要求。

建议流程：

1. 阅读相关文档和代码。
2. 小步修改。
3. 跑必要测试或构建。
4. 更新对应文档和开发日志。
5. `git diff --check`。
6. `git status --short`。
7. commit。
8. push GitHub。
9. 如涉及部署，执行生产部署并健康检查。

## 22. 禁止事项

不要：

- 在没有明确审批和安全设计的情况下接入真实券商交易。
- 在没有明确审批的情况下实现自动买卖。
- 把 AI 输出当成确定性投资建议。
- 未说明字段口径就混用多个行情数据源。
- 让前端直接调用外部数据商接口。
- 高频消耗共享 API token。
- 无限制保存巨大 raw payload。
- 在没有迁移的情况下直接改生产表结构。
- 跳过 `market_data_clean` 直接用外部 API 结果跑策略或回测。
- 在回测中使用未来数据。
- 隐藏数据缺失、样本不足或同步失败。
- 未确认服务器其他项目时修改生产端口或反向代理假设。
- 删除用户工作区中已有但无关的改动。

## 23. 不确定时怎么做

如果需求不清楚：

- 先读当前代码和文档。
- 不确定内容标记为 `待确认`。
- 选择保守、可回滚的实现。
- 数据源、策略、风控、回测变化必须可追溯。
- 只有在安全假设风险较高时才询问用户。

