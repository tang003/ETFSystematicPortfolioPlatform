from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster


def list_assets(db: Session, enabled: bool | None = None) -> list[AssetMaster]:
    query = select(AssetMaster).order_by(AssetMaster.asset_class, AssetMaster.symbol)
    if enabled is not None:
        query = query.where(AssetMaster.enabled.is_(enabled))
    return list(db.scalars(query).all())

