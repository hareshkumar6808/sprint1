import { getHealth } from "@/lib/api";
export default async function Home() {
  const health = await getHealth();
  return <main className="shell"><section className="panel"><div className="eyebrow">Local-first research system</div><h1>FinSync<br/>Intelligence</h1><p>The project foundation is ready. Simulated market fixtures, shared agent contracts, profiles, and health checks are connected for the next hackathon phase.</p><div className="status"><span className={`dot ${health.ok ? "ok" : ""}`}/><span>Backend {health.ok ? `healthy · v${health.version}` : "offline — start the API locally"}</span></div><p><small>Educational research intelligence only. Not financial advice or a guaranteed outcome.</small></p></section></main>;
}
