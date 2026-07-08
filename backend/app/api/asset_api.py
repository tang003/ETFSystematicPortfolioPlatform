from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset_schema import AssetRead
from app.services.asset_service import list_assets

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def get_assets(
    enabled: bool | None = Query(default=None, description="按启用状态筛选 ETF"),
    db: Session = Depends(get_db),
) -> list[AssetRead]:
    return list_assets(db=db, enabled=enabled)

