from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    completed = "completed"
    unavailable = "unavailable"
    degraded = "degraded"
    failed = "failed"


class Classification(str, Enum):
    bullish = "bullish"
    neutral = "neutral"
    bearish = "bearish"
    strong = "strong"
    mixed = "mixed"
    weak = "weak"
    positive = "positive"
    negative = "negative"
    suitable = "suitable"
    unsuitable = "unsuitable"
    insufficient_data = "insufficient_data"


class Source(BaseModel):
    title: str
    document: str
    date: date
    chunk_id: str | None = None
    source_id: str | None = None
    excerpt: str | None = None
    relevance_score: float | None = Field(default=None, ge=0, le=1)


class AgentOutput(BaseModel):
    agent: Literal["technical", "sentiment", "fundamental", "behavioral"]
    status: AgentStatus
    classification: Classification
    confidence: int = Field(ge=0, le=100)
    summary: str
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    runtime_mode: Literal["llm", "deterministic_fallback"] = "deterministic_fallback"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    retrieval_mode: Literal["semantic", "tfidf_fallback", "unavailable"] | None = None
    retrieval_latency_ms: float = Field(default=0, ge=0)
    chunks_retrieved: int = Field(default=0, ge=0)


class ProfileInput(BaseModel):
    user_id: str = Field(min_length=1)
    risk_profile: Literal["conservative", "moderate", "aggressive"]
    investment_horizon_years: int = Field(ge=1, le=50)
    maximum_volatility: float = Field(ge=0, le=100)
    portfolio: list[dict[str, Any]] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)
    interaction_history: list[dict[str, Any]] = Field(default_factory=list)


class Profile(ProfileInput):
    id: int
    created_at: datetime
    updated_at: datetime


class MarketSnapshot(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    five_day_return: float
    twenty_day_return: float
    twenty_day_moving_average: float
    current_volume: int
    average_volume: int
    volatility: float
    drawdown: float
    pe_ratio: float
    revenue_growth: float
    debt_to_equity_ratio: float
    data_timestamp: datetime
    simulated_data: bool
    provider_name: str = "local_simulated_fixture"
    freshness: str = "fixture_timestamp"
    fallback_reason: str | None = None


class Synthesis(BaseModel):
    classification: Classification
    confidence: int = Field(ge=0, le=100)
    summary: str
    personalized_guidance: str
    conflicts: list[str]
    risk_flags: list[str]
    evidence_used: list[str]
    missing_evidence: list[str]


class AnalysisMetrics(BaseModel):
    latency_ms: float
    historical_signal_accuracy_percent: float
    portfolio_concentration_score: float
    data_completeness_percent: float
    agents_completed: int
    agents_expected: int
    historical_signal_correct: int = Field(default=0, ge=0)
    historical_signal_evaluated: int = Field(default=0, ge=0)
    per_agent_latency_ms: dict[str, float] = Field(default_factory=dict)
    retrieval_latency_ms: float = Field(default=0, ge=0)
    documents_retrieved: int = Field(default=0, ge=0)
    chunks_retrieved: int = Field(default=0, ge=0)
    evidence_coverage_percent: float = Field(default=0, ge=0, le=100)
    agent_agreement_percent: float = Field(default=0, ge=0, le=100)
    fallback_activations: int = Field(default=0, ge=0)
    runtime_mode: Literal["llm", "deterministic_fallback"] = "deterministic_fallback"
    retrieval_mode: Literal["semantic", "tfidf_fallback", "unavailable"] = "unavailable"
    market_data_mode: Literal["live", "simulated"] = "simulated"


class DecisionEvent(BaseModel):
    title: str
    description: str


class CommitteeResult(BaseModel):
    support: int = Field(ge=0)
    oppose: int = Field(ge=0)
    abstain: int = Field(ge=0)
    consensus_score: int = Field(ge=0, le=100)
    fragility_score: int = Field(ge=0, le=100)


class DevilsAdvocate(BaseModel):
    signal: str
    confidence: int = Field(ge=0, le=100)
    challenge: str
    evidence: list[str]


class EvidenceVerification(BaseModel):
    coverage_score: int = Field(ge=0, le=100)
    verified_claims: int = Field(ge=0)
    total_claims: int = Field(ge=0)
    unsupported_claims: list[str]


class MissingInformation(BaseModel):
    gaps: list[str]
    confidence_penalty: int = Field(ge=0, le=100)


class DecisionFactor(BaseModel):
    factor: str
    weight: int = Field(ge=0, le=100)


class StressTest(BaseModel):
    normal_signal: str
    normal_confidence: int = Field(ge=0, le=100)
    stressed_signal: str
    stressed_confidence: int = Field(ge=0, le=100)
    robustness: Literal["high", "medium", "low"]
    removed_evidence: str


class Counterfactual(BaseModel):
    investment_amount: int = Field(ge=0)
    risk_before: int = Field(ge=0, le=100)
    risk_after: int = Field(ge=0, le=100)
    sector_exposure_before: int = Field(ge=0, le=100)
    sector_exposure_after: int = Field(ge=0, le=100)
    diversification_before: int = Field(ge=0, le=100)
    diversification_after: int = Field(ge=0, le=100)
    interpretation: str


class ReplayStep(BaseModel):
    order: int = Field(ge=1)
    stage: str
    status: Literal["complete", "degraded", "failed"]
    message: str


class DecisionLab(BaseModel):
    investigation_id: str
    event: DecisionEvent
    committee: CommitteeResult
    devils_advocate: DevilsAdvocate
    evidence_verification: EvidenceVerification
    missing_information: MissingInformation
    decision_dna: list[DecisionFactor]
    change_our_mind: list[str]
    stress_test: StressTest
    counterfactual: Counterfactual
    replay: list[ReplayStep]


class AnalysisResponse(BaseModel):
    analysis_id: str
    symbol: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profile: Profile
    market_snapshot: MarketSnapshot
    market_signal: Classification
    agents: list[AgentOutput]
    synthesis: Synthesis
    sources: list[Source]
    reasoning_trace: list[str]
    metrics: AnalysisMetrics
    decision_lab: DecisionLab
    warnings: list[str]
    disclaimer: str


class AnalyzeRequest(BaseModel):
    user_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)


class DecisionInput(BaseModel):
    user_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    action: Literal["BUY", "SELL", "WATCH", "IGNORE", "INVESTIGATE"]
    analysis_id: str = Field(min_length=1)
    current_signal: Classification
    confidence: int = Field(ge=0, le=100)


class UserDecision(DecisionInput):
    id: int
    created_at: datetime
