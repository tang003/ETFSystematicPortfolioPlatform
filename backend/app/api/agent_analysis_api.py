from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.agent_analysis_schema import EtfAgentAnalysisRequest, EtfAgentAnalysisResponse
from app.services.agent_analysis_service import analyze_etf_with_agents

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
        )
    )
