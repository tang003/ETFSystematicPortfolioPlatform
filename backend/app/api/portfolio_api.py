from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.portfolio_schema import TargetPortfolioRead
from app.services.strategy_service import latest_target_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/target", response_model=list[TargetPortfolioRead])
def get_latest_target_portfolio(db: Session = Depends(get_db)) -> list[TargetPortfolioRead]:
    return latest_target_portfolio(db)

