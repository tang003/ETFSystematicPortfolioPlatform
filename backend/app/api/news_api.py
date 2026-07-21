from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_api import require_admin_user
from app.core.database import get_db
from app.schemas.news_schema import NewsArticleRead, NewsSyncRequest, NewsSyncResponse
from app.services.news_service import list_news, sync_news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=list[NewsArticleRead])
def get_news(
    symbol: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[NewsArticleRead]:
    return list_news(db, symbol=symbol, q=q, limit=limit)


@router.get("/related/{symbol}", response_model=list[NewsArticleRead])
def get_related_news(
    symbol: str,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[NewsArticleRead]:
    return list_news(db, symbol=symbol, limit=limit)


@router.post("/sync", response_model=NewsSyncResponse)
def sync_news_endpoint(
    request: NewsSyncRequest,
    _: str = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> NewsSyncResponse:
    try:
        return sync_news(db, source=request.source, num=request.num, page=request.page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - external news providers are intentionally wrapped.
        raise HTTPException(status_code=502, detail=f"新闻数据源暂不可用：{exc}") from exc

