from datetime import date, datetime

from pydantic import BaseModel, Field


class EtfAgentAnalysisRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    start_date: date | None = None
    end_date: date | None = None
    use_llm: bool = True
    auto_sync: bool = True


class AgentOpinionRead(BaseModel):
    role: str
    title: str
    stance: str
    score: int
    summary: str
    evidence: list[str]
    risks: list[str]
    suggestion: str


class EtfAgentAnalysisResponse(BaseModel):
    id: int | None = None
    symbol: str
    name: str | None
    start_date: date
    end_date: date
    data_status: str
    llm_enabled: bool
    llm_used: bool
    llm_model: str | None
    final_action: str
    final_score: int
    final_summary: str
    manager_commentary: str
    agents: list[AgentOpinionRead]
    warnings: list[str]
    created_at: datetime | None = None


class EtfAgentAnalysisLogRead(BaseModel):
    id: int
    symbol: str
    name: str | None
    start_date: date
    end_date: date
    data_status: str
    llm_used: bool
    llm_model: str | None
    final_action: str
    final_score: int
    final_summary: str
    manager_commentary: str
    agents: list[AgentOpinionRead]
    warnings: list[str]
    created_at: datetime
