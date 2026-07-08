from fastapi import FastAPI

from app.api.asset_api import router as asset_router
from app.api.health_api import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health_router)
    app.include_router(asset_router, prefix=settings.api_prefix)
    return app


app = create_app()

