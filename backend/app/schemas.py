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
    warnings: list[str]
    disclaimer: str


class AnalyzeRequest(BaseModel):
    user_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
