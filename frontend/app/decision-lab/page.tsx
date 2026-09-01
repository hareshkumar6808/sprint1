"use client";

import { AppLayout } from "@/components/layout";
import { DecisionLab } from "@/components/DecisionLab";
import { DECISION_LAB_PREVIEW } from "@/lib/decision-lab-fixture";
import type { AnalysisResponse } from "@/types/analysis";

const DEMO_ANALYSIS: AnalysisResponse = {
  analysis_id: "a-full-decision-lab-preview",
  symbol: "RELIANCE",
  generated_at: new Date().toISOString(),
  market_snapshot: {
    company_name: "Reliance Industries Limited",
    symbol: "RELIANCE",
    current_price: 3100,
    previous_close: 3050,
    five_day_return: 2.3,
    twenty_day_return: 5.1,
    twenty_day_moving_average: 3020,
    current_volume: 3200000,
    average_volume: 2500000,
    rsi: 68,
    volatility: 18.5,
    drawdown: 12.3,
    provider_name: "NSE Live",
    data_timestamp: new Date().toISOString(),
    data_mode: "live",
    simulated_data: false,
    fallback_reason: null,
    pe_ratio: 28.5,
    revenue_growth: 12.0,
    debt_to_equity_ratio: 0.35,
  },
  market_signal: "bullish",
  synthesis: {
    classification: "bullish",
    confidence: 87,
    summary: "Strong positive momentum with solid fundamentals.",
    personalized_guidance: "Based on your moderate risk profile, consider a measured entry.",
    conflicts: [],
    risk_flags: ["High sector volatility", "Regulatory uncertainty"],
    missing_evidence: [],
    evidence_used: ["Technical: Strong uptrend", "Fundamental: Revenue growth"],
  },
  profile: {
    user_id: "demo-user",
    risk_profile: "moderate",
    investment_horizon_years: 8,
    maximum_volatility: 15,
    portfolio: [],
    watchlist: [],
    interaction_history: [],
    id: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  agents: [
    {
      agent: "technical",
      status: "completed",
      classification: "bullish",
      confidence: 85,
      summary: "Price momentum supports upside.",
      evidence: ["Strong RSI above 60", "Price above 20-day MA"],
      risks: [],
      sources: [],
      latency_ms: 145,
      warnings: [],
    },
    {
      agent: "fundamental",
      status: "completed",
      classification: "bullish",
      confidence: 89,
      summary: "Solid earnings and cash flow.",
      evidence: ["Revenue growth of 12% YoY", "Strong balance sheet"],
      risks: [],
      sources: [],
      latency_ms: 320,
      warnings: [],
    },
    {
      agent: "sentiment",
      status: "completed",
      classification: "neutral",
      confidence: 65,
      summary: "Mixed market sentiment.",
      evidence: ["Positive news flow", "Sector concerns offsetting gains"],
      risks: [],
      sources: [],
      latency_ms: 210,
      warnings: [],
    },
    {
      agent: "behavioral",
      status: "completed",
      classification: "bullish",
      confidence: 88,
      summary: "Risk levels within acceptable parameters.",
      evidence: ["Volatility elevated but manageable", "Within horizon tolerance"],
      risks: [],
      sources: [],
      latency_ms: 156,
      warnings: [],
    },
  ],
  decision_lab: DECISION_LAB_PREVIEW,
  reasoning_trace: [
    "Collected market data from NSE provider",
    "Retrieved historical filing documents for Reliance",
    "Technical agent detected strong price momentum and RSI confirmation",
    "Fundamental agent verified revenue growth and stable cash flow",
    "Sentiment agent noted positive news but some sector headwinds",
    "Risk agent confirmed volatility within acceptable bounds for moderate profile",
    "Devil's advocate challenged sector concentration risk",
    "Evidence verification confirmed 7 of 8 key claims",
    "Synthesized independent signals with personal risk profile",
    "Confidence score adjusted for missing sentiment consensus",
  ],
  sources: [
    {
      title: "5-day moving average shows uptrend continuation",
      document: "NSE Historical Prices",
      date: new Date().toISOString(),
      chunk_id: "chunk-1",
      excerpt: "Technical analysis indicates continuation of uptrend",
      relevance_score: 0.95,
    },
    {
      title: "Revenue increased 12% YoY to ₹2.15 lakh crore",
      document: "Q2 2026 Earnings Report",
      date: new Date().toISOString(),
      chunk_id: "chunk-2",
      excerpt: "Strong financial performance in latest quarter",
      relevance_score: 0.98,
    },
  ],
  metrics: {
    latency_ms: 2340,
    retrieval_latency_ms: 1200,
    chunks_retrieved: 45,
    evidence_coverage_percent: 92,
    agent_agreement_percent: 75,
    fallback_activations: 0,
    portfolio_concentration_score: 7.2,
    data_completeness_percent: 98,
    agents_completed: 4,
    agents_expected: 4,
    market_data_mode: "live",
    runtime_mode: "llm",
    retrieval_mode: "semantic",
    historical_signal_accuracy_percent: 86,
  },
  warnings: ["This preview uses simulated portfolio assumptions and must not be treated as live market evidence."],
  disclaimer: "Educational decision-support only. This analysis is not investment advice and does not guarantee financial outcomes.",
};

export default function DecisionLabPage() {
  return (
    <AppLayout currentPage="decision-lab" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Adversarial intelligence</p>
            <h1>Decision Laboratory</h1>
          </div>
        </div>

        <p className="demo-notice">Simulated preview — this investigation uses illustrative evidence and portfolio assumptions, not a live recommendation.</p>

        <p style={{
          color: "var(--text-secondary)",
          marginBottom: "2rem",
          maxWidth: "600px",
        }}>
          Full-screen view of the decision laboratory. Explore how independent agents analyzed this investment opportunity and where they agreed or diverged.
        </p>

        <DecisionLab data={DECISION_LAB_PREVIEW} analysis={DEMO_ANALYSIS} preview={true} />
      </div>
    </AppLayout>
  );
}
