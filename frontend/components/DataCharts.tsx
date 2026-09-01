"use client";

import { useEffect, useRef } from "react";
import type { Candle } from "@/types/analysis";

function fit(canvas: HTMLCanvasElement) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context?.scale(ratio, ratio);
  return { context, width, height };
}

export function PriceChart({ candles }: { candles: Candle[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || candles.length < 2) return;
    const draw = () => {
      const { context, width, height } = fit(canvas);
      if (!context) return;
      const values = candles.slice(-60).map((item) => item.close);
      const low = Math.min(...values);
      const high = Math.max(...values);
      const span = Math.max(high - low, .01);
      context.clearRect(0, 0, width, height);
      context.strokeStyle = "#d7dcd2";
      context.lineWidth = 1;
      for (let row = 1; row < 4; row += 1) { const y = (height / 4) * row; context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke(); }
      context.strokeStyle = "#1d5b3a";
      context.lineWidth = 2.5;
      context.beginPath();
      values.forEach((value, index) => { const x = (index / (values.length - 1)) * width; const y = height - 14 - ((value - low) / span) * (height - 28); if (index === 0) context.moveTo(x, y); else context.lineTo(x, y); });
      context.stroke();
      context.fillStyle = "#1d5b3a";
      context.font = "600 11px system-ui";
      context.fillText(`₹${high.toFixed(2)}`, 6, 13);
      context.fillText(`₹${low.toFixed(2)}`, 6, height - 4);
    };
    draw(); window.addEventListener("resize", draw); return () => window.removeEventListener("resize", draw);
  }, [candles]);
  return <canvas className="price-chart-canvas" ref={ref} aria-label="Actual closing-price history for the selected instrument"/>;
}

export function AllocationPie({ items }: { items: { symbol: string; weight: number }[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const { context, width, height } = fit(canvas);
      if (!context) return;
      context.clearRect(0, 0, width, height);
      const total = items.reduce((sum, item) => sum + Math.max(item.weight, 0), 0);
      const radius = Math.min(width, height) * .34;
      const centerX = width / 2, centerY = height / 2;
      const colors = ["#1d5b3a", "#dff46a", "#315f85", "#a95b22", "#6d746b"];
      if (!total) { context.strokeStyle = "#c9cec4"; context.lineWidth = 18; context.beginPath(); context.arc(centerX, centerY, radius, 0, Math.PI * 2); context.stroke(); return; }
      let start = -Math.PI / 2;
      items.forEach((item, index) => { const angle = (Math.max(item.weight, 0) / total) * Math.PI * 2; context.fillStyle = colors[index % colors.length]; context.beginPath(); context.moveTo(centerX, centerY); context.arc(centerX, centerY, radius, start, start + angle); context.closePath(); context.fill(); start += angle; });
      context.fillStyle = "#151914"; context.beginPath(); context.arc(centerX, centerY, radius * .52, 0, Math.PI * 2); context.fill();
      context.fillStyle = "#f5f5ef"; context.textAlign = "center"; context.font = "700 16px system-ui"; context.fillText(`${total.toFixed(0)}%`, centerX, centerY + 5);
    };
    draw(); window.addEventListener("resize", draw); return () => window.removeEventListener("resize", draw);
  }, [items]);
  return <canvas className="allocation-pie-canvas" ref={ref} aria-label="Portfolio allocation pie chart"/>;
}
