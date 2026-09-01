import type { Source } from "@/types/analysis";
export function SourcesPanel({ sources = [] }: { sources?: Source[] }) { return <ul>{sources.map((source) => <li key={`${source.document}-${source.chunk_id}`}>{source.title}</li>)}</ul>; }
