"use client";

import { X } from "lucide-react";
import type { MarketQuote } from "@/types/analysis";

interface WatchlistPanelProps {
  items?: MarketQuote[];
  onRemove?: (instrumentKey: string) => void;
  onSelect?: (instrumentKey: string) => void;
}

export function WatchlistPanel({ items = [], onRemove, onSelect }: WatchlistPanelProps) {
  return (
    <div className="right-panel">
      <div className="panel-header">
        <span>WATCHLIST</span>
      </div>

      <div className="panel-content" style={{ flex: 1, overflow: "auto" }}>
        {items.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {items.map((item) => (
              <button
                key={item.instrument_key}
                onClick={() => onSelect?.(item.instrument_key)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "start",
                  padding: "0.75rem",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  background: "var(--surface-secondary)",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 150ms ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--selected)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface-secondary)")}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "13px" }}>{item.symbol}</div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                    ₹{item.last_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove?.(item.instrument_key);
                  }}
                  className="btn-icon"
                  style={{ width: "24px", height: "24px", padding: 0 }}
                  aria-label="Remove from watchlist"
                >
                  <X size={14} />
                </button>
              </button>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px", padding: "2rem 1rem" }}>
            No watchlist items
          </div>
        )}
      </div>
    </div>
  );
}
