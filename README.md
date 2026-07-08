# ETF Systematic Portfolio Platform

ETF 系统化资产配置平台，面向个人中长期 ETF 投研与资产配置流程。系统第一阶段先完成基础工程、数据库结构、ETF 主数据查询和健康检查。

## 当前版本

- 版本：`v0.1.0-phase1`
- 阶段：基础工程与数据库
- 范围：FastAPI 后端、PostgreSQL 表结构、ETF 初始池、Docker Compose、基础文档

## 本地启动

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

- API 健康检查：http://localhost:8000/health
- Swagger 文档：http://localhost:8000/docs
- ETF 资产列表：http://localhost:8000/api/assets

## 项目文档

核心维护文档位于 `docs/`。以后每完成一个阶段或版本，都需要同步更新相关设计文档和 `docs/09_开发日志.md`。

