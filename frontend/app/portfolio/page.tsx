"use client";

import { useEffect, useMemo, useState } from "react";
import { AppLayout } from "@/components/layout";
import { DataTable, type Column } from "@/components/ui";
import { PriceChart } from "@/components/DataCharts";
import { getCandles, getQuotes } from "@/lib/api";
import type { Candle, MarketQuote } from "@/types/analysis";
import { Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

interface Holding {
  instrumentKey: string;
  symbol: string;
  shares: number;
  buyPrice: number;
  currentPrice: number;
  weight: number;
}

const DEMO_HOLDINGS: Holding[] = [
  { instrumentKey: "NSE_EQ|INE467B01029", symbol: "TCS", shares: 100, buyPrice: 3200, currentPrice: 3450, weight: 40 },
  { instrumentKey: "NSE_EQ|INE002A01018", symbol: "RELIANCE", shares: 50, buyPrice: 2800, currentPrice: 3100, weight: 35 },
  { instrumentKey: "NSE_EQ|INE009A01021", symbol: "INFY", shares: 80, buyPrice: 2100, currentPrice: 2200, weight: 25 },
];

const COLORS = ["#243B53", "#315F86", "#456C8C", "#5D7A9E"];

export default function PortfolioPage() {
  const [quotes, setQuotes] = useState<Record<string, MarketQuote>>({});
  const [candles, setCandles] = useState<Record<string, Candle[]>>({});
  useEffect(() => { const controller = new AbortController(); const keys = DEMO_HOLDINGS.map((item) => item.instrumentKey); void getQuotes(keys, controller.signal).then((items) => setQuotes(Object.fromEntries(items.map((item) => [item.instrument_key, item])))).catch(() => setQuotes({})); void Promise.all(DEMO_HOLDINGS.map(async (item) => [item.symbol, await getCandles(item.instrumentKey, controller.signal)] as const)).then((items) => setCandles(Object.fromEntries(items))).catch(() => setCandles({})); return () => controller.abort(); }, []);
  const holdings = useMemo(() => DEMO_HOLDINGS.map((item) => ({ ...item, currentPrice: quotes[item.instrumentKey]?.last_price ?? item.currentPrice })), [quotes]);

  const totalValue = holdings.reduce((sum, h) => sum + h.shares * h.currentPrice, 0);
  const totalCost = holdings.reduce((sum, h) => sum + h.shares * h.buyPrice, 0);
  const unrealizedGain = totalValue - totalCost;
  const unrealizedReturn = ((unrealizedGain / totalCost) * 100).toFixed(2);

  const portfolioData = holdings.map((h) => ({
    name: h.symbol,
    value: (h.weight / 100) * totalValue,
    weight: h.weight,
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

        <p className="demo-notice">Demo share counts and buy prices are illustrative. Current prices and 90-day lines come from Yahoo Finance and may be delayed or cached.</p>

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
            <p className="eyebrow">90-day market history</p>
            <h3>RELIANCE closing price</h3>
            {candles.RELIANCE?.length > 1 ? <PriceChart candles={candles.RELIANCE}/> : <p className="text-muted">Loading market history…</p>}
          </div>
        </div>

        <div className="two-column-responsive" style={{ gap: "2rem", marginBottom: "2rem" }}>
          <div className="form-card"><p className="eyebrow">90-day market history</p><h3>TCS closing price</h3>{candles.TCS?.length > 1 ? <PriceChart candles={candles.TCS}/> : <p className="text-muted">Loading market history…</p>}</div>
          <div className="form-card"><p className="eyebrow">90-day market history</p><h3>INFY closing price</h3>{candles.INFY?.length > 1 ? <PriceChart candles={candles.INFY}/> : <p className="text-muted">Loading market history…</p>}</div>
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
