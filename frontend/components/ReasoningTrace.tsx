export function ReasoningTrace({ steps = [] }: { steps?: string[] }) { return <ol>{steps.map((step) => <li key={step}>{step}</li>)}</ol>; }
