"use client";

interface MarketBarProps {
  indices?: Array<{
    symbol: string;
    value: number;
    change: number;
    changePercent: number;
  }>;
}

export function MarketBar({ indices }: MarketBarProps) {
  const defaultIndices = [
    { symbol: "NIFTY 50", value: 24150, change: 125, changePercent: 0.52 },
    { symbol: "SENSEX", value: 79225, change: 280, changePercent: 0.35 },
    { symbol: "NIFTY BANK", value: 52400, change: 150, changePercent: 0.29 },
  ];

  const displayIndices = indices || defaultIndices;

  return (
    <div className="market-bar">
      {displayIndices.map((index) => (
        <div key={index.symbol} className="market-stat">
          <strong>{index.symbol}</strong>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>
            {index.value.toLocaleString("en-IN")}
          </span>
          <span
            className={`text-${index.changePercent >= 0 ? "positive" : "negative"}`}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {index.changePercent >= 0 ? "+" : ""}
            {index.changePercent.toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
}
