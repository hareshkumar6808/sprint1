import type { Synthesis } from "@/types/analysis";
export function SynthesisCard({ synthesis }: { synthesis?: Synthesis }) { return <article>{synthesis?.summary ?? "Synthesis awaiting evidence"}</article>; }
