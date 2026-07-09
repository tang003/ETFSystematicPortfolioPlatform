from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.schemas.asset_schema import AssetUpsertItem


def list_assets(db: Session, enabled: bool | None = None) -> list[AssetMaster]:
    query = select(AssetMaster).order_by(AssetMaster.asset_class, AssetMaster.symbol)
    if enabled is not None:
        query = query.where(AssetMaster.enabled.is_(enabled))
    return list(db.scalars(query).all())


def batch_upsert_assets(db: Session, items: list[AssetUpsertItem]) -> int:
    if not items:
        return 0
    payload = [item.model_dump() for item in items]
    statement = insert(AssetMaster).values(payload)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": statement.excluded.name,
                "exchange": statement.excluded.exchange,
                "asset_class": statement.excluded.asset_class,
                "asset_region": statement.excluded.asset_region,
                "currency": statement.excluded.currency,
                "is_cross_border": statement.excluded.is_cross_border,
                "is_leveraged": statement.excluded.is_leveraged,
                "is_inverse": statement.excluded.is_inverse,
                "enabled": statement.excluded.enabled,
                "risk_level": statement.excluded.risk_level,
                "description": statement.excluded.description,
            },
        )
    )
    db.commit()
    return len(payload)


def update_asset(
    db: Session,
    symbol: str,
    *,
    enabled: bool | None = None,
    risk_level: int | None = None,
    description: str | None = None,
) -> AssetMaster | None:
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == symbol))
    if asset is None:
        return None
    if enabled is not None:
        asset.enabled = enabled
    if risk_level is not None:
        asset.risk_level = risk_level
    if description is not None:
        asset.description = description
    db.commit()
    db.refresh(asset)
    return asset
