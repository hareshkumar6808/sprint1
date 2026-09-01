import type { AgentOutput } from "@/types/analysis";
export function AgentCard({ output }: { output?: AgentOutput }) { return <article>{output?.summary ?? "Agent awaiting analysis"}</article>; }
