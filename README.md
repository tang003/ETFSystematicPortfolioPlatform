# ETF Systematic Portfolio Platform

ETF 系统化资产配置平台，面向个人中长期 ETF 投研、资产配置、持仓分析和月度复盘。系统当前不连接真实券商账户，不自动下单，所有调仓结果都作为人工确认前的建议。

## 当前版本

- 版本：`v0.13.1-docs-polish`
- 阶段：文档包装与交接优化
- 业务能力：ETF 数据同步、数据质量检查、因子计算、策略组合、当前持仓分析、风控调仓、回测、中文报告、Vue 前端控制台
- 技术栈：FastAPI、PostgreSQL、Redis、SQLAlchemy、Pydantic、Vue 3、Element Plus、Vite、Docker Compose

## 快速启动

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

- Web 控制台：http://localhost:5173
- API 健康检查：http://localhost:8000/health
- Swagger 文档：http://localhost:8000/docs
- ETF 资产列表：http://localhost:8000/api/assets

## 主要功能

- 全流程任务：一键串联行情同步、因子计算、策略运行、风控调仓、回测和报告。
- ETF 池：管理和查询系统当前启用的 ETF 主数据。
- 数据健康：同步交易日历和行情，检查缺失数据、异常数据和清洗结果。
- 因子排名：计算趋势、动量、波动、回撤、流动性等指标并生成 Alpha 排名。
- 目标组合：运行 `core_etf_rotation` 策略，生成目标权重。
- 当前持仓：录入用户已有 ETF 持仓，判断加仓、减仓、持有或退出。
- 风控调仓：基于目标组合和真实当前权重生成调仓建议单。
- 回测：运行基础买入持有回测，查看净值曲线和绩效指标。
- 报告：生成中文为主、保留必要英文术语的月度 Markdown 报告。

## 文档入口

核心文档位于 `docs/`。建议优先阅读：

1. `docs/00_文档导航.md`：文档地图、阅读路径、维护规范。
2. `docs/10_系统流程说明.md`：从业务角度理解完整系统流程。
3. `docs/04_API接口文档.md`：查看后端接口、请求参数和响应示例。
4. `docs/09_开发日志.md`：查看每个版本的变更、验收和后续待办。

后续每完成一个版本，都需要同步更新相关设计文档和 `docs/09_开发日志.md`，方便自己维护，也方便把文档交给 AI 快速接手项目。
