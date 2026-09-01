"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { DataTable, type Column } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

interface Holding {
  symbol: string;
  shares: number;
  buyPrice: number;
  currentPrice: number;
  weight: number;
}

const DEMO_HOLDINGS: Holding[] = [
  { symbol: "TCS", shares: 100, buyPrice: 3200, currentPrice: 3450, weight: 40 },
  { symbol: "RELIANCE", shares: 50, buyPrice: 2800, currentPrice: 3100, weight: 35 },
  { symbol: "INFY", shares: 80, buyPrice: 2100, currentPrice: 2200, weight: 25 },
];

const COLORS = ["#243B53", "#315F86", "#456C8C", "#5D7A9E"];

export default function PortfolioPage() {
  const [holdings] = useState<Holding[]>(DEMO_HOLDINGS);

  const totalValue = holdings.reduce((sum, h) => sum + h.shares * h.currentPrice, 0);
  const totalCost = holdings.reduce((sum, h) => sum + h.shares * h.buyPrice, 0);
  const unrealizedGain = totalValue - totalCost;
  const unrealizedReturn = ((unrealizedGain / totalCost) * 100).toFixed(2);

  const portfolioData = holdings.map((h) => ({
    name: h.symbol,
    value: (h.weight / 100) * totalValue,
    weight: h.weight,
  }));

  const performanceData = holdings.map((h) => ({
    symbol: h.symbol,
    return: (((h.currentPrice - h.buyPrice) / h.buyPrice) * 100).toFixed(2),
    value: h.currentPrice,
  }));

  const holdingsColumns: Column<Holding>[] = [
    {
      key: "symbol",
      header: "Symbol",
      align: "left",
      render: (value) => <strong>{String(value)}</strong>,
    },
    {
      key: "shares",
      header: "Shares",
      align: "right",
    },
    {
      key: "buyPrice",
      header: "Buy Price",
      align: "right",
      render: (value) => `₹${Number(value).toFixed(2)}`,
    },
    {
      key: "currentPrice",
      header: "Current",
      align: "right",
      render: (value) => `₹${Number(value).toFixed(2)}`,
    },
    {
      key: "weight",
      header: "Allocation",
      align: "right",
      render: (value) => `${value}%`,
    },
  ];

  return (
    <AppLayout currentPage="portfolio" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Investment overview</p>
            <h1>Your Portfolio</h1>
          </div>
        </div>

        <p className="demo-notice">Simulated demo portfolio — prices, allocations, and returns are illustrative and are not live market data.</p>

        {/* Summary metrics */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2rem",
        }}>
          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Total Portfolio Value</label>
              <strong style={{ fontSize: "1.75rem", color: "var(--brand)" }}>
                ₹{(totalValue / 100000).toFixed(2)}L
              </strong>
              <small>Current market value</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Unrealized Gain</label>
              <strong
                style={{
                  fontSize: "1.75rem",
                  color: unrealizedGain >= 0 ? "var(--positive)" : "var(--negative)",
                }}
              >
                ₹{(unrealizedGain / 100000).toFixed(2)}L
              </strong>
              <small>{unrealizedReturn}% return</small>
            </div>
          </div>

          <div className="form-card">
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Holdings</label>
              <strong style={{ fontSize: "1.75rem" }}>{holdings.length}</strong>
              <small>Active positions</small>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="two-column-responsive" style={{
          gap: "2rem",
          marginBottom: "2rem",
        }}>
          <div className="form-card" style={{ display: "flex", flexDirection: "column" }}>
            <p className="eyebrow">Allocation</p>
            <h3>Portfolio Composition</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={portfolioData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name }) => String(name)}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {portfolioData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `₹${(value as number / 100000).toFixed(2)}L`} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="form-card" style={{ display: "flex", flexDirection: "column" }}>
            <p className="eyebrow">Returns</p>
            <h3>Per-Stock Performance</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="symbol" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip
                  formatter={(value) => `${value}%`}
                  contentStyle={{
                    background: "var(--surface-primary)",
                    border: `1px solid var(--border)`,
                  }}
                />
                <Bar dataKey="return" fill="var(--interactive)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Holdings table */}
        <div className="form-card">
          <div className="card-title">
            <h3>Holdings</h3>
            <p>Current positions and allocations</p>
          </div>
          <div style={{ background: "var(--surface-primary)", borderRadius: "8px", overflow: "hidden" }}>
            <DataTable
              columns={holdingsColumns}
              data={holdings}
              keyField="symbol"
              emptyMessage="No holdings"
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
