from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_api import require_admin_user
from app.core.database import get_db
from app.schemas.asset_schema import (
    AssetBatchUpsertRequest,
    AssetBatchUpsertResponse,
    AssetProfileSyncRequest,
    AssetProfileSyncResponse,
    AssetRead,
    AssetSyncLogRead,
    AssetUniverseSyncRequest,
    AssetUniverseSyncResponse,
    AssetUpdateRequest,
)
from app.services.asset_service import (
    batch_upsert_assets,
    list_asset_sync_logs,
    list_assets,
    seed_curated_etf_pool,
    sync_etf_profiles,
    sync_etf_universe,
    update_asset,
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def get_assets(
    q: str | None = Query(default=None, description="按代码、名称、指数或基金公司搜索"),
    limit: int | None = Query(default=None, ge=1, le=5000),
    enabled: bool | None = Query(default=None, description="按启用状态筛选 ETF"),
    db: Session = Depends(get_db),
) -> list[AssetRead]:
    return list_assets(db=db, enabled=enabled, q=q, limit=limit)


@router.post("/batch-upsert", response_model=AssetBatchUpsertResponse)
def upsert_assets(
    request: AssetBatchUpsertRequest,
    _: str = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AssetBatchUpsertResponse:
    count = batch_upsert_assets(db=db, items=request.items)
    return AssetBatchUpsertResponse(total=len(request.items), inserted_or_updated=count)


@router.post("/seed-curated", response_model=AssetBatchUpsertResponse)
def seed_curated_assets(
    _: str = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AssetBatchUpsertResponse:
    result = seed_curated_etf_pool(db=db)
    return AssetBatchUpsertResponse(total=result["total"], inserted_or_updated=result["inserted_or_updated"])


@router.post("/sync-universe", response_model=AssetUniverseSyncResponse)
def sync_asset_universe(
    request: AssetUniverseSyncRequest,
    _: str = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AssetUniverseSyncResponse:
    try:
        result = sync_etf_universe(db=db, source=request.source, limit=request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - external market data providers are intentionally wrapped.
        raise HTTPException(status_code=502, detail=f"ETF 基础池数据源暂不可用：{exc}") from exc
    return AssetUniverseSyncResponse(**result)


@router.post("/sync-profiles", response_model=AssetProfileSyncResponse)
def sync_asset_profiles(
    request: AssetProfileSyncRequest,
    _: str = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AssetProfileSyncResponse:
    try:
        result = sync_etf_profiles(
            db=db,
            source=request.source,
            symbols=request.symbols,
            limit=request.limit,
            preserve_existing=request.preserve_existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - external market data providers are intentionally wrapped.
        raise HTTPException(status_code=502, detail=f"ETF 资料补全暂不可用：{exc}") from exc
    return AssetProfileSyncResponse(**result)


@router.get("/sync-logs", response_model=list[AssetSyncLogRead])
def get_asset_sync_logs(
    sync_type: str | None = Query(default=None, description="同步类型，例如 profile"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AssetSyncLogRead]:
    return list_asset_sync_logs(db=db, sync_type=sync_type, limit=limit)


@router.patch("/{symbol}", response_model=AssetRead)
def patch_asset(
    symbol: str,
    request: AssetUpdateRequest,
    _: str = Depends(require_admin_user),
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
