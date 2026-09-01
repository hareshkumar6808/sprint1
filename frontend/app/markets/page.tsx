"use client";

import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout";
import { DataTable, type Column } from "@/components/ui";
import type { Instrument } from "@/types/analysis";
import { getQuotes, searchInstruments } from "@/lib/api";
import { Search } from "lucide-react";

interface MarketRow extends Instrument {
  lastPrice?: number;
  change?: number;
  changePercent?: number;
  volume?: number;
  volumeRatio?: number;
}

export default function MarketsPage() {
  const [instruments, setInstruments] = useState<MarketRow[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setInstruments([]);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const results = await searchInstruments(searchQuery, controller.signal);
        const quotes = results.length ? await getQuotes(results.map((item) => item.instrument_key), controller.signal) : [];
        const byKey = Object.fromEntries(quotes.map((item) => [item.instrument_key, item]));
        setInstruments(results.map((item) => ({ ...item, lastPrice: byKey[item.instrument_key]?.last_price ?? undefined, change: byKey[item.instrument_key]?.absolute_change ?? undefined, changePercent: byKey[item.instrument_key]?.percentage_change ?? undefined, volume: byKey[item.instrument_key]?.volume ?? undefined })));
      } catch {
        setInstruments([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [searchQuery]);

  const columns: Column<MarketRow>[] = [
    {
      key: "symbol",
      header: "Symbol",
      align: "left",
      render: (value) => <strong>{String(value)}</strong>,
    },
    {
      key: "name",
      header: "Company",
      align: "left",
    },
    {
      key: "exchange",
      header: "Exchange",
      align: "center",
    },
    {
      key: "lastPrice",
      header: "Price",
      align: "right",
      render: (value) => typeof value === "number" ? `₹${value.toFixed(2)}` : "—",
    },
    {
      key: "changePercent",
      header: "Change %",
      align: "right",
      render: (value) => {
        if (typeof value !== "number") return "—";
        const color = value >= 0 ? "var(--positive)" : "var(--negative)";
        return <span style={{ color }}>{value >= 0 ? "+" : ""}{value.toFixed(2)}%</span>;
      },
    },
    {
      key: "volumeRatio",
      header: "Volume Ratio",
      align: "right",
      render: (value) => typeof value === "number" ? `${value.toFixed(2)}×` : "—",
    },
  ];

  return (
    <AppLayout currentPage="markets" onNavigate={() => {}} onSearch={() => {}}>
      <div style={{ padding: "2rem", background: "var(--bg)" }}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Market intelligence</p>
            <h1>Instrument Discovery</h1>
          </div>
        </div>

        <div className="form-card" style={{ marginBottom: "2rem" }}>
          <div className="field">
            <label htmlFor="market-search">Search NSE/BSE</label>
            <div style={{ position: "relative" }}>
              <Search
                size={18}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "12px",
                  color: "var(--text-secondary)",
                }}
              />
              <input
                id="market-search"
                type="text"
                placeholder="Search by symbol or company name"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoComplete="off"
                style={{ paddingLeft: "40px" }}
              />
            </div>
            <small>
              {searching && "Searching catalogue…"}
              {!searching && searchQuery.length >= 2 && instruments.length === 0 && "No instruments found."}
              {!searching && searchQuery.length >= 2 && instruments.length > 0 && `Found ${instruments.length} instrument${instruments.length !== 1 ? "s" : ""}.`}
            </small>
          </div>
        </div>

        {instruments.length > 0 && (
          <div style={{ background: "var(--surface-primary)", borderRadius: "8px", overflow: "hidden" }}>
            <DataTable
              columns={columns}
              data={instruments}
              keyField="instrument_key"
              emptyMessage="No instruments available"
            />
          </div>
        )}

        {instruments.length === 0 && searchQuery.length === 0 && (
          <div style={{
            background: "var(--surface-primary)",
            padding: "3rem 2rem",
            borderRadius: "8px",
            textAlign: "center",
          }}>
            <p style={{ color: "var(--text-secondary)" }}>
              Search for a stock or company to explore market data.
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
