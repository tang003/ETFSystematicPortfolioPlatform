# ETF Systematic Portfolio Platform

ETF 系统化资产配置平台，面向个人中长期 ETF 投研与资产配置流程。系统第一阶段先完成基础工程、数据库结构、ETF 主数据查询和健康检查。

## 当前版本

- 版本：`v0.9.0-phase9-operable-web-console`
- 阶段：可操作 Web 控制台
- 范围：FastAPI 后端、PostgreSQL/Redis、ETF 数据同步、因子计算、策略组合、风控调仓、回测、报告、Vue 前端控制台

## 本地启动

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

- API 健康检查：http://localhost:8000/health
- Swagger 文档：http://localhost:8000/docs
- ETF 资产列表：http://localhost:8000/api/assets
- Web 控制台：http://localhost:5173

Web 控制台当前支持中文导航，并可在页面内执行交易日历同步、行情同步、数据检查、因子计算、策略运行、风控检查、调仓单生成、回测和月度报告生成。

## 项目文档

核心维护文档位于 `docs/`。以后每完成一个阶段或版本，都需要同步更新相关设计文档和 `docs/09_开发日志.md`。
