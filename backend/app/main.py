from fastapi import Depends, FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.auth_api import require_authenticated_user
from app.api.auth_api import router as auth_router
from app.api.asset_api import router as asset_router
from app.api.backtest_api import router as backtest_router
from app.api.calendar_api import router as calendar_router
from app.api.data_quality_api import router as data_quality_router
from app.api.etf_compare_api import router as etf_compare_router
from app.api.etf_detail_api import router as etf_detail_router
from app.api.factor_api import router as factor_router
from app.api.health_api import router as health_router
from app.api.market_api import router as market_router
from app.api.portfolio_api import router as portfolio_router
from app.api.rebalance_api import router as rebalance_router
from app.api.report_api import router as report_router
from app.api.risk_api import router as risk_router
from app.api.strategy_api import router as strategy_router
from app.api.workflow_api import router as workflow_router
from app.core.config import get_settings, validate_runtime_configuration
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    validate_runtime_configuration(settings)
    production = settings.app_env.lower() == "production"
    app = FastAPI(
        title=settings.app_name,
        version="0.36.1",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )
    if production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_prefix)
    protected = [Depends(require_authenticated_user)]
    app.include_router(asset_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(calendar_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(market_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(data_quality_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(etf_compare_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(etf_detail_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(factor_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(strategy_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(portfolio_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(risk_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(rebalance_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(backtest_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(report_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(workflow_router, prefix=settings.api_prefix, dependencies=protected)
    return app


app = create_app()
