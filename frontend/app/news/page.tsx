"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { Calendar, AlertCircle, Eye } from "lucide-react";

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  source: string;
  timestamp: string;
  symbol?: string;
  sentiment: "positive" | "neutral" | "negative";
  views: number;
}

const DEMO_NEWS: NewsArticle[] = [
  {
    id: "1",
    title: "TCS Q2 Results Beat Expectations",
    summary: "Tata Consultancy Services reported strong revenue growth of 8.3% QoQ, driven by robust demand in cloud and digital services.",
    source: "Financial Express",
    timestamp: "2 hours ago",
    symbol: "TCS",
    sentiment: "positive",
    views: 1243,
  },
  {
    id: "2",
    title: "Reliance Industries Eyes New Energy Ventures",
    summary: "RIL announced plans to invest ₹50,000 crore in green energy and battery manufacturing over the next five years.",
    source: "Business Today",
    timestamp: "4 hours ago",
    symbol: "RELIANCE",
    sentiment: "positive",
    views: 892,
  },
  {
    id: "3",
    title: "INFY Extends Partnership with Major Retailer",
    summary: "Infosys secured a multi-year contract extension with a Fortune 500 retailer for digital transformation services.",
    source: "Economic Times",
    timestamp: "6 hours ago",
    symbol: "INFY",
    sentiment: "positive",
    views: 756,
  },
  {
    id: "4",
    title: "Sector Alert: Tech Sector Faces Headwinds",
    summary: "Analysts warn of potential short-term volatility in IT services as global tech spending slows.",
    source: "Moneycontrol",
    timestamp: "8 hours ago",
    sentiment: "negative",
    views: 654,
  },
  {
    id: "5",
    title: "RBI Holds Rates Steady at 6.5%",
    summary: "Reserve Bank of India kept the policy rate unchanged, citing inflation concerns while monitoring growth.",
    source: "Reuters",
    timestamp: "1 day ago",
    sentiment: "neutral",
    views: 2154,
  },
];

function SentimentBadge({ sentiment }: { sentiment: "positive" | "neutral" | "negative" }) {
  const colors = {
    positive: { bg: "rgba(50, 101, 122, 0.1)", text: "var(--positive)" },
    neutral: { bg: "rgba(93, 101, 112, 0.1)", text: "var(--text-secondary)" },
    negative: { bg: "rgba(182, 75, 75, 0.1)", text: "var(--negative)" },
  };
  const c = colors[sentiment];
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
      {sentiment}
    </span>
  );
}

export default function NewsPage() {
  const [filter, setFilter] = useState<"all" | "positive" | "negative" | "neutral">("all");

  const filteredNews = filter === "all" ? DEMO_NEWS : DEMO_NEWS.filter((n) => n.sentiment === filter);

  return (
    <AppLayout currentPage="news" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Market pulse</p>
            <h1>News & Updates</h1>
          </div>
        </div>

        <p className="demo-notice">Simulated demo news feed — headlines, engagement counts, and sentiment labels are illustrative.</p>

        {/* Filter buttons */}
        <div style={{
          display: "flex",
          gap: "1rem",
          marginBottom: "2rem",
          flexWrap: "wrap",
        }}>
          {(["all", "positive", "negative", "neutral"] as const).map((sentiment) => (
            <button
              key={sentiment}
              onClick={() => setFilter(sentiment)}
              style={{
                padding: "8px 16px",
                borderRadius: "4px",
                border: `2px solid ${filter === sentiment ? "var(--interactive)" : "var(--border)"}`,
                background: filter === sentiment ? "var(--selected)" : "var(--surface-primary)",
                color: filter === sentiment ? "var(--interactive)" : "var(--text-secondary)",
                cursor: "pointer",
                fontWeight: filter === sentiment ? 600 : 500,
                textTransform: "capitalize",
              }}
            >
              {sentiment}
            </button>
          ))}
        </div>

        {/* News list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {filteredNews.map((article) => (
            <article
              key={article.id}
              style={{
                padding: "1.5rem",
                background: "var(--surface-primary)",
                borderRadius: "8px",
                border: `1px solid var(--border)`,
                cursor: "pointer",
                transition: "all 150ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--interactive)";
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.06)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "1rem",
                marginBottom: "1rem",
              }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--text-primary)" }}>
                    {article.title}
                  </h3>
                  <p style={{
                    margin: 0,
                    color: "var(--text-secondary)",
                    fontSize: "14px",
                    lineHeight: 1.5,
                  }}>
                    {article.summary}
                  </p>
                </div>
                <SentimentBadge sentiment={article.sentiment} />
              </div>

              <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "1rem",
                paddingTop: "1rem",
                borderTop: "1px solid var(--border)",
              }}>
                <div style={{ display: "flex", gap: "1rem", fontSize: "13px", color: "var(--text-muted)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Calendar size={14} />
                    {article.timestamp}
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Eye size={14} />
                    {article.views}
                  </span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  {article.symbol && (
                    <span style={{
                      padding: "4px 12px",
                      background: "var(--selected)",
                      borderRadius: "4px",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}>
                      {article.symbol}
                    </span>
                  )}
                  <span style={{
                    padding: "4px 12px",
                    background: "var(--surface-secondary)",
                    borderRadius: "4px",
                    fontSize: "13px",
                    color: "var(--text-secondary)",
                  }}>
                    {article.source}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>

        {filteredNews.length === 0 && (
          <div style={{
            padding: "3rem 2rem",
            textAlign: "center",
            background: "var(--surface-primary)",
            borderRadius: "8px",
          }}>
            <AlertCircle size={32} style={{ margin: "0 auto 1rem", color: "var(--text-muted)" }} />
            <p style={{ color: "var(--text-secondary)" }}>No news articles match this filter.</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
