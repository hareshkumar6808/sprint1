import type { DecisionLab } from "@/types/analysis";

export const DECISION_LAB_PREVIEW: DecisionLab = {
  investigation_id: "INV-DEMO-PREVIEW",
  event: { title: "Volume anomaly detected", description: "Trading volume moved above its recent average while directional evidence remained mixed." },
  committee: { support: 2, oppose: 1, abstain: 1, consensus_score: 68, fragility_score: 32 },
  devils_advocate: { signal: "bearish", confidence: 64, challenge: "The apparent momentum may be short-lived if elevated volume reflects distribution rather than accumulation.", evidence: ["Recent price strength is not confirmed across every evidence source.", "Portfolio concentration increases the cost of a wrong directional call."] },
  evidence_verification: { coverage_score: 88, verified_claims: 7, total_claims: 8, unsupported_claims: ["The cause of the volume spike is not verified."] },
  missing_information: { gaps: ["No verified management commentary for the detected event."], confidence_penalty: 8 },
  decision_dna: [{ factor: "Fundamentals", weight: 31 }, { factor: "Technical", weight: 29 }, { factor: "Sentiment", weight: 18 }, { factor: "Portfolio fit", weight: 22 }],
  change_our_mind: ["Price closes below the 20-day moving average on sustained volume.", "Verified filings materially weaken the growth outlook.", "New evidence resolves the current agent disagreement."],
  stress_test: { normal_signal: "moderately_bullish", normal_confidence: 76, stressed_signal: "neutral", stressed_confidence: 58, robustness: "medium", removed_evidence: "The strongest positive technical observation" },
  counterfactual: { investment_amount: 20000, risk_before: 61, risk_after: 68, sector_exposure_before: 19, sector_exposure_after: 27, diversification_before: 74, diversification_after: 69, interpretation: "This simulated allocation increases concentration and portfolio risk; review the position size against your stated risk profile." },
  replay: [{ order: 1, stage: "investigation_started", status: "complete", message: "Investigation started" }, { order: 2, stage: "agent_committee", status: "complete", message: "Independent agent positions recorded" }, { order: 3, stage: "evidence_verification", status: "degraded", message: "One claim could not be verified" }, { order: 4, stage: "synthesis_complete", status: "complete", message: "Personalized decision view prepared" }],
};
