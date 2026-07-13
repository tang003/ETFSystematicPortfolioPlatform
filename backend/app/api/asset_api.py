from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset_schema import (
    AssetBatchUpsertRequest,
    AssetBatchUpsertResponse,
    AssetRead,
    AssetUniverseSyncRequest,
    AssetUniverseSyncResponse,
    AssetUpdateRequest,
)
from app.services.asset_service import batch_upsert_assets, list_assets, sync_etf_universe, update_asset

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


@router.post("/sync-universe", response_model=AssetUniverseSyncResponse)
def sync_asset_universe(
    request: AssetUniverseSyncRequest,
    db: Session = Depends(get_db),
) -> AssetUniverseSyncResponse:
    try:
        result = sync_etf_universe(db=db, source=request.source, limit=request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - external market data providers are intentionally wrapped.
        raise HTTPException(status_code=502, detail=f"ETF 全市场数据源暂不可用：{exc}") from exc
    return AssetUniverseSyncResponse(**result)


@router.patch("/{symbol}", response_model=AssetRead)
def patch_asset(
    symbol: str,
    request: AssetUpdateRequest,
    db: Session = Depends(get_db),
) -> AssetRead:
    asset = update_asset(
        db=db,
        symbol=symbol,
        enabled=request.enabled,
        risk_level=request.risk_level,
        description=request.description,
        profile=request,
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
