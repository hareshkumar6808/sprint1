"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getHealth, listStocks, loadAnalysisHistory, runAnalysis, saveProfile as persistProfile } from "@/lib/api";
import type { AgentOutput, AnalysisResponse, Classification, MarketSnapshot, ProfileInput, RiskProfile, Source } from "@/types/analysis";

const SYMBOLS = ["RELIANCE", "TCS", "INFY"];
const USER_ID = "demo-user";
const STAGES = ["Loading market data", "Retrieving filing evidence", "Running specialist agents", "Synthesizing personalized guidance"];
const AGENT_META = {
  technical: ["Technical Agent", "Momentum, volume & market risk", "↗"],
  sentiment: ["Sentiment Agent", "Local news evidence", "◉"],
  fundamental: ["Fundamental / RAG Agent", "Retrieved filing evidence", "⌘"],
  behavioral: ["Behavioral Agent", "Personal risk suitability", "◇"],
} as const;
type EditableHolding = { symbol: string; weight: string };

const formatMoney = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
const formatDate = (value: string) => new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const titleCase = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const tone = (value: Classification | string) => ["bullish", "positive", "strong", "suitable", "completed"].includes(value) ? "positive" : ["bearish", "negative", "weak", "unsuitable", "failed"].includes(value) ? "negative" : ["degraded", "unavailable", "insufficient_data"].includes(value) ? "warning" : "neutral";
const numericDraft = (value: string) => /^\d+$/.test(value) ? String(Number(value)) : value;
const normalizedNumber = (value: string) => value.trim() !== "" && Number.isFinite(Number(value)) ? String(Number(value)) : value;

function Tag({ value }: { value: Classification | string }) { return <span className={`tag ${tone(value)}`}><span aria-hidden="true">{tone(value) === "positive" ? "▲" : tone(value) === "negative" ? "▼" : tone(value) === "warning" ? "!" : "◆"}</span>{titleCase(value)}</span>; }
function ListBlock({ title, items, empty = "None reported" }: { title: string; items: string[]; empty?: string }) { return <div className="list-block"><h4>{title}</h4>{items.length ? <ul>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p className="empty-copy">{empty}</p>}</div>; }

function AgentCard({ output }: { output: AgentOutput }) {
  const [name, role, icon] = AGENT_META[output.agent];
  return <article className={`agent-card state-${output.status}`}>
    <div className="agent-head"><span className="agent-icon" aria-hidden="true">{icon}</span><div><p>{name}</p><small>{role}</small></div><Tag value={output.status}/></div>
    <div className="agent-classification"><Tag value={output.classification}/><span>{output.confidence}% confidence</span></div>
    <div className="confidence-track" aria-label={`${output.confidence}% confidence`}><span style={{ width: `${output.confidence}%` }}/></div>
    <p className="agent-summary">{output.summary}</p>
    <details><summary>Inspect evidence, risks & sources <span>+</span></summary><div className="agent-detail"><ListBlock title="Evidence" items={output.evidence}/><ListBlock title="Risks" items={output.risks}/>{output.sources.length > 0 && <div className="list-block"><h4>Sources</h4><ul>{output.sources.map((source) => <li key={`${source.document}-${source.chunk_id}`}>{source.title}<small>{source.document}{source.chunk_id ? ` · ${source.chunk_id}` : ""}</small></li>)}</ul></div>}<ListBlock title="Warnings" items={output.warnings}/></div></details>
    <footer><span>Latency</span><strong>{output.latency_ms.toFixed(2)} ms</strong></footer>
  </article>;
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</article>; }

function SourceItem({ source, agents }: { source: Source; agents: AgentOutput[] }) {
  const associated = agents.filter((agent) => agent.sources.some((item) => item.document === source.document && item.chunk_id === source.chunk_id)).map((agent) => AGENT_META[agent.agent][0]);
  return <li className="source-item"><div><span className="source-symbol">§</span><div><strong>{source.title}</strong><p>{source.document}</p></div></div><dl><div><dt>Date</dt><dd>{source.date}</dd></div>{source.chunk_id && <div><dt>Chunk</dt><dd>{source.chunk_id}</dd></div>}<div><dt>Used by</dt><dd>{associated.join(", ") || "Synthesis"}</dd></div></dl><span className="sim-label">Simulated source</span></li>;
}

export function Dashboard() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [version, setVersion] = useState("");
  const [stocks, setStocks] = useState<MarketSnapshot[]>([]);
  const [history, setHistory] = useState<AnalysisResponse[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("TCS");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [risk, setRisk] = useState<RiskProfile>("conservative");
  const [horizon, setHorizon] = useState("8");
  const [maxVolatility, setMaxVolatility] = useState("15");
  const [holdings, setHoldings] = useState<EditableHolding[]>([{ symbol: "TCS", weight: "70" }, { symbol: "RELIANCE", weight: "30" }]);
  const [watchlist, setWatchlist] = useState<string[]>(["TCS"]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [retryAction, setRetryAction] = useState<"save" | "analyze">("analyze");

  const allocation = holdings.reduce((sum, holding) => sum + (Number.isFinite(Number(holding.weight)) ? Number(holding.weight) : 0), 0);
  const horizonNumber = Number(horizon);
  const volatilityNumber = Number(maxVolatility);
  const profilePayload = useMemo<ProfileInput>(() => ({ user_id: USER_ID, risk_profile: risk, investment_horizon_years: horizonNumber, maximum_volatility: volatilityNumber, portfolio: holdings.map((holding) => ({ symbol: holding.symbol, weight: Number(holding.weight) })), watchlist, interaction_history: [{ action: "viewed", symbol: selectedSymbol }] }), [risk, horizonNumber, volatilityNumber, holdings, watchlist, selectedSymbol]);
  const validation = horizon.trim() === "" ? "Investment horizon is required." : !Number.isFinite(horizonNumber) || !Number.isInteger(horizonNumber) || horizonNumber < 1 || horizonNumber > 50 ? "Investment horizon must be a whole number from 1 to 50 years." : maxVolatility.trim() === "" ? "Maximum volatility is required." : !Number.isFinite(volatilityNumber) || volatilityNumber < 0 || volatilityNumber > 100 ? "Maximum volatility must be a number from 0% to 100%." : holdings.some((holding) => holding.weight.trim() === "" || !Number.isFinite(Number(holding.weight)) || Number(holding.weight) < 0 || Number(holding.weight) > 100) ? "Each portfolio weight must be a number from 0% to 100%." : Math.abs(allocation - 100) > 0.001 ? `Portfolio allocation must total 100%. Current total: ${allocation.toFixed(2).replace(/\.00$/, "")}%.` : "";

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const results = await Promise.allSettled([getHealth(signal), listStocks(signal), loadAnalysisHistory(USER_ID, signal)]);
    if (results[0].status === "fulfilled") { setConnected(true); setVersion(results[0].value.version); } else setConnected(false);
    if (results[1].status === "fulfilled") setStocks(results[1].value);
    if (results[2].status === "fulfilled") setHistory(results[2].value);
  }, []);

  useEffect(() => { const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort(); }, [refresh]);
  useEffect(() => { if (!loading) return; const timer = window.setInterval(() => setStage((current) => Math.min(current + 1, STAGES.length - 1)), 850); return () => window.clearInterval(timer); }, [loading]);

  async function handleSave(showSuccess = true) {
    if (validation) { setRetryAction(showSuccess ? "save" : "analyze"); setMessage({ kind: "error", text: validation }); return false; }
    setSaving(true); setMessage(null);
    try { await persistProfile(profilePayload); setConnected(true); if (showSuccess) setMessage({ kind: "success", text: "Profile and portfolio saved for demo-user." }); return true; }
    catch (error) { setRetryAction(showSuccess ? "save" : "analyze"); setConnected(false); setMessage({ kind: "error", text: error instanceof Error ? error.message : "Unable to save the profile." }); return false; }
    finally { setSaving(false); }
  }

  async function handleAnalyze() {
    if (loading) return;
    const saved = await handleSave(false); if (!saved) return;
    setLoading(true); setStage(0); setMessage(null);
    try { const result = await runAnalysis(USER_ID, selectedSymbol); setAnalysis(result); setConnected(true); setMessage({ kind: "success", text: `${selectedSymbol} analysis completed with ${result.metrics.agents_completed} of ${result.metrics.agents_expected} agents.` }); const updated = await loadAnalysisHistory(USER_ID); setHistory(updated); window.setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }), 50); }
    catch (error) { setRetryAction("analyze"); setConnected(false); setMessage({ kind: "error", text: error instanceof Error ? error.message : "Analysis failed. Please retry." }); }
    finally { setLoading(false); }
  }

  function updateHolding(index: number, field: "symbol" | "weight", value: string) { setHoldings((current) => current.map((holding, itemIndex) => itemIndex === index ? { ...holding, [field]: field === "weight" ? numericDraft(value) : value } : holding)); }
  function normalizeHolding(index: number) { setHoldings((current) => current.map((holding, itemIndex) => itemIndex === index ? { ...holding, weight: normalizedNumber(holding.weight) } : holding)); }
  function addHolding() { const symbol = SYMBOLS.find((item) => !holdings.some((holding) => holding.symbol === item)); if (symbol) setHoldings((current) => [...current, { symbol, weight: "0" }]); }
  function reopen(item: AnalysisResponse) { setAnalysis(item); setSelectedSymbol(item.symbol); document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }); }

  const snapshot = analysis?.market_snapshot;
  const technical = analysis?.agents.find((agent) => agent.agent === "technical");
  const sentiment = analysis?.agents.find((agent) => agent.agent === "sentiment");
  const volumeRatio = snapshot ? snapshot.current_volume / snapshot.average_volume : 0;
  const movingAveragePosition = snapshot ? (snapshot.current_price / snapshot.twenty_day_moving_average - 1) * 100 : 0;
  const dailyReturn = snapshot ? (snapshot.current_price / snapshot.previous_close - 1) * 100 : 0;

  return <main className="app-shell" id="top">
    <header className="topbar"><a className="brand" href="#top"><span className="brand-mark">F</span><span><strong>FinSync</strong><small>Intelligence</small></span></a><div className="header-copy"><span>Multi-Agent Market Research</span><small>Evidence before conclusions</small></div><div className="header-badges"><span className="badge simulated">◆ Simulated data</span><button className={`badge connection ${connected === true ? "online" : connected === false ? "offline" : "checking"}`} onClick={() => void refresh()}><span aria-hidden="true">●</span>{connected === true ? `API connected ${version ? `· v${version}` : ""}` : connected === false ? "Backend unavailable" : "Checking API"}</button></div></header>
    <div className="disclaimer-strip"><span>i</span><p><strong>Educational research intelligence.</strong> Simulated local evidence only—not financial advice, guaranteed outcomes, or direct trading instructions.</p></div>

    <section className="command-grid">
      <aside className="profile-column">
        <div className="section-heading"><div><p className="eyebrow">Research context</p><h2>Profile & portfolio</h2></div><span className="user-chip">demo-user</span></div>
        <div className="form-card"><div className="field"><label htmlFor="risk">Risk profile</label><select id="risk" value={risk} onChange={(event) => setRisk(event.target.value as RiskProfile)}><option value="conservative">Conservative</option><option value="moderate">Balanced</option><option value="aggressive">Aggressive</option></select><small>Changes suitability and personalized guidance.</small></div><div className="two-fields"><div className="field"><label htmlFor="horizon">Horizon <span>years</span></label><input id="horizon" type="text" inputMode="numeric" value={horizon} aria-invalid={Boolean(validation && /horizon/i.test(validation))} onChange={(event) => setHorizon(numericDraft(event.target.value))} onBlur={() => setHorizon(normalizedNumber(horizon))}/></div><div className="field"><label htmlFor="volatility">Max volatility <span>%</span></label><input id="volatility" type="text" inputMode="decimal" value={maxVolatility} aria-invalid={Boolean(validation && /volatility/i.test(validation))} onChange={(event) => setMaxVolatility(numericDraft(event.target.value))} onBlur={() => setMaxVolatility(normalizedNumber(maxVolatility))}/></div></div></div>
        <div className="form-card portfolio-card"><div className="card-title"><div><h3>Holdings</h3><p>Used to evaluate concentration.</p></div><strong className={Math.abs(allocation - 100) <= 0.001 ? "valid" : "invalid"}>{allocation.toFixed(2).replace(/\.00$/, "")}% allocated</strong></div>{holdings.map((holding, index) => <div className="holding-row" key={`${holding.symbol}-${index}`}><select aria-label={`Holding ${index + 1} symbol`} value={holding.symbol} onChange={(event) => updateHolding(index, "symbol", event.target.value)}>{SYMBOLS.map((symbol) => <option key={symbol}>{symbol}</option>)}</select><label><input aria-label={`${holding.symbol} allocation`} type="text" inputMode="decimal" value={holding.weight} onChange={(event) => updateHolding(index, "weight", event.target.value)} onBlur={() => normalizeHolding(index)}/><span>%</span></label><button className="icon-button" type="button" aria-label={`Remove ${holding.symbol}`} onClick={() => setHoldings((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></div>)}<button className="text-button" type="button" onClick={addHolding} disabled={holdings.length === SYMBOLS.length}>＋ Add holding</button>{validation && <p className="validation-text" role="alert">{validation}</p>}<div className="watchlist"><h4>Watchlist</h4><div>{SYMBOLS.map((symbol) => <label key={symbol}><input type="checkbox" checked={watchlist.includes(symbol)} onChange={() => setWatchlist((current) => current.includes(symbol) ? current.filter((item) => item !== symbol) : [...current, symbol])}/><span>{symbol}</span></label>)}</div></div><button className="secondary-button" onClick={() => void handleSave()} disabled={saving}>{saving ? "Saving profile…" : "Save profile & portfolio"}</button></div>
      </aside>

      <section className="research-column">
        <div className="hero-copy"><p className="eyebrow">Research command center</p><h1>Independent agents.<br/><em>One supported view.</em></h1><p>Inspect market behavior, synthetic news, retrieved filing passages, and personal risk fit without hiding disagreements or missing evidence.</p></div>
        <div className="analysis-control"><div className="control-title"><div><span className="pulse-mark">✦</span><div><h2>Run a new analysis</h2><p>Uses the profile and portfolio shown at left.</p></div></div><span>4 agents</span></div><label htmlFor="company">Company</label><select id="company" value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)} disabled={loading}>{stocks.length ? stocks.map((stock) => <option key={stock.symbol} value={stock.symbol}>{stock.symbol} · {stock.company_name.replace(" (Simulated)", "")}</option>) : SYMBOLS.map((symbol) => <option key={symbol}>{symbol}</option>)}</select><button className="primary-button" onClick={() => void handleAnalyze()} disabled={loading || Boolean(validation)}>{loading ? "Agents are researching…" : "Run Multi-Agent Analysis"}<span>{loading ? "◌" : "→"}</span></button>
          {loading && <div className="execution" aria-live="polite"><p>Pipeline active · {STAGES[stage]}</p><ol>{STAGES.map((item, index) => <li className={index === stage ? "active" : ""} key={item}><span>{index === stage ? "◌" : "○"}</span>{item}</li>)}</ol></div>}
          {message && <div className={`feedback ${message.kind}`} role={message.kind === "error" ? "alert" : "status"}><span>{message.kind === "success" ? "✓" : "!"}</span><p>{message.text}</p>{message.kind === "error" && <button onClick={() => retryAction === "save" ? void handleSave() : void handleAnalyze()}>Retry</button>}</div>}
        </div>
        <div className="scenario-grid"><button onClick={() => setSelectedSymbol("RELIANCE")}><span>Complete</span><strong>RELIANCE</strong><small>Generally positive evidence</small></button><button onClick={() => setSelectedSymbol("TCS")}><span>Conflict</span><strong>TCS</strong><small>Agents disagree visibly</small></button><button onClick={() => setSelectedSymbol("INFY")}><span>Degraded</span><strong>INFY</strong><small>Missing sentiment input</small></button></div>
      </section>
    </section>

    {!analysis && !loading && <section className="first-use"><span>✦</span><div><p className="eyebrow">Your first report starts here</p><h2>Select a company and run the four-agent pipeline.</h2><p>The complete report will keep agent evidence, conflicts, citations, risk context, and missing inputs visible.</p></div></section>}

    {analysis && <section className="results" id="results">
      {(analysis.synthesis.conflicts.length > 0 || analysis.synthesis.missing_evidence.length > 0) && <div className="warning-banner"><span>!</span><div><strong>{analysis.synthesis.missing_evidence.length ? "Degraded-data analysis completed" : "Conflicting signals detected"}</strong><p>{analysis.synthesis.missing_evidence.length ? "The pipeline continued, but missing inputs reduced confidence and are disclosed below." : "Independent agents reached different classifications. Review the evidence before interpreting the synthesis."}</p></div></div>}
      <div className="result-heading"><div><p className="eyebrow">Analysis · {analysis.symbol}</p><h2>{analysis.market_snapshot.company_name.replace(" (Simulated)", "")}</h2><p>Generated {formatDate(analysis.generated_at)} · Analysis ID {analysis.analysis_id.slice(0, 8)}</p></div><Tag value={analysis.market_signal}/></div>

      <section className="synthesis-card"><div className="synthesis-top"><div><p className="eyebrow">Personalized synthesis</p><div className="synthesis-label"><Tag value={analysis.synthesis.classification}/><strong>{analysis.synthesis.confidence}%</strong><span>confidence</span></div></div><div className="risk-used"><span>Risk profile used</span><strong>{titleCase(analysis.profile.risk_profile)}</strong></div></div>{analysis.synthesis.classification === "insufficient_data" ? <h3>Insufficient verified evidence to produce a supported conclusion.</h3> : <h3>{analysis.synthesis.summary}</h3>}<blockquote>{analysis.synthesis.personalized_guidance}</blockquote><div className="synthesis-grid"><ListBlock title="Conflicting signals" items={analysis.synthesis.conflicts} empty="No directional conflict detected"/><ListBlock title="Risk flags" items={analysis.synthesis.risk_flags}/><ListBlock title="Missing evidence" items={analysis.synthesis.missing_evidence} empty="No required evidence missing"/></div></section>

      {snapshot && <section className="panel-section"><div className="panel-heading"><div><p className="eyebrow">Market state</p><h3>Simulated market snapshot</h3></div><span className="sim-label">◆ Simulated · {formatDate(snapshot.data_timestamp)}</span></div><div className="snapshot-grid"><Metric label="Current price" value={formatMoney(snapshot.current_price)}/><Metric label="Previous close" value={formatMoney(snapshot.previous_close)}/><Metric label="Available daily return" value={`${dailyReturn >= 0 ? "+" : ""}${dailyReturn.toFixed(2)}%`}/><Metric label="5-day return" value={`${snapshot.five_day_return >= 0 ? "+" : ""}${snapshot.five_day_return.toFixed(1)}%`}/><Metric label="20-day return" value={`${snapshot.twenty_day_return >= 0 ? "+" : ""}${snapshot.twenty_day_return.toFixed(1)}%`}/><Metric label="Vs. 20-day average" value={`${movingAveragePosition >= 0 ? "+" : ""}${movingAveragePosition.toFixed(2)}%`}/><Metric label="Volume ratio" value={`${volumeRatio.toFixed(2)}×`}/><Metric label="Volatility" value={`${snapshot.volatility.toFixed(1)}%`}/><Metric label="Drawdown" value={`${snapshot.drawdown.toFixed(1)}%`}/></div></section>}

      <section className="panel-section"><div className="panel-heading"><div><p className="eyebrow">Independent dimensions</p><h3>Signal classification</h3></div></div><div className="signal-grid"><article><span className="signal-icon">↗</span><div><small>Price momentum</small><Tag value={technical?.classification ?? "insufficient_data"}/><p>{technical?.summary ?? "Technical evidence unavailable."}</p></div><strong>{technical?.confidence ?? 0}%</strong></article><article><span className="signal-icon">≋</span><div><small>Volume anomaly</small><Tag value={volumeRatio >= 1.4 ? "strong" : "neutral"}/><p>{volumeRatio >= 1.4 ? `Volume is elevated at ${volumeRatio.toFixed(2)}× its average.` : `Volume is near its average at ${volumeRatio.toFixed(2)}×.`}</p></div><strong>{technical?.confidence ?? 0}%</strong></article><article><span className="signal-icon">◉</span><div><small>Sentiment</small><Tag value={sentiment?.classification ?? "insufficient_data"}/><p>{sentiment?.summary ?? "No supported sentiment conclusion."}</p></div><strong>{sentiment?.confidence ?? 0}%</strong></article></div></section>

      <section className="panel-section agent-section"><div className="panel-heading"><div><p className="eyebrow">Specialist research</p><h3>Four independent agent reports</h3></div><span>{analysis.metrics.agents_completed}/{analysis.metrics.agents_expected} completed</span></div><div className="agent-grid">{analysis.agents.map((agent) => <AgentCard output={agent} key={agent.agent}/>)}</div></section>

      <section className="two-panel-grid"><div className="panel-section reasoning-panel"><details open><summary><div><p className="eyebrow">Explainability</p><h3>How the agents reached this conclusion</h3></div><span>＋</span></summary><ol>{analysis.reasoning_trace.map((step, index) => { const category = /market|validated/i.test(step) ? "Raw market observations" : /filing|retriev/i.test(step) ? "Retrieved filing evidence" : /concurrent|agent/i.test(step) ? "Independent agent classifications" : /conflict/i.test(step) ? "Conflict detection" : /profile|risk/i.test(step) ? "Risk-profile adjustment" : "Final synthesis"; return <li key={`${step}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><small>{category}</small><p>{step}</p></div></li>; })}</ol></details></div><div className="panel-section metrics-panel"><div className="panel-heading"><div><p className="eyebrow">Observed performance</p><h3>Analysis metrics</h3></div></div><div className="metrics-grid"><Metric label="Total latency" value={`${analysis.metrics.latency_ms.toFixed(2)} ms`}/><Metric label="Historical accuracy" value={`${analysis.metrics.historical_signal_accuracy_percent.toFixed(1)}%`} note={analysis.metrics.historical_signal_evaluated ? `${analysis.metrics.historical_signal_correct} of ${analysis.metrics.historical_signal_evaluated} fixture signals correct · not live predictive performance` : "Fixture-based historical evaluation · sample unavailable for this older saved analysis"}/><Metric label="Portfolio concentration" value={analysis.metrics.portfolio_concentration_score.toFixed(1)}/><Metric label="Data completeness" value={`${analysis.metrics.data_completeness_percent.toFixed(0)}%`}/><Metric label="Agents complete" value={`${analysis.metrics.agents_completed} / ${analysis.metrics.agents_expected}`}/></div></div></section>

      <section className="panel-section sources-panel"><div className="panel-heading"><div><p className="eyebrow">Traceable evidence</p><h3>Sources used in this analysis</h3></div><span>{analysis.sources.length} cited records</span></div>{analysis.sources.length ? <ul className="source-list">{analysis.sources.map((source) => <SourceItem source={source} agents={analysis.agents} key={`${source.document}-${source.chunk_id}`}/>)}</ul> : <div className="empty-panel"><strong>No cited evidence available</strong><p>The interface will not substitute uncited claims.</p></div>}<details className="evidence-drawer"><summary>View all evidence used by synthesis <span>＋</span></summary><ul>{analysis.synthesis.evidence_used.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></details></section>
    </section>}

    <section className="history-section"><div className="panel-heading"><div><p className="eyebrow">Persisted research</p><h3>Analysis history</h3></div><button className="text-button" onClick={() => void refresh()}>↻ Refresh history</button></div>{history.length ? <div className="history-list">{history.map((item) => <button key={item.analysis_id} onClick={() => reopen(item)}><span><strong>{item.symbol}</strong><small>{formatDate(item.generated_at)}</small></span><Tag value={item.synthesis.classification}/><span><strong>{item.synthesis.confidence}%</strong><small>Confidence</small></span><span><strong>{titleCase(item.profile.risk_profile)}</strong><small>Risk profile</small></span><span><strong>{item.metrics.data_completeness_percent.toFixed(0)}%</strong><small>Complete</small></span><b>Open →</b></button>)}</div> : <div className="empty-panel"><span>⌁</span><strong>No saved analyses yet</strong><p>Completed reports will appear here and can be reopened without rerunning the agents.</p></div>}</section>
    <footer className="site-footer"><div className="brand"><span className="brand-mark">F</span><span><strong>FinSync</strong><small>Intelligence</small></span></div><p>Built for transparent, educational market research with visibly simulated evidence.</p><a href="#top">Back to top ↑</a></footer>
  </main>;
}
