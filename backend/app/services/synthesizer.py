"""Deterministic, evidence-aware synthesis rules."""
from app.schemas import AgentOutput, AgentStatus, Classification, Synthesis

SCORES = {
    Classification.bullish: 1, Classification.positive: 1, Classification.strong: 1, Classification.suitable: 1,
    Classification.bearish: -1, Classification.negative: -1, Classification.weak: -1, Classification.unsuitable: -1,
    Classification.neutral: 0, Classification.mixed: 0, Classification.insufficient_data: 0,
}


def synthesize(agents: list[AgentOutput]) -> tuple[Classification, Synthesis, list[str]]:
    cited = [agent for agent in agents if agent.sources and agent.evidence]
    missing = [f"{agent.agent}: {agent.status.value}" for agent in agents if agent.status != AgentStatus.completed]
    warnings = [warning for agent in agents for warning in agent.warnings]
    if not cited:
        synthesis = Synthesis(classification=Classification.insufficient_data, confidence=0,
                              summary="No cited evidence is available, so no market conclusion was produced.",
                              personalized_guidance="Investigate further and obtain verified evidence before drawing a conclusion.",
                              conflicts=[], risk_flags=[], evidence_used=[], missing_evidence=missing or ["All cited evidence"])
        return Classification.insufficient_data, synthesis, warnings

    directional = [(agent.agent, SCORES[agent.classification]) for agent in agents if agent.status == AgentStatus.completed]
    total = sum(score for _, score in directional)
    market_scores = [score for name, score in directional if name != "behavioral"]
    market_total = sum(market_scores)
    market_signal = Classification.bullish if market_total > 0 else Classification.bearish if market_total < 0 else Classification.neutral
    has_conflict = any(score > 0 for _, score in directional) and any(score < 0 for _, score in directional)
    conflicts = []
    if has_conflict:
        conflicts.append("Agents contain both favorable and unfavorable classifications")
    elif len(set(score for _, score in directional)) > 1:
        conflicts.append("Agent classifications vary between directional and neutral evidence")
    available_confidence = [agent.confidence for agent in agents if agent.status == AgentStatus.completed]
    confidence = sum(available_confidence) / len(available_confidence) if available_confidence else 0
    confidence -= len(missing) * 12
    confidence -= len(conflicts) * 10
    confidence += min(8, abs(total) * 2)
    confidence_value = max(0, min(95, round(confidence)))
    behavioral = next((agent for agent in agents if agent.agent == "behavioral"), None)
    if behavioral and behavioral.classification == Classification.unsuitable:
        guidance = "Consider monitoring this research cautiously; the observed volatility or concentration does not fit the stored profile."
    elif behavioral and behavioral.classification == Classification.suitable:
        guidance = "Consider the cited evidence in the context of the longer horizon and risk capacity, while monitoring the listed risks."
    else:
        guidance = "Monitor the conflicting evidence and investigate further before treating the signal as relevant to the stored profile."
    risk_flags = list(dict.fromkeys(risk for agent in agents for risk in agent.risks))
    evidence_used = [item for agent in cited for item in agent.evidence]
    synthesis = Synthesis(classification=market_signal, confidence=confidence_value,
                          summary=f"Deterministic synthesis is {market_signal.value} with {len(cited)} cited agent outputs.",
                          personalized_guidance=guidance, conflicts=conflicts, risk_flags=risk_flags,
                          evidence_used=evidence_used, missing_evidence=missing)
    return market_signal, synthesis, warnings
