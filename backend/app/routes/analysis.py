from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.database import connection, encode_json
from app.routes.profiles import get_profile
from app.schemas import (AnalysisMetrics, AnalysisResponse, AnalyzeRequest, AgentStatus,
                         Classification, Source)
from app.services.market_data import SimulatedMarketDataProvider, SymbolNotFoundError
from app.services.decision_lab import build_decision_lab
from app.services.metrics import (data_completeness, historical_accuracy,
                                  historical_accuracy_counts, portfolio_concentration)
from app.services.orchestrator import run_agents
from app.services.synthesizer import synthesize

router = APIRouter(prefix="/analyze", tags=["analysis"])
provider = SimulatedMarketDataProvider()
DISCLAIMER = ("Educational research intelligence using simulated local data. This is not financial advice, "
              "a direct trading instruction, or a guaranteed outcome.")


def _deduplicate_sources(agents: list[object]) -> list[Source]:
    found: dict[tuple[str, str | None], Source] = {}
    for agent in agents:
        for source in agent.sources:  # type: ignore[attr-defined]
            found[(source.document, source.chunk_id)] = source
    return list(found.values())


@router.post("", response_model=AnalysisResponse)
async def analyze(payload: AnalyzeRequest) -> AnalysisResponse:
    started = perf_counter()
    profile = get_profile(payload.user_id)
    try:
        snapshot = provider.get_snapshot(payload.symbol)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    agents, orchestration_latency = await run_agents(snapshot, profile)
    market_signal, synthesis, warnings = synthesize(agents)
    total_latency = round((perf_counter() - started) * 1000, 3)
    historical_correct, historical_evaluated = historical_accuracy_counts(snapshot.symbol)
    metrics = AnalysisMetrics(
        latency_ms=total_latency,
        historical_signal_accuracy_percent=historical_accuracy(snapshot.symbol),
        portfolio_concentration_score=portfolio_concentration(profile),
        data_completeness_percent=data_completeness(agents),
        agents_completed=sum(agent.status == AgentStatus.completed for agent in agents), agents_expected=4,
        historical_signal_correct=historical_correct,
        historical_signal_evaluated=historical_evaluated,
    )
    reasoning = [
        f"Loaded the stored {profile.risk_profile} profile and validated {snapshot.symbol} simulated market data.",
        f"Ran four independent agents concurrently in {orchestration_latency:.3f} ms.",
        "Combined only structured agent evidence using deterministic classification and confidence rules.",
    ]
    if synthesis.conflicts:
        reasoning.append("Reduced confidence because agent classifications conflict or vary.")
    if synthesis.missing_evidence:
        reasoning.append("Reduced confidence because one or more evidence inputs are missing.")
    analysis_id = str(uuid4())
    decision_lab = build_decision_lab(analysis_id, snapshot, profile, agents, synthesis)
    response = AnalysisResponse(
        analysis_id=analysis_id, symbol=snapshot.symbol, profile=profile, market_snapshot=snapshot,
        market_signal=market_signal, agents=agents, synthesis=synthesis,
        sources=_deduplicate_sources(agents), reasoning_trace=reasoning, metrics=metrics,
        warnings=list(dict.fromkeys(warnings)), disclaimer=DISCLAIMER, decision_lab=decision_lab,
    )
    serialized = response.model_dump(mode="json")
    with connection() as conn:
        conn.execute("""
          INSERT INTO analysis_logs
          (analysis_id,user_id,symbol,market_classification,recommendation,confidence,latency_ms,
           historical_accuracy,concentration_score,data_completeness,agent_outputs_json,sources_json,warnings_json,response_json)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (response.analysis_id, profile.user_id, snapshot.symbol, market_signal.value,
                synthesis.personalized_guidance, synthesis.confidence, metrics.latency_ms,
                metrics.historical_signal_accuracy_percent, metrics.portfolio_concentration_score,
                metrics.data_completeness_percent, encode_json(serialized["agents"]),
                encode_json(serialized["sources"]), encode_json(serialized["warnings"]), encode_json(serialized)))
    return response
