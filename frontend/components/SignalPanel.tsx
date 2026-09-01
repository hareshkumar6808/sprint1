import type { Classification } from "@/types/analysis";
export function SignalPanel({ signal }: { signal?: Classification }) { return <section aria-label="Market signal">{signal ?? "insufficient_data"}</section>; }
