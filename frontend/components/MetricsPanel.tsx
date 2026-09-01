import type { Metrics } from "@/types/analysis";
export function MetricsPanel({ metrics }: { metrics?: Metrics }) { return <section aria-label="Analysis metrics">{metrics ? `${metrics.agents_completed}/${metrics.agents_expected} agents completed` : "No metrics yet"}</section>; }
