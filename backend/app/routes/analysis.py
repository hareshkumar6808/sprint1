from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.database import connection, encode_json
from app.routes.profiles import get_profile
from app.schemas import (AnalysisMetrics, AnalysisResponse, AnalyzeRequest, AgentStatus,
                         Classification, Source)
from app.services.market_data import ResilientMarketDataProvider, SymbolNotFoundError
from app.services.decision_lab import build_decision_lab
from app.services.metrics import (data_completeness, historical_accuracy,
                                  historical_accuracy_counts, portfolio_concentration)
from app.services.orchestrator import run_agents
from app.services.synthesizer import synthesize
from app.services.instruments import find_by_symbol, get_instrument
from app.services.market_data import IncompleteMarketDataError
from app.services.committee import expanded_committee

router = APIRouter(prefix="/analyze", tags=["analysis"])
provider = ResilientMarketDataProvider()
DISCLAIMER = ("Educational research intelligence. Market data may be delayed or simulated. This is not financial "
              "advice, a direct trading instruction, a guaranteed outcome, or suitable for order execution.")


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
    with connection() as conn:
        decisions = conn.execute("SELECT action,ticker,created_at FROM user_decisions WHERE user_id=? ORDER BY id DESC LIMIT 20",
                                 (profile.user_id,)).fetchall()
    research_profile = profile.model_copy(update={"interaction_history": [*profile.interaction_history,
        *[{"action": row["action"], "symbol": row["ticker"], "timestamp": row["created_at"]} for row in decisions]]})
    try:
        instrument = get_instrument(payload.instrument_key) if payload.instrument_key else find_by_symbol(payload.symbol)
        snapshot = provider.get_instrument_snapshot(instrument) if instrument and payload.instrument_key else provider.get_snapshot(payload.symbol)
    except (SymbolNotFoundError, IncompleteMarketDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    agents, orchestration_latency = await run_agents(snapshot, research_profile)
    market_signal, synthesis, warnings = synthesize(agents)
    total_latency = round((perf_counter() - started) * 1000, 3)
    historical_correct, historical_evaluated = historical_accuracy_counts(snapshot.symbol)
    fundamental = next((agent for agent in agents if agent.agent == "fundamental"), None)
    directional = [agent.classification.value for agent in agents if agent.status == AgentStatus.completed]
    largest = max((directional.count(value) for value in set(directional)), default=0)
    cited_claims = sum(len(agent.evidence) for agent in agents if agent.sources)
    total_claims = sum(len(agent.evidence) for agent in agents)
    metrics = AnalysisMetrics(
        latency_ms=total_latency,
        historical_signal_accuracy_percent=historical_accuracy(snapshot.symbol),
        portfolio_concentration_score=portfolio_concentration(profile),
        data_completeness_percent=data_completeness(agents),
        agents_completed=sum(agent.status == AgentStatus.completed for agent in agents), agents_expected=4,
        historical_signal_correct=historical_correct,
        historical_signal_evaluated=historical_evaluated,
        per_agent_latency_ms={agent.agent: agent.latency_ms for agent in agents},
        retrieval_latency_ms=fundamental.retrieval_latency_ms if fundamental else 0,
        documents_retrieved=len({source.document for source in (fundamental.sources if fundamental else [])}),
        chunks_retrieved=fundamental.chunks_retrieved if fundamental else 0,
        evidence_coverage_percent=round(cited_claims / total_claims * 100, 2) if total_claims else 0,
        agent_agreement_percent=round(largest / len(directional) * 100, 2) if directional else 0,
        fallback_activations=sum(agent.runtime_mode == "deterministic_fallback" for agent in agents)
            + int(bool(snapshot.fallback_reason)) + int(bool(fundamental and fundamental.retrieval_mode == "tfidf_fallback")),
        runtime_mode=("xai" if any(agent.runtime_mode == "xai" for agent in agents) else
                      "llm" if any(agent.runtime_mode == "llm" for agent in agents) else "deterministic_fallback"),
        retrieval_mode=fundamental.retrieval_mode if fundamental and fundamental.retrieval_mode else "unavailable",
        market_data_mode="simulated" if snapshot.simulated_data else snapshot.data_mode,
    )
    if snapshot.data_status == "unverified_delay":
        synthesis = synthesis.model_copy(update={"confidence": max(0, synthesis.confidence - 8),
            "risk_flags": [*synthesis.risk_flags, "Yahoo Finance delay is not independently verified"]})
    reasoning = [
        f"Loaded the stored {profile.risk_profile} profile and validated {snapshot.symbol} {metrics.market_data_mode} market data.",
        f"Ran four independent agents concurrently in {orchestration_latency:.3f} ms.",
        "Combined only structured agent evidence using deterministic classification and confidence rules.",
    ]
    if synthesis.conflicts:
        reasoning.append("Reduced confidence because agent classifications conflict or vary.")
    if synthesis.missing_evidence:
        reasoning.append("Reduced confidence because one or more evidence inputs are missing.")
    analysis_id = str(uuid4())
    decision_lab = build_decision_lab(analysis_id, snapshot, profile, agents, synthesis)
    analytical_units = await expanded_committee(agents, profile, snapshot, synthesis)
    regime = "high_volatility" if snapshot.volatility >= 30 else "unknown"
    completed_weights = {agent.agent: agent.confidence for agent in agents if agent.status == AgentStatus.completed}
    weight_total = sum(completed_weights.values()) or 1
    synthesis_weights = {name: round(value / weight_total, 4) for name, value in completed_weights.items()}
    response = AnalysisResponse(
        analysis_id=analysis_id, symbol=snapshot.symbol, profile=profile, market_snapshot=snapshot,
        market_signal=market_signal, agents=agents, synthesis=synthesis,
        sources=_deduplicate_sources(agents), reasoning_trace=reasoning, metrics=metrics,
        warnings=list(dict.fromkeys(warnings)), disclaimer=DISCLAIMER, decision_lab=decision_lab,
        analytical_units=analytical_units, regime=regime, synthesis_weights=synthesis_weights,
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
        features = {"one_day_return": snapshot.one_day_return, "five_day_return": snapshot.five_day_return,
                    "twenty_day_return": snapshot.twenty_day_return, "volume_ratio": (snapshot.current_volume / snapshot.average_volume if snapshot.average_volume else None),
                    "volatility": snapshot.volatility, "drawdown": snapshot.drawdown}
        event_type = "volume_anomaly" if features["volume_ratio"] is not None and features["volume_ratio"] >= 1.4 else "analysis_opened"
        event_key = f"{snapshot.symbol}:{event_type}:{snapshot.data_timestamp.date().isoformat()}"
        conn.execute("""INSERT OR IGNORE INTO events
          (event_key,instrument_key,symbol,event_type,severity,evidence_json,occurred_at) VALUES (?,?,?,?,?,?,?)""",
          (event_key, snapshot.instrument_key, snapshot.symbol, event_type, "medium" if event_type == "volume_anomaly" else "info",
           encode_json(features), snapshot.data_timestamp.isoformat()))
        conn.execute("""INSERT OR IGNORE INTO predictions
          (analysis_id,instrument_key,symbol,prediction_timestamp,price,direction,raw_confidence,calibrated_confidence,horizon_days,evidence_snapshot_json,version)
          VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (response.analysis_id, snapshot.instrument_key, snapshot.symbol,
          response.generated_at.isoformat(), snapshot.current_price, market_signal.value, synthesis.confidence, None, 20,
          encode_json({"sources": [source.model_dump(mode="json") for source in response.sources], "weights": synthesis_weights}), "committee-1.0"))
    return response
