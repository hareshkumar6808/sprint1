export type AgentStatus = "completed"|"unavailable"|"degraded"|"failed";
export type Classification = "bullish"|"neutral"|"bearish"|"strong"|"mixed"|"weak"|"positive"|"negative"|"suitable"|"unsuitable"|"insufficient_data";
export interface Source { title:string; document:string; date:string; chunk_id:string|null }
export interface AgentOutput { agent:"technical"|"sentiment"|"fundamental"|"behavioral"; status:AgentStatus; classification:Classification; confidence:number; summary:string; evidence:string[]; risks:string[]; sources:Source[]; latency_ms:number; warnings:string[] }
export interface Metrics { latency_ms:number; historical_signal_accuracy_percent:number; portfolio_concentration_score:number; data_completeness_percent:number; agents_completed:number; agents_expected:number }
export interface Synthesis { classification:Classification; confidence:number; summary:string; personalized_guidance:string; conflicts:string[]; risk_flags:string[]; evidence_used:string[]; missing_evidence:string[] }
export interface AnalysisResponse { analysis_id:string; symbol:string; generated_at:string; profile:unknown; market_snapshot:unknown; market_signal:Classification; agents:AgentOutput[]; synthesis:Synthesis; sources:Source[]; reasoning_trace:string[]; metrics:Metrics; warnings:string[]; disclaimer:string }
