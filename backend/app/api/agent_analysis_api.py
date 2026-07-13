from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.agent_analysis_schema import EtfAgentAnalysisLogRead, EtfAgentAnalysisRequest, EtfAgentAnalysisResponse
from app.services.agent_analysis_service import analyze_etf_with_agents, list_agent_analysis_logs

router = APIRouter(prefix="/agent-analysis", tags=["agent-analysis"])


@router.post("/etf", response_model=EtfAgentAnalysisResponse)
def analyze_etf_with_agent_committee(
    request: EtfAgentAnalysisRequest,
    db: Session = Depends(get_db),
) -> EtfAgentAnalysisResponse:
    return EtfAgentAnalysisResponse(
        **analyze_etf_with_agents(
            db,
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            use_llm=request.use_llm,
            auto_sync=request.auto_sync,
        )
    )


@router.get("/etf/history", response_model=list[EtfAgentAnalysisLogRead])
def list_etf_agent_analysis_history(
    symbol: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[EtfAgentAnalysisLogRead]:
    return [EtfAgentAnalysisLogRead(**item) for item in list_agent_analysis_logs(db, symbol=symbol, limit=limit)]
