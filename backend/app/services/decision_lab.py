"""Deterministic adversarial analysis derived only from existing investigation data."""
from collections import defaultdict
from datetime import datetime, timezone
from math import floor

from app.schemas import (AgentOutput, AgentStatus, Classification, CommitteeResult,
                         Counterfactual, DecisionEvent, DecisionFactor, DecisionLab,
                         DevilsAdvocate, EvidenceVerification, MarketSnapshot,
                         MissingInformation, Profile, ReplayStep, StressTest, Synthesis)
from app.services.market_data import calculate_features
from app.services.metrics import portfolio_concentration

POSITIVE = {Classification.bullish, Classification.positive, Classification.strong, Classification.suitable}
NEGATIVE = {Classification.bearish, Classification.negative, Classification.weak, Classification.unsuitable}
SECTORS = {"RELIANCE": "Energy", "TCS": "Technology", "INFY": "Technology"}


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _vote(agent: AgentOutput) -> int:
    if agent.status != AgentStatus.completed:
        return 0
    return 1 if agent.classification in POSITIVE else -1 if agent.classification in NEGATIVE else 0


def _signal(score: int) -> str:
    return "bullish" if score > 0 else "bearish" if score < 0 else "neutral"


def _committee(agents: list[AgentOutput]) -> CommitteeResult:
    votes = [_vote(agent) for agent in agents]
    support, oppose, abstain = votes.count(1), votes.count(-1), votes.count(0)
    total = len(votes) or 1
    largest_group = max(support, oppose, abstain)
    consensus = _clamp(largest_group / total * 100)
    # Baseline disagreement plus an explicit penalty when both directional camps exist.
    fragility = _clamp(100 - consensus + min(support, oppose) * 20)
    return CommitteeResult(support=support, oppose=oppose, abstain=abstain,
                           consensus_score=consensus, fragility_score=fragility)


def _devils_advocate(agents: list[AgentOutput], committee: CommitteeResult) -> DevilsAdvocate:
    majority = 1 if committee.support > committee.oppose else -1 if committee.oppose > committee.support else 0
    challengers = [agent for agent in agents if _vote(agent) == -majority and agent.evidence]
    if challengers:
        strongest = max(challengers, key=lambda item: (item.confidence, item.agent))
        return DevilsAdvocate(signal=_signal(-majority), confidence=strongest.confidence,
                              challenge=strongest.summary, evidence=strongest.evidence[:3])
    caution = [risk for agent in agents for risk in agent.risks]
    signal = "caution" if majority == 0 else _signal(-majority)
    return DevilsAdvocate(
        signal=signal, confidence=_clamp(35 + len(caution) * 5),
        challenge=(caution[0] if caution else
                   "No sourced opposing claim was found; the adversarial challenge has limited evidence."),
        evidence=caution[:3],
    )


def _verify(agents: list[AgentOutput]) -> EvidenceVerification:
    claims = [(claim, bool(agent.sources)) for agent in agents for claim in agent.evidence]
    verified = sum(is_cited for _, is_cited in claims)
    unsupported = [claim for claim, is_cited in claims if not is_cited]
    total = len(claims)
    return EvidenceVerification(coverage_score=_clamp(verified / total * 100) if total else 0,
                                verified_claims=verified, total_claims=total,
                                unsupported_claims=unsupported)


def _missing(agents: list[AgentOutput], snapshot: MarketSnapshot, profile: Profile) -> MissingInformation:
    gaps: list[str] = []
    penalty = 0
    for agent in agents:
        if agent.status != AgentStatus.completed:
            gaps.append(f"{agent.agent.title()} intelligence is {agent.status.value}")
            penalty += 12
        elif not agent.sources:
            gaps.append(f"{agent.agent.title()} intelligence has no source attribution")
            penalty += 8
    if not profile.portfolio:
        gaps.append("Portfolio holdings are unavailable")
        penalty += 6
    if not profile.interaction_history:
        gaps.append("Behavioral interaction history is unavailable")
        penalty += 4
    age_days = (datetime.now(timezone.utc).date() - snapshot.data_timestamp.date()).days
    if age_days > 1:
        gaps.append(f"Market snapshot is {age_days} days old")
        penalty += min(15, age_days)
    return MissingInformation(gaps=gaps, confidence_penalty=_clamp(penalty))


def _weights(raw: list[tuple[str, float]]) -> list[DecisionFactor]:
    total = sum(value for _, value in raw) or 1
    exact = [(name, value * 100 / total) for name, value in raw]
    values = [floor(value) for _, value in exact]
    remainder = 100 - sum(values)
    order = sorted(range(len(exact)), key=lambda index: (-(exact[index][1] - values[index]), index))
    for index in order[:remainder]:
        values[index] += 1
    return [DecisionFactor(factor=name, weight=values[index]) for index, (name, _) in enumerate(raw)]


def _dna(agents: list[AgentOutput], verification: EvidenceVerification, profile: Profile) -> list[DecisionFactor]:
    by_name = {agent.agent: agent for agent in agents}
    score = lambda name: by_name[name].confidence if by_name.get(name) and by_name[name].status == AgentStatus.completed else 0
    return _weights([
        ("Momentum", score("technical")), ("Fundamentals", score("fundamental")),
        ("Sentiment", score("sentiment")),
        ("Portfolio Risk", 60 + min(40, portfolio_concentration(profile))),
        ("Behavioral", score("behavioral")), ("Evidence Quality", verification.coverage_score),
    ])


def _change_conditions(snapshot: MarketSnapshot) -> list[str]:
    features = calculate_features(snapshot)
    conditions = [
        "A new verified filing contradicts the retrieved revenue, margin, debt, or guidance evidence.",
        f"Volatility moves beyond the investor's configured risk threshold.",
    ]
    if snapshot.twenty_day_moving_average is not None:
        direction = "below" if snapshot.current_price >= snapshot.twenty_day_moving_average else "above"
        conditions.insert(0, f"Price closes {direction} the current 20-day average of ₹{snapshot.twenty_day_moving_average:,.2f}.")
    if snapshot.twenty_day_return is not None:
        conditions.insert(1, f"The current {snapshot.twenty_day_return:+.1f}% 20-day momentum reverses direction.")
    if features.volume_ratio is not None:
        conditions.insert(2, f"Volume normalizes from {features.volume_ratio:.2f}x average or expands in the opposite price direction.")
    return conditions


def _stress(agents: list[AgentOutput], synthesis: Synthesis) -> StressTest:
    contributors = [agent for agent in agents if _vote(agent) and agent.evidence and agent.sources]
    strongest = max(contributors, key=lambda item: (item.confidence, item.agent), default=None)
    remaining = [agent for agent in agents if agent is not strongest]
    stressed_score = sum(_vote(agent) for agent in remaining)
    removed_confidence = strongest.confidence if strongest else 0
    stressed_confidence = _clamp(synthesis.confidence - max(8, round(removed_confidence / max(1, len(agents)))))
    stressed_signal = _signal(stressed_score)
    changed = stressed_signal != synthesis.classification.value
    drop = synthesis.confidence - stressed_confidence
    robustness = "low" if changed else "high" if drop <= 12 else "medium"
    description = (f"{strongest.agent.title()} contribution ({strongest.confidence}% confidence): "
                   f"{strongest.evidence[0]}" if strongest else "No cited directional evidence was available to remove.")
    return StressTest(normal_signal=synthesis.classification.value, normal_confidence=synthesis.confidence,
                      stressed_signal=stressed_signal, stressed_confidence=stressed_confidence,
                      robustness=robustness, removed_evidence=description)


def _holding_value(item: dict[str, object]) -> float:
    for key in ("value", "weight", "allocation_percent", "percentage"):
        if key in item:
            return max(0.0, float(item[key]))
    if "quantity" in item and "price" in item:
        return max(0.0, float(item["quantity"]) * float(item["price"]))
    return 0.0


def _portfolio(snapshot: MarketSnapshot, profile: Profile) -> Counterfactual:
    investment = 20_000
    holdings = [(str(item.get("symbol", "")).upper(), _holding_value(item)) for item in profile.portfolio]
    holdings = [(symbol, value) for symbol, value in holdings if value > 0]
    # Allocation-only profiles lack rupee values; normalize them to a disclosed ₹2 lakh demo portfolio.
    raw_total = sum(value for _, value in holdings)
    assumed = not holdings or raw_total <= 100
    base_total = 200_000.0 if assumed else raw_total
    normalized = [(symbol, (value / raw_total * base_total) if raw_total else 0.0) for symbol, value in holdings]
    sector = SECTORS.get(snapshot.symbol, "Other")
    sector_before_value = sum(value for symbol, value in normalized if SECTORS.get(symbol, "Other") == sector)
    before_exposure = _clamp(sector_before_value / base_total * 100) if base_total else 0
    after_exposure = _clamp((sector_before_value + investment) / (base_total + investment) * 100)
    concentration = portfolio_concentration(profile)
    before_diversification = _clamp(100 - concentration)
    target_before = next((value for symbol, value in normalized if symbol == snapshot.symbol), 0.0)
    values_after = [value for symbol, value in normalized if symbol != snapshot.symbol] + [target_before + investment]
    weights_after = [value / (base_total + investment) for value in values_after]
    after_concentration = ((max(weights_after, default=0) * 100) + sum(w * w for w in weights_after) * 100) / 2
    after_diversification = _clamp(100 - after_concentration)
    risk_before = _clamp(35 + concentration * .35 + {"conservative": 8, "moderate": 3, "aggressive": 0}[profile.risk_profile])
    risk_after = _clamp(risk_before + (snapshot.volatility - profile.maximum_volatility) * .3
                        + (after_exposure - before_exposure) * .25)
    assumption = " using a deterministic ₹2,00,000 demo portfolio assumption" if assumed else ""
    return Counterfactual(investment_amount=investment, risk_before=risk_before, risk_after=risk_after,
                          sector_exposure_before=before_exposure, sector_exposure_after=after_exposure,
                          diversification_before=before_diversification,
                          diversification_after=after_diversification,
                          interpretation=(f"Adding ₹20,000 of {snapshot.symbol} changes {sector} exposure from "
                                          f"{before_exposure}% to {after_exposure}%{assumption}; these are simulated, not live values."))


def build_decision_lab(investigation_id: str, snapshot: MarketSnapshot, profile: Profile,
                       agents: list[AgentOutput], synthesis: Synthesis) -> DecisionLab:
    committee = _committee(agents)
    verification = _verify(agents)
    missing = _missing(agents, snapshot, profile)
    features = calculate_features(snapshot)
    event_title = "Volume anomaly detected" if features.volume_ratio is not None and features.volume_ratio >= 1.4 else "Market movement detected"
    degraded = any(agent.status != AgentStatus.completed for agent in agents)
    replay_names = [
        ("investigation_started", "Investigation started"),
        ("market_event_detected", f"{event_title} for {snapshot.symbol}"),
        ("parallel_agents_completed", "Parallel specialist agents completed"),
        ("retrieval_completed", "Existing filing and source retrieval completed"),
        ("conflict_checked", "Committee votes and conflict were checked"),
        ("devils_advocate_completed", "Devil's Advocate challenge completed"),
        ("evidence_verified", "Material evidence claims were checked for citations"),
        ("missing_information_assessed", "Missing intelligence was assessed"),
        ("final_synthesis_generated", "Existing deterministic synthesis was retained"),
        ("portfolio_simulation_completed", "Personalized ₹20,000 simulation completed"),
    ]
    replay = [ReplayStep(order=index, stage=stage,
                         status="degraded" if degraded and stage in {"parallel_agents_completed", "missing_information_assessed"} else "complete",
                         message=message) for index, (stage, message) in enumerate(replay_names, 1)]
    return DecisionLab(
        investigation_id=f"INV-{snapshot.symbol}-{investigation_id[:8].upper()}",
        event=DecisionEvent(title=event_title,
                            description=(f"{snapshot.symbol} volume is {features.volume_ratio:.2f}x its average; "
                                         f"data mode is {snapshot.data_mode}." if features.volume_ratio is not None else
                                         f"{snapshot.symbol} volume anomaly is unavailable; data mode is {snapshot.data_mode}.")),
        committee=committee, devils_advocate=_devils_advocate(agents, committee),
        evidence_verification=verification, missing_information=missing,
        decision_dna=_dna(agents, verification, profile), change_our_mind=_change_conditions(snapshot),
        stress_test=_stress(agents, synthesis), counterfactual=_portfolio(snapshot, profile), replay=replay,
    )
