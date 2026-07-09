from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset_schema import AssetBatchUpsertRequest, AssetBatchUpsertResponse, AssetRead
from app.services.asset_service import batch_upsert_assets, list_assets

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def get_assets(
    enabled: bool | None = Query(default=None, description="按启用状态筛选 ETF"),
    db: Session = Depends(get_db),
) -> list[AssetRead]:
    return list_assets(db=db, enabled=enabled)


@router.post("/batch-upsert", response_model=AssetBatchUpsertResponse)
def upsert_assets(
    request: AssetBatchUpsertRequest,
    db: Session = Depends(get_db),
) -> AssetBatchUpsertResponse:
    count = batch_upsert_assets(db=db, items=request.items)
    return AssetBatchUpsertResponse(total=len(request.items), inserted_or_updated=count)
