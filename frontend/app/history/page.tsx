"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { DataTable, type Column, Tabs, type Tab } from "@/components/ui";

interface AnalysisRow {
  id: string;
  symbol: string;
  date: string;
  classification: string;
  confidence: number;
  riskProfile: string;
  completeness: number;
}

interface DecisionRow {
  id: string;
  action: string;
  ticker: string;
  signal: string;
  confidence: number;
  date: string;
}

const DEMO_ANALYSES: AnalysisRow[] = [
  {
    id: "1",
    symbol: "RELIANCE",
    date: "Sep 1, 2026",
    classification: "BUY",
    confidence: 87,
    riskProfile: "Moderate",
    completeness: 98,
  },
  {
    id: "2",
    symbol: "TCS",
    date: "Aug 31, 2026",
    classification: "HOLD",
    confidence: 72,
    riskProfile: "Conservative",
    completeness: 95,
  },
  {
    id: "3",
    symbol: "INFY",
    date: "Aug 30, 2026",
    classification: "BUY",
    confidence: 81,
    riskProfile: "Aggressive",
    completeness: 100,
  },
];

const DEMO_DECISIONS: DecisionRow[] = [
  {
    id: "1",
    action: "BUY",
    ticker: "RELIANCE",
    signal: "BUY",
    confidence: 87,
    date: "Sep 1, 2026",
  },
  {
    id: "2",
    action: "WATCH",
    ticker: "TCS",
    signal: "HOLD",
    confidence: 72,
    date: "Aug 31, 2026",
  },
  {
    id: "3",
    action: "BUY",
    ticker: "INFY",
    signal: "BUY",
    confidence: 81,
    date: "Aug 30, 2026",
  },
];

function ClassificationBadge({ classification }: { classification: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    BUY: { bg: "rgba(50, 101, 122, 0.1)", text: "var(--positive)" },
    SELL: { bg: "rgba(182, 75, 75, 0.1)", text: "var(--negative)" },
    HOLD: { bg: "rgba(166, 107, 36, 0.1)", text: "var(--warning)" },
    WATCH: { bg: "rgba(69, 108, 140, 0.1)", text: "var(--info)" },
  };
  const c = colors[classification] || colors.HOLD;
  return (
    <span style={{
      display: "inline-block",
      padding: "4px 12px",
      borderRadius: "4px",
      background: c.bg,
      color: c.text,
      fontSize: "13px",
      fontWeight: 600,
    }}>
      {classification}
    </span>
  );
}

export default function HistoryPage() {
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisRow | null>(null);

  const analysisColumns: Column<AnalysisRow>[] = [
    {
      key: "symbol",
      header: "Symbol",
      align: "left",
      render: (value) => <strong>{String(value)}</strong>,
    },
    {
      key: "classification",
      header: "Signal",
      align: "center",
      render: (value) => <ClassificationBadge classification={value as string} />,
    },
    {
      key: "confidence",
      header: "Confidence",
      align: "right",
      render: (value) => `${value}%`,
    },
    {
      key: "riskProfile",
      header: "Risk Profile",
      align: "left",
    },
    {
      key: "completeness",
      header: "Completeness",
      align: "right",
      render: (value) => `${value}%`,
    },
    {
      key: "date",
      header: "Date",
      align: "right",
    },
  ];

  const decisionColumns: Column<DecisionRow>[] = [
    {
      key: "ticker",
      header: "Ticker",
      align: "left",
      render: (value) => <strong>{String(value)}</strong>,
    },
    {
      key: "action",
      header: "Action",
      align: "center",
      render: (value) => <ClassificationBadge classification={value as string} />,
    },
    {
      key: "signal",
      header: "Market Signal",
      align: "center",
      render: (value) => <ClassificationBadge classification={value as string} />,
    },
    {
      key: "confidence",
      header: "Confidence",
      align: "right",
      render: (value) => `${value}%`,
    },
    {
      key: "date",
      header: "Date",
      align: "right",
    },
  ];

  const tabs: Tab[] = [
    {
      id: "analyses",
      label: "Analyses",
      content: (
        <div style={{ background: "var(--surface-primary)", borderRadius: "8px", overflow: "hidden" }}>
          <DataTable
            columns={analysisColumns}
            data={DEMO_ANALYSES}
            keyField="id"
            onRowClick={setSelectedAnalysis}
            emptyMessage="No analyses yet"
          />
        </div>
      ),
    },
    {
      id: "decisions",
      label: "Decisions",
      content: (
        <div style={{ background: "var(--surface-primary)", borderRadius: "8px", overflow: "hidden" }}>
          <DataTable
            columns={decisionColumns}
            data={DEMO_DECISIONS}
            keyField="id"
            emptyMessage="No decisions yet"
          />
        </div>
      ),
    },
  ];

  return (
    <AppLayout currentPage="history" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Research archive</p>
            <h1>Analysis History</h1>
          </div>
        </div>

        <p className="demo-notice">Simulated demo history — these analyses and decisions are examples, not records loaded from your account.</p>

        {/* Summary stats */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2rem",
        }}>
          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Total Analyses</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--brand)" }}>
                {DEMO_ANALYSES.length}
              </strong>
              <small>Completed reports</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Avg. Confidence</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--positive)" }}>
                {(DEMO_ANALYSES.reduce((sum, a) => sum + a.confidence, 0) / DEMO_ANALYSES.length).toFixed(0)}%
              </strong>
              <small>Average signal strength</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Total Decisions</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--interactive)" }}>
                {DEMO_DECISIONS.length}
              </strong>
              <small>Recorded actions</small>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="form-card">
          <Tabs tabs={tabs} defaultTab="analyses" />
        </div>

        {/* Selected analysis detail */}
        {selectedAnalysis && (
          <div className="form-card" style={{ marginTop: "2rem" }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}>
              <h3>{selectedAnalysis.symbol} Analysis</h3>
              <button
                onClick={() => setSelectedAnalysis(null)}
                style={{
                  padding: "4px 12px",
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                }}
              >
                Close
              </button>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: "1rem",
            }}>
              <div>
                <small style={{ color: "var(--text-muted)" }}>Classification</small>
                <p style={{ fontSize: "14px", fontWeight: 600, margin: "0.25rem 0 0 0" }}>
                  <ClassificationBadge classification={selectedAnalysis.classification} />
                </p>
              </div>
              <div>
                <small style={{ color: "var(--text-muted)" }}>Confidence</small>
                <p style={{ fontSize: "14px", fontWeight: 600, margin: "0.25rem 0 0 0" }}>
                  {selectedAnalysis.confidence}%
                </p>
              </div>
              <div>
                <small style={{ color: "var(--text-muted)" }}>Risk Profile</small>
                <p style={{ fontSize: "14px", fontWeight: 600, margin: "0.25rem 0 0 0" }}>
                  {selectedAnalysis.riskProfile}
                </p>
              </div>
              <div>
                <small style={{ color: "var(--text-muted)" }}>Date</small>
                <p style={{ fontSize: "14px", fontWeight: 600, margin: "0.25rem 0 0 0" }}>
                  {selectedAnalysis.date}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
