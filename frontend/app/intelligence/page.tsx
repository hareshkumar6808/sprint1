"use client";

import { AppLayout } from "@/components/layout";
import { DataTable, type Column } from "@/components/ui";
import { Zap } from "lucide-react";

interface AgentReport {
  id: string;
  agent: string;
  specialization: string;
  status: "ready" | "running" | "completed";
  lastRun: string;
  accuracy: number;
  latency: number;
}

const DEMO_AGENTS: AgentReport[] = [
  {
    id: "1",
    agent: "Technical Analyst",
    specialization: "Price patterns, momentum, resistance/support levels",
    status: "ready",
    lastRun: "2 hours ago",
    accuracy: 87,
    latency: 145,
  },
  {
    id: "2",
    agent: "Sentiment Analyst",
    specialization: "News sentiment, social signals, market narrative",
    status: "ready",
    lastRun: "1 hour ago",
    accuracy: 74,
    latency: 210,
  },
  {
    id: "3",
    agent: "Fundamental Analyst",
    specialization: "Financial statements, valuation metrics, earnings quality",
    status: "ready",
    lastRun: "3 hours ago",
    accuracy: 92,
    latency: 320,
  },
  {
    id: "4",
    agent: "Risk Analyst",
    specialization: "Volatility, drawdown, portfolio concentration risks",
    status: "ready",
    lastRun: "30 minutes ago",
    accuracy: 89,
    latency: 156,
  },
];

function StatusBadge({ status }: { status: "ready" | "running" | "completed" }) {
  const colors = {
    ready: { bg: "rgba(50, 101, 122, 0.1)", text: "var(--positive)" },
    running: { bg: "rgba(166, 107, 36, 0.1)", text: "var(--warning)" },
    completed: { bg: "rgba(36, 59, 83, 0.1)", text: "var(--brand)" },
  };
  const c = colors[status];
  return (
    <span style={{
      display: "inline-block",
      padding: "4px 12px",
      borderRadius: "4px",
      background: c.bg,
      color: c.text,
      fontSize: "13px",
      fontWeight: 600,
      textTransform: "capitalize",
    }}>
      {status === "running" && <span style={{ display: "inline-block", animation: "spin 1s linear infinite", marginRight: "4px" }}>◌</span>}
      {status}
    </span>
  );
}

export default function IntelligencePage() {
  const columns: Column<AgentReport>[] = [
    {
      key: "agent",
      header: "Agent",
      align: "left",
      render: (value) => <strong>{String(value)}</strong>,
    },
    {
      key: "specialization",
      header: "Specialization",
      align: "left",
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      render: (value) => <StatusBadge status={value as "ready" | "running" | "completed"} />,
    },
    {
      key: "accuracy",
      header: "Accuracy",
      align: "right",
      render: (value) => `${value}%`,
    },
    {
      key: "latency",
      header: "Latency",
      align: "right",
      render: (value) => `${value}ms`,
    },
    {
      key: "lastRun",
      header: "Last Run",
      align: "right",
    },
  ];

  return (
    <AppLayout currentPage="intelligence" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Research engine</p>
            <h1>Intelligence Network</h1>
          </div>
        </div>

        <p className="demo-notice">Simulated demo metrics — agent status, accuracy, and latency values are illustrative.</p>

        {/* System overview */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2rem",
        }}>
          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Active Agents</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--brand)" }}>
                {DEMO_AGENTS.length}
              </strong>
              <small>All systems operational</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Avg. Accuracy</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--positive)" }}>
                {(DEMO_AGENTS.reduce((sum, a) => sum + a.accuracy, 0) / DEMO_AGENTS.length).toFixed(0)}%
              </strong>
              <small>Historical performance</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Avg. Latency</label>
              <strong style={{ fontSize: "1.75rem" }}>
                {(DEMO_AGENTS.reduce((sum, a) => sum + a.latency, 0) / DEMO_AGENTS.length).toFixed(0)}ms
              </strong>
              <small>Analysis response time</small>
            </div>
          </div>
        </div>

        {/* Agents table */}
        <div className="form-card">
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1rem",
          }}>
            <Zap size={18} style={{ color: "var(--brand)" }} />
            <h3>Specialist Agents</h3>
          </div>
          <div style={{ background: "var(--surface-primary)", borderRadius: "8px", overflow: "hidden" }}>
            <DataTable
              columns={columns}
              data={DEMO_AGENTS}
              keyField="id"
              emptyMessage="No agents available"
            />
          </div>
        </div>

        {/* How it works section */}
        <div className="form-card" style={{ marginTop: "2rem" }}>
          <h3>How It Works</h3>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "1.5rem",
            marginTop: "1rem",
          }}>
            <div>
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                Independent Analysis
              </p>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                Each agent analyzes independently without knowledge of other agents&apos; conclusions.
              </p>
            </div>
            <div>
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                Conflict Detection
              </p>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                Disagreements are flagged automatically for deeper investigation.
              </p>
            </div>
            <div>
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                Personalized&nbsp;Synthesis
              </p>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                Results are adjusted for your risk profile and investment horizon.
              </p>
            </div>
            <div>
              <p style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                Full Traceability
              </p>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                All evidence, sources, and reasoning steps are preserved and auditable.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
