# ETF Systematic Portfolio Platform

ETF 系统化资产配置平台，面向个人中长期 ETF 投研、资产配置、持仓分析、定投计划、风险控制、回测复盘和报告生成。

当前系统不连接真实券商账户，不自动下单，不直接操作资金。所有买卖、调仓、定投建议都需要用户人工确认。

## 当前版本

- 版本：`v0.64.7-tushare-doc-and-default-source-cleanup`
- 阶段：Tushare-only 数据模式、数据健康补齐、后台任务中心、数据源调用统计

## 线上地址

- Web 控制台：`https://etf.8886767.xyz`
- AI 投研页面：`https://etf.8886767.xyz/agent-analysis`
- 健康检查：`https://etf.8886767.xyz/health/ready`

## 技术栈

后端：

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- PostgreSQL
- Redis

前端：

- Vue 3
- TypeScript
- Element Plus
- ECharts
- Vite

部署：

- Docker Compose
- Nginx 前端容器
- 外部 Caddy 反向代理
- GitHub 拉取部署

## 当前主要功能

- ETF 池：同步和维护 ETF 基础池/主数据，启用研究对象；正式基础池和主资料同步当前使用 Tushare。
- ETF 主资料：支持基金公司、跟踪指数、基金规模、费率、上市日期、跟踪误差、溢价率等字段，并可按当前筛选结果自动补全。
- 行情同步：正式路径使用 Tushare fund_daily，旧 AKShare / Eastmoney 代码仅作为历史遗留保留，业务入口已停用。
- 数据质量：记录行情缺失、异常、清洗结果。
- 数据健康：展示分析周期内的样本覆盖率、缺失行情、建议补齐代码，并支持后台补齐任务。
- 因子计算：趋势、动量、波动、回撤、流动性和 Alpha。
- ETF 对比：收益、波动、回撤、成交额、相关性、可交易性评分。
- ETF 详情：单只 ETF 曲线、回撤、因子、最近行情和同指数 ETF 替代推荐。
- 策略：核心 ETF 轮动策略 `core_etf_rotation`。
- 目标组合：生成目标权重。
- 当前持仓：手动录入代码、数量、成本价，系统补全名称、类型、现价、市值和同指数替代观察。
- 持仓分析：判断加仓、减仓、持有或退出，并提示同指数替代 ETF。
- 定投计划：根据资金、周期、目标年化生成每期建议。
- 风控调仓：执行风控检查并生成调仓建议单。
- 回测：支持基础策略回测和月度追加资金。
- 报告：生成中文 Markdown 月度报告，包含持仓替代观察。
- AI 投研：DeepSeek + 多 Agent ETF 分析，包含执行替代 Agent，并保存历史记录。
- 部署运维：数据库备份、恢复、迁移、worker 后台任务。
- 任务中心：展示全流程、历史初始化、行情补齐任务的进度、步骤、耗时和失败原因。
- 数据源管理：维护 Tushare、DeepSeek、聚合新闻配置，并展示近期同步统计和同步日志。

## 本地启动

```bash
cp .env.example .env
docker compose up --build
```

本地地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- Swagger：`http://localhost:8000/docs`

## 常用测试

后端：

```bash
docker compose build api
docker compose run --rm api pytest -q
```

前端：

```bash
cd frontend
npm run build
```

Compose：

```bash
docker compose config -q
```

## DeepSeek 配置

DeepSeek 用于 AI 投研中文总结。

```bash
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=45
DEEPSEEK_MAX_TOKENS=1800
DEEPSEEK_THINKING_ENABLED=false
```

密钥只能放在 `.env` 或服务器 `.env.production`，不要提交 GitHub。

## Tushare 配置

```bash
TUSHARE_TOKEN=your_token
TUSHARE_REQUEST_INTERVAL_SECONDS=1.5
```

共享 token 或低积分时，建议只同步 `core` 范围，并设置请求间隔。

## 生产部署

服务器目录：

```bash
/opt/ETFSystematicPortfolioPlatform
```

部署命令：

```bash
cd /opt/ETFSystematicPortfolioPlatform
git pull --ff-only
python3 scripts/deploy_production.py --compose-file compose.production.external-caddy.yml --env-file .env.production
```

生产环境使用外部 Caddy 接管 80/443，本项目通过 `compose.production.external-caddy.yml` 绑定本机端口，避免影响服务器其他项目。

## 文档入口

建议先读：

1. `docs/00_文档导航.md`
2. `docs/01_项目说明.md`
3. `docs/02_系统架构.md`
4. `docs/03_数据库设计.md`
5. `docs/04_API接口文档.md`
6. `docs/10_系统流程说明.md`
7. `docs/09_开发日志.md`

## 给 AI 修改项目时

最少提供：

- `README.md`
- `docs/00_文档导航.md`
- `docs/01_项目说明.md`
- `docs/02_系统架构.md`
- `docs/03_数据库设计.md`
- `docs/04_API接口文档.md`
- `docs/10_系统流程说明.md`
- 本次任务相关代码文件

## 投资和安全边界

- 本项目不是投资顾问服务。
- 系统建议不代表收益承诺。
- 当前不自动下单。
- 当前不连接真实券商交易。
- 后续若接交易接口，必须新增人工确认、风控拦截、订单审计和异常暂停机制。
- 不要把任何真实 API Key、数据库密码、登录密码提交到 Git。
