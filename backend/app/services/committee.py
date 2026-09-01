"""Expanded three-stage committee built only from validated investigation inputs."""
import asyncio
from datetime import datetime, timezone
from time import perf_counter

from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Profile, Synthesis
from app.services.metrics import portfolio_concentration


def _unit(name: str, role: str, status: AgentStatus, classification: Classification, confidence: int,
          summary: str, evidence: list[str] | None = None, evidence_ids: list[str] | None = None,
          risks: list[str] | None = None, missing: list[str] | None = None, started: float = 0) -> AgentOutput:
    now = datetime.now(timezone.utc)
    return AgentOutput(agent=name, version="1.0", role=role, status=status, classification=classification,
        confidence=confidence, summary=summary, evidence=evidence or [], evidence_ids=evidence_ids or [],
        risks=risks or [], missing_information=missing or [], sources=[], runtime_mode="deterministic_fallback",
        latency_ms=round((perf_counter() - started) * 1000, 3), started_at=now, ended_at=now)


async def _regulatory(core: list[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    fundamental = next((item for item in core if item.agent == "fundamental"), None)
    ids = fundamental.evidence_ids if fundamental else []
    evidence = [item for item in (fundamental.evidence if fundamental else []) if "risk" in item.lower() or "regulat" in item.lower()]
    if not evidence:
        return _unit("regulatory", "regulatory intelligence", AgentStatus.unavailable, Classification.insufficient_data, 0,
                     "No associated regulatory evidence was retrieved; no regulatory claim was inferred.", missing=["Verified regulatory filing or notice"], started=started)
    return _unit("regulatory", "regulatory intelligence", AgentStatus.completed, Classification.mixed, min(70, 45 + len(evidence) * 5),
                 "Regulatory risk language was found in instrument-isolated retrieved evidence.", evidence, ids,
                 risks=evidence[:3], started=started)


async def _macro(snapshot: MarketSnapshot) -> AgentOutput:
    started = perf_counter()
    return _unit("macro_regime", "macro and market regime", AgentStatus.unavailable, Classification.insufficient_data, 0,
                 "Benchmark and macro series are unavailable, so the market regime is unknown.",
                 missing=["Broad-market benchmark series", "Rates, FX, and commodity series"], started=started)


async def _portfolio(profile: Profile, snapshot: MarketSnapshot) -> AgentOutput:
    started = perf_counter()
    if not profile.portfolio:
        return _unit("portfolio_risk", "portfolio risk", AgentStatus.unavailable, Classification.insufficient_data, 0,
                     "Portfolio holdings are unavailable.", missing=["Portfolio holdings and allocations"], started=started)
    concentration = portfolio_concentration(profile)
    classification = Classification.unsuitable if concentration > 60 else Classification.neutral
    evidence = [f"Portfolio concentration score: {concentration:.2f}", f"Analyzed volatility: {snapshot.volatility:.2f}%"]
    return _unit("portfolio_risk", "portfolio risk", AgentStatus.completed, classification, 65,
                 "Portfolio risk is derived from supplied holdings and the selected instrument snapshot.", evidence,
                 [f"profile:{profile.user_id}"], risks=["Concentration exceeds 60"] if concentration > 60 else [], started=started)


def _adversarial(core: list[AgentOutput], stage1: list[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    completed = [item for item in [*core, *stage1] if item.status == AgentStatus.completed and item.evidence]
    negative = [item for item in completed if item.classification in {Classification.bearish, Classification.negative, Classification.weak, Classification.unsuitable}]
    chosen = max(negative or completed, key=lambda item: item.confidence, default=None)
    if not chosen:
        return _unit("devils_advocate", "strongest sourced counterargument", AgentStatus.unavailable, Classification.insufficient_data, 0,
                     "No cited counterargument is available.", missing=["Opposing cited evidence"], started=started)
    return _unit("devils_advocate", "strongest sourced counterargument", AgentStatus.completed, chosen.classification,
                 chosen.confidence, f"Strongest counterargument: {chosen.summary}", chosen.evidence[:3], chosen.evidence_ids,
                 risks=chosen.risks[:3], started=started)


def _missing(units: list[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    gaps = [gap for item in units for gap in item.missing_information]
    gaps += [f"{item.agent} unavailable" for item in units if item.status != AgentStatus.completed]
    return _unit("missing_information", "missing information and confidence impact", AgentStatus.completed,
                 Classification.insufficient_data if gaps else Classification.neutral, max(0, 80 - len(gaps) * 8),
                 f"{len(gaps)} material information gaps were identified.", missing=list(dict.fromkeys(gaps)), started=started)


def _verify(units: list[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    claims = [(claim, item) for item in units for claim in item.evidence]
    supported = [(claim, item) for claim, item in claims if item.evidence_ids or item.sources]
    unsupported = [claim for claim, item in claims if not item.evidence_ids and not item.sources]
    confidence = round(len(supported) / len(claims) * 100) if claims else 0
    return _unit("evidence_verification", "claim-to-evidence verification", AgentStatus.completed,
                 Classification.neutral if supported else Classification.insufficient_data, confidence,
                 f"{len(supported)} of {len(claims)} evidence claims map to supplied evidence identifiers.",
                 [claim for claim, _ in supported[:5]], [eid for _, item in supported for eid in item.evidence_ids][:10],
                 risks=[f"Unsupported claim removed: {claim}" for claim in unsupported[:5]], started=started)


def _committee(units: list[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    positive = {Classification.bullish, Classification.positive, Classification.strong, Classification.suitable}
    negative = {Classification.bearish, Classification.negative, Classification.weak, Classification.unsuitable}
    votes = [1 if item.classification in positive else -1 if item.classification in negative else 0 for item in units if item.status == AgentStatus.completed]
    score = sum(votes)
    classification = Classification.bullish if score > 1 else Classification.bearish if score < -1 else Classification.neutral
    agreement = round(max(votes.count(1), votes.count(-1), votes.count(0)) / len(votes) * 100) if votes else 0
    return _unit("committee", "committee and conflict engine", AgentStatus.completed, classification, agreement,
                 f"Committee recorded {votes.count(1)} supportive, {votes.count(-1)} opposing, and {votes.count(0)} neutral votes.",
                 [f"{item.agent}: {item.classification.value}" for item in units], [eid for item in units for eid in item.evidence_ids], started=started)


async def expanded_committee(core: list[AgentOutput], profile: Profile, snapshot: MarketSnapshot,
                             synthesis: Synthesis) -> list[AgentOutput]:
    stage1 = list(await asyncio.gather(_regulatory(core), _macro(snapshot), _portfolio(profile, snapshot)))
    adversarial = _adversarial(core, stage1)
    missing = _missing([*core, *stage1])
    verification = _verify([*core, *stage1, adversarial])
    committee = _committee([*core, *stage1, adversarial])
    final = _unit("synthesis", "bounded final synthesis", AgentStatus.completed, synthesis.classification,
                  synthesis.confidence, synthesis.summary, synthesis.evidence_used,
                  [eid for item in [*core, *stage1, adversarial, verification] for eid in item.evidence_ids],
                  synthesis.risk_flags, synthesis.missing_evidence)
    return [*core, *stage1, adversarial, missing, verification, committee, final]
