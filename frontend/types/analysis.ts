export type AgentStatus = "completed" | "unavailable" | "degraded" | "failed";
export type Classification = "bullish" | "neutral" | "bearish" | "strong" | "mixed" | "weak" | "positive" | "negative" | "suitable" | "unsuitable" | "insufficient_data";
export type RiskProfile = "conservative" | "moderate" | "aggressive";
export interface Source { title: string; document: string; date: string; chunk_id: string | null }
export interface Holding { symbol: string; weight: number; [key: string]: unknown }
export interface Interaction { action: string; symbol?: string; [key: string]: unknown }
export interface ProfileInput { user_id: string; risk_profile: RiskProfile; investment_horizon_years: number; maximum_volatility: number; portfolio: Holding[]; watchlist: string[]; interaction_history: Interaction[] }
export interface Profile extends ProfileInput { id: number; created_at: string; updated_at: string }
export interface MarketSnapshot { symbol: string; company_name: string; current_price: number; previous_close: number; five_day_return: number; twenty_day_return: number; twenty_day_moving_average: number; current_volume: number; average_volume: number; volatility: number; drawdown: number; pe_ratio: number; revenue_growth: number; debt_to_equity_ratio: number; data_timestamp: string; simulated_data: boolean }
export interface AgentOutput { agent: "technical" | "sentiment" | "fundamental" | "behavioral"; status: AgentStatus; classification: Classification; confidence: number; summary: string; evidence: string[]; risks: string[]; sources: Source[]; latency_ms: number; warnings: string[] }
export interface Metrics { latency_ms: number; historical_signal_accuracy_percent: number; portfolio_concentration_score: number; data_completeness_percent: number; agents_completed: number; agents_expected: number; historical_signal_correct?: number; historical_signal_evaluated?: number }
export interface Synthesis { classification: Classification; confidence: number; summary: string; personalized_guidance: string; conflicts: string[]; risk_flags: string[]; evidence_used: string[]; missing_evidence: string[] }
export type DecisionLabSignal = Classification | "moderately_bullish" | "moderately_bearish";
export type ReplayStatus = "complete" | "degraded" | "failed";
export interface DecisionLab {
  investigation_id: string;
  event: { title: string; description: string };
  committee: { support: number; oppose: number; abstain: number; consensus_score: number; fragility_score: number };
  devils_advocate: { signal: DecisionLabSignal; confidence: number; challenge: string; evidence: string[] };
  evidence_verification: { coverage_score: number; verified_claims: number; total_claims: number; unsupported_claims: string[] };
  missing_information: { gaps: string[]; confidence_penalty: number };
  decision_dna: { factor: string; weight: number }[];
  change_our_mind: string[];
  stress_test: { normal_signal: DecisionLabSignal; normal_confidence: number; stressed_signal: DecisionLabSignal; stressed_confidence: number; robustness: "low" | "medium" | "high" | string; removed_evidence: string };
  counterfactual: { investment_amount: number; risk_before: number; risk_after: number; sector_exposure_before: number; sector_exposure_after: number; diversification_before: number; diversification_after: number; interpretation: string };
  replay: { order: number; stage: string; status: ReplayStatus; message: string }[];
}
export interface AnalysisResponse { analysis_id: string; symbol: string; generated_at: string; profile: Profile; market_snapshot: MarketSnapshot; market_signal: Classification; agents: AgentOutput[]; synthesis: Synthesis; sources: Source[]; reasoning_trace: string[]; metrics: Metrics; warnings: string[]; disclaimer: string; decision_lab?: DecisionLab }
export interface HealthResponse { status: string; service: string; version: string }
