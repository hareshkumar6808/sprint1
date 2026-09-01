export function WarningBanner({ warnings = [] }: { warnings?: string[] }) { return warnings.length ? <aside role="alert">{warnings.join(" · ")}</aside> : null; }
