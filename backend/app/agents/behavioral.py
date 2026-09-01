"""Risk-profile and portfolio suitability agent."""
from time import perf_counter

from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Profile, Source
from app.services.metrics import portfolio_concentration


async def run(profile: Profile, snapshot: MarketSnapshot) -> AgentOutput:
    started = perf_counter()
    score = 0
    if snapshot.volatility > profile.maximum_volatility:
        score -= 2
    else:
        score += 1
    score += 1 if profile.investment_horizon_years >= 5 else -1
    score += {"conservative": -1, "moderate": 0, "aggressive": 2}[profile.risk_profile]
    concentration = portfolio_concentration(profile)
    if concentration > 60:
        score -= 1
    classification = Classification.suitable if score >= 2 else Classification.unsuitable if score <= -1 else Classification.neutral
    warnings = []
    if snapshot.volatility > profile.maximum_volatility:
        warnings.append(f"Stock volatility {snapshot.volatility:.1f}% exceeds the profile limit of {profile.maximum_volatility:.1f}%")
    if not profile.interaction_history:
        warnings.append("No behavioral interaction history is available")
    evidence = [f"Risk profile: {profile.risk_profile}", f"Investment horizon: {profile.investment_horizon_years} years",
                f"Maximum volatility: {profile.maximum_volatility:.1f}%", f"Portfolio concentration score: {concentration:.2f}",
                f"Recorded interactions: {len(profile.interaction_history)}"]
    return AgentOutput(agent="behavioral", status=AgentStatus.completed, classification=classification,
                       confidence=72 if profile.interaction_history else 62,
                       summary=f"The same market snapshot is {classification.value} for this {profile.risk_profile} profile.",
                       evidence=evidence, risks=warnings,
                       sources=[Source(title="Stored investor profile", document=f"profile:{profile.user_id}",
                                       date=snapshot.data_timestamp.date(), chunk_id=None)],
                       latency_ms=round((perf_counter() - started) * 1000, 3), warnings=warnings)
