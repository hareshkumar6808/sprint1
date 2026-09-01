"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getCandles, getHealth, getQuote, getQuotes, loadAnalysisHistory, loadDecisions, recordDecision, runAnalysis, saveProfile as persistProfile, searchInstruments } from "@/lib/api";
import { DECISION_LAB_PREVIEW } from "@/lib/decision-lab-fixture";
import { DecisionLab } from "@/components/DecisionLab";
import { AllocationPie, PriceChart } from "@/components/DataCharts";
import type { AgentOutput, AnalysisResponse, Candle, Classification, DecisionAction, Instrument, MarketQuote, ProfileInput, RiskProfile, Source, UserDecision } from "@/types/analysis";

const DEMO_INSTRUMENTS: Record<string, Instrument> = {
  RELIANCE: { instrument_key: "NSE_EQ|INE002A01018", exchange: "NSE", symbol: "RELIANCE", name: "RELIANCE INDUSTRIES LTD", isin: "INE002A01018", instrument_type: "EQ" },
  TCS: { instrument_key: "NSE_EQ|INE467B01029", exchange: "NSE", symbol: "TCS", name: "TATA CONSULTANCY SERVICES LTD", isin: "INE467B01029", instrument_type: "EQ" },
  INFY: { instrument_key: "NSE_EQ|INE009A01021", exchange: "NSE", symbol: "INFY", name: "INFOSYS LTD", isin: "INE009A01021", instrument_type: "EQ" },
};
const USER_ID = "demo-user";
const STAGES = ["Loading market data", "Retrieving filing evidence", "Running specialist agents", "Synthesizing personalized guidance"];
const AGENT_META = {
  technical: ["Technical Agent", "Momentum, volume & market risk", "↗"],
  sentiment: ["Sentiment Agent", "Local news evidence", "◉"],
  fundamental: ["Fundamental / RAG Agent", "Retrieved filing evidence", "⌘"],
  behavioral: ["Behavioral Agent", "Personal risk suitability", "◇"],
} as const;
type EditableHolding = { symbol: string; instrumentKey: string; exchange: string; weight: string };

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
    <footer><span>{titleCase(output.runtime_mode ?? "deterministic_fallback")}</span><strong>{output.latency_ms.toFixed(2)} ms</strong></footer>
  </article>;
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</article>; }

function SourceItem({ source, agents }: { source: Source; agents: AgentOutput[] }) {
  const associated = agents.filter((agent) => agent.sources.some((item) => item.document === source.document && item.chunk_id === source.chunk_id)).map((agent) => AGENT_META[agent.agent][0]);
  return <li className="source-item"><div><span className="source-symbol">§</span><div><strong>{source.title}</strong><p>{source.document}</p>{source.excerpt && <p>{source.excerpt}</p>}</div></div><dl><div><dt>Date</dt><dd>{source.date}</dd></div>{source.chunk_id && <div><dt>Chunk</dt><dd>{source.chunk_id}</dd></div>}{source.relevance_score != null && <div><dt>Relevance</dt><dd>{(source.relevance_score * 100).toFixed(1)}%</dd></div>}<div><dt>Used by</dt><dd>{associated.join(", ") || "Synthesis"}</dd></div></dl><span className="sim-label">{source.document.startsWith("provider:") ? "Provider source" : "Simulated/local source"}</span></li>;
}

export function Dashboard() {

  const [history, setHistory] = useState<AnalysisResponse[]>([]);
  const [decisions, setDecisions] = useState<UserDecision[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("TCS");
  const [selectedInstrument, setSelectedInstrument] = useState<Instrument>(DEMO_INSTRUMENTS.TCS);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Instrument[]>([]);
  const [searching, setSearching] = useState(false);
  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [quoteError, setQuoteError] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [risk, setRisk] = useState<RiskProfile>("conservative");
  const [horizon, setHorizon] = useState("8");
  const [maxVolatility, setMaxVolatility] = useState("15");
  const [holdings, setHoldings] = useState<EditableHolding[]>([{ symbol: "TCS", instrumentKey: DEMO_INSTRUMENTS.TCS.instrument_key, exchange: "NSE", weight: "70" }, { symbol: "RELIANCE", instrumentKey: DEMO_INSTRUMENTS.RELIANCE.instrument_key, exchange: "NSE", weight: "30" }]);
  const [watchlist, setWatchlist] = useState<string[]>([DEMO_INSTRUMENTS.TCS.instrument_key]);
  const [watchQuotes, setWatchQuotes] = useState<Record<string, MarketQuote>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [retryAction, setRetryAction] = useState<"save" | "analyze">("analyze");

  const allocation = holdings.reduce((sum, holding) => sum + (Number.isFinite(Number(holding.weight)) ? Number(holding.weight) : 0), 0);
  const horizonNumber = Number(horizon);
  const volatilityNumber = Number(maxVolatility);
  const profilePayload = useMemo<ProfileInput>(() => ({ user_id: USER_ID, risk_profile: risk, investment_horizon_years: horizonNumber, maximum_volatility: volatilityNumber, portfolio: holdings.map((holding) => ({ symbol: holding.symbol, instrument_key: holding.instrumentKey, exchange: holding.exchange, weight: Number(holding.weight) })), watchlist, interaction_history: [{ action: "viewed", symbol: selectedSymbol, instrument_key: selectedInstrument.instrument_key }] }), [risk, horizonNumber, volatilityNumber, holdings, watchlist, selectedSymbol, selectedInstrument]);
  const validation = horizon.trim() === "" ? "Investment horizon is required." : !Number.isFinite(horizonNumber) || !Number.isInteger(horizonNumber) || horizonNumber < 1 || horizonNumber > 50 ? "Investment horizon must be a whole number from 1 to 50 years." : maxVolatility.trim() === "" ? "Maximum volatility is required." : !Number.isFinite(volatilityNumber) || volatilityNumber < 0 || volatilityNumber > 100 ? "Maximum volatility must be a number from 0% to 100%." : holdings.some((holding) => holding.weight.trim() === "" || !Number.isFinite(Number(holding.weight)) || Number(holding.weight) < 0 || Number(holding.weight) > 100) ? "Each portfolio weight must be a number from 0% to 100%." : Math.abs(allocation - 100) > 0.001 ? `Portfolio allocation must total 100%. Current total: ${allocation.toFixed(2).replace(/\.00$/, "")}%.` : "";

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const results = await Promise.allSettled([getHealth(signal), loadAnalysisHistory(USER_ID, signal), loadDecisions(USER_ID, signal)]);

    if (results[1].status === "fulfilled") setHistory(results[1].value);
    if (results[2].status === "fulfilled") setDecisions(results[2].value);
  }, []);

  useEffect(() => { const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort(); }, [refresh]);
  useEffect(() => { if (searchQuery.trim().length < 2) { setSearchResults([]); return; } const controller = new AbortController(); const timer = window.setTimeout(async () => { setSearching(true); try { setSearchResults(await searchInstruments(searchQuery, controller.signal)); } catch { setSearchResults([]); } finally { setSearching(false); } }, 300); return () => { controller.abort(); window.clearTimeout(timer); }; }, [searchQuery]);
  useEffect(() => { const controller = new AbortController(); setQuote(null); setCandles([]); setQuoteError(""); void Promise.allSettled([getQuote(selectedInstrument.instrument_key, controller.signal), getCandles(selectedInstrument.instrument_key, controller.signal)]).then(([quoteResult, candleResult]) => { if (quoteResult.status === "fulfilled") setQuote(quoteResult.value); else setQuoteError(quoteResult.reason instanceof Error ? quoteResult.reason.message : "Quote unavailable"); if (candleResult.status === "fulfilled") setCandles(candleResult.value); }); return () => controller.abort(); }, [selectedInstrument]);
  useEffect(() => { if (!watchlist.length) { setWatchQuotes({}); return; } const controller = new AbortController(); void getQuotes(watchlist, controller.signal).then((items) => setWatchQuotes(Object.fromEntries(items.map((item) => [item.instrument_key, item])))).catch(() => setWatchQuotes({})); return () => controller.abort(); }, [watchlist]);
  useEffect(() => { if (!loading) return; const timer = window.setInterval(() => setStage((current) => Math.min(current + 1, STAGES.length - 1)), 850); return () => window.clearInterval(timer); }, [loading]);

  async function handleSave(showSuccess = true) {
    if (validation) { setRetryAction(showSuccess ? "save" : "analyze"); setMessage({ kind: "error", text: validation }); return false; }
    setSaving(true); setMessage(null);
    try { await persistProfile(profilePayload); if (showSuccess) setMessage({ kind: "success", text: "Profile and portfolio saved for demo-user." }); return true; }
    catch (error) { setRetryAction(showSuccess ? "save" : "analyze"); setMessage({ kind: "error", text: error instanceof Error ? error.message : "Unable to save the profile." }); return false; }
    finally { setSaving(false); }
  }

  async function handleAnalyze() {
    if (loading) return;
    const saved = await handleSave(false); if (!saved) return;
    setLoading(true); setStage(0); setMessage(null);
    try { const result = await runAnalysis(USER_ID, selectedSymbol, selectedInstrument.instrument_key); setAnalysis(result); setMessage({ kind: "success", text: `${selectedSymbol} analysis completed with ${result.metrics.agents_completed} of ${result.metrics.agents_expected} agents.` }); const updated = await loadAnalysisHistory(USER_ID); setHistory(updated); window.setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }), 50); }
    catch (error) { setRetryAction("analyze"); setMessage({ kind: "error", text: error instanceof Error ? error.message : "Analysis failed. Please retry." }); }
    finally { setLoading(false); }
  }

  function updateHolding(index: number, field: "weight", value: string) { setHoldings((current) => current.map((holding, itemIndex) => itemIndex === index ? { ...holding, [field]: numericDraft(value) } : holding)); }
  function normalizeHolding(index: number) { setHoldings((current) => current.map((holding, itemIndex) => itemIndex === index ? { ...holding, weight: normalizedNumber(holding.weight) } : holding)); }
  function addHolding() { if (!holdings.some((holding) => holding.instrumentKey === selectedInstrument.instrument_key)) setHoldings((current) => [...current, { symbol: selectedInstrument.symbol, instrumentKey: selectedInstrument.instrument_key, exchange: selectedInstrument.exchange, weight: "0" }]); }
  function reopen(item: AnalysisResponse) { setAnalysis(item); setSelectedSymbol(item.symbol); document.getElementById("results")?.scrollIntoView({ behavior: "smooth" }); }
  function chooseInstrument(item: Instrument) { setSelectedInstrument(item); setSelectedSymbol(item.symbol); setSearchQuery(""); setSearchResults([]); }
  async function decide(action: DecisionAction) { if (!analysis) return; try { await recordDecision(analysis, action); setDecisions(await loadDecisions(USER_ID)); setMessage({ kind: "success", text: `${action} decision recorded.` }); } catch (error) { setMessage({ kind: "error", text: error instanceof Error ? error.message : "Decision could not be recorded." }); } }

  const snapshot = analysis?.market_snapshot;
  const technical = analysis?.agents.find((agent) => agent.agent === "technical");
  const sentiment = analysis?.agents.find((agent) => agent.agent === "sentiment");
  const volumeRatio = snapshot?.average_volume ? snapshot.current_volume / snapshot.average_volume : 0;
  const movingAveragePosition = snapshot?.twenty_day_moving_average ? (snapshot.current_price / snapshot.twenty_day_moving_average - 1) * 100 : 0;
  const dailyReturn = snapshot ? (snapshot.current_price / snapshot.previous_close - 1) * 100 : 0;

  return <div className="dashboard-content">

    <section className="command-grid">
      <aside className="profile-column">
        <div className="section-heading"><div><p className="eyebrow">Research context</p><h2>Profile & portfolio</h2></div><span className="user-chip">demo-user</span></div>
        <div className="form-card"><div className="field"><label htmlFor="risk">Risk profile</label><select id="risk" value={risk} onChange={(event) => setRisk(event.target.value as RiskProfile)}><option value="conservative">Conservative</option><option value="moderate">Balanced</option><option value="aggressive">Aggressive</option></select><small>Changes suitability and personalized guidance.</small></div><div className="two-fields"><div className="field"><label htmlFor="horizon">Horizon <span>years</span></label><input id="horizon" type="text" inputMode="numeric" value={horizon} aria-invalid={Boolean(validation && /horizon/i.test(validation))} onChange={(event) => setHorizon(numericDraft(event.target.value))} onBlur={() => setHorizon(normalizedNumber(horizon))}/></div><div className="field"><label htmlFor="volatility">Max volatility <span>%</span></label><input id="volatility" type="text" inputMode="decimal" value={maxVolatility} aria-invalid={Boolean(validation && /volatility/i.test(validation))} onChange={(event) => setMaxVolatility(numericDraft(event.target.value))} onBlur={() => setMaxVolatility(normalizedNumber(maxVolatility))}/></div></div></div>
        <div className="form-card portfolio-card"><div className="card-title"><div><h3>Holdings</h3><p>Instrument keys prevent exchange collisions.</p></div><strong className={Math.abs(allocation - 100) <= 0.001 ? "valid" : "invalid"}>{allocation.toFixed(2).replace(/\.00$/, "")}% allocated</strong></div>{holdings.map((holding, index) => <div className="holding-row" key={holding.instrumentKey}><span className="holding-identity"><strong>{holding.symbol}</strong><small>{holding.exchange}</small></span><label><input aria-label={`${holding.symbol} allocation`} type="text" inputMode="decimal" value={holding.weight} onChange={(event) => updateHolding(index, "weight", event.target.value)} onBlur={() => normalizeHolding(index)}/><span>%</span></label><button className="icon-button" type="button" aria-label={`Remove ${holding.symbol}`} onClick={() => setHoldings((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></div>)}<button className="text-button" type="button" onClick={addHolding} disabled={holdings.some((holding) => holding.instrumentKey === selectedInstrument.instrument_key)}>＋ Add selected instrument</button>{validation && <p className="validation-text" role="alert">{validation}</p>}<div className="watchlist"><h4>Watchlist</h4><div>{watchlist.map((key) => <label key={key}><span>{watchQuotes[key]?.symbol ?? key}<small>{watchQuotes[key] ? `${formatMoney(watchQuotes[key].last_price)} · ${watchQuotes[key].data_mode}` : "Quote unavailable"}</small></span><button type="button" className="icon-button" onClick={() => setWatchlist((current) => current.filter((item) => item !== key))}>×</button></label>)}</div><button className="text-button" type="button" disabled={watchlist.includes(selectedInstrument.instrument_key)} onClick={() => setWatchlist((current) => [...current, selectedInstrument.instrument_key])}>＋ Watch selected</button></div><button className="secondary-button" onClick={() => void handleSave()} disabled={saving}>{saving ? "Saving profile…" : "Save profile & portfolio"}</button></div>
      </aside>

      <section className="research-column">
        <div className="hero-copy"><p className="eyebrow">Research command center</p><h1>Independent agents.<br/><em>One supported view.</em></h1><p>Inspect market behavior, synthetic news, retrieved filing passages, and personal risk fit without hiding disagreements or missing evidence.</p></div>
        <section className="live-chart-grid" aria-label="Live market and portfolio charts">
          <article className="chart-card"><div><p className="eyebrow">90-day price history</p><h3>{selectedSymbol} closing price</h3></div>{candles.length > 1 ? <PriceChart candles={candles}/> : <p className="search-state">Loading actual closing-price history…</p>}</article>
          <article className="chart-card allocation-card"><div><p className="eyebrow">Portfolio</p><h3>Allocation</h3></div><AllocationPie items={holdings.map((holding) => ({ symbol: holding.symbol, weight: Number(holding.weight) || 0 }))}/><div className="pie-legend">{holdings.map((holding) => <small key={holding.instrumentKey}>{holding.symbol} {holding.weight || "0"}%</small>)}</div></article>
        </section>
        <div className="analysis-control"><div className="control-title"><div><span className="pulse-mark">✦</span><div><h2>Search Indian equities</h2><p>Searches the synchronized NSE/BSE catalogue locally.</p></div></div><span>4 agents</span></div><label htmlFor="instrument-search">Company or symbol</label><input id="instrument-search" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="e.g. HDFC Bank or HDFCBANK" autoComplete="off"/>{searching && <p className="search-state">Searching catalogue…</p>}{searchQuery.length >= 2 && !searching && !searchResults.length && <p className="search-state">No supported equity instruments found.</p>}{searchResults.length > 0 && <ul className="instrument-results" role="listbox">{searchResults.map((item) => <li key={item.instrument_key}><button role="option" aria-selected={item.instrument_key === selectedInstrument.instrument_key} onClick={() => chooseInstrument(item)}><strong>{item.symbol}</strong><span>{item.name}</span><b>{item.exchange}</b></button></li>)}</ul>}<div className="selected-instrument"><div><small>Selected instrument</small><strong>{selectedInstrument.symbol} · {selectedInstrument.exchange}</strong><span>{selectedInstrument.name}</span></div>{quote ? <div><small>{quote.provider_name} · {quote.data_mode}</small><strong>{formatMoney(quote.last_price)}</strong><span>{quote.provider_timestamp ? formatDate(quote.provider_timestamp) : quote.freshness}</span></div> : <div><small>Quote</small><span>{quoteError || "Loading…"}</span></div>}</div>{quote?.fallback_reason && <p className="quote-warning">⚠ {quote.fallback_reason}</p>}<button className="primary-button" onClick={() => void handleAnalyze()} disabled={loading || Boolean(validation)}>{loading ? "Agents are researching…" : "Run Multi-Agent Analysis"}<span>{loading ? "◌" : "→"}</span></button>
          {loading && <div className="execution" aria-live="polite"><p>Pipeline active · {STAGES[stage]}</p><ol>{STAGES.map((item, index) => <li className={index === stage ? "active" : ""} key={item}><span>{index === stage ? "◌" : "○"}</span>{item}</li>)}</ol></div>}
          {message && <div className={`feedback ${message.kind}`} role={message.kind === "error" ? "alert" : "status"}><span>{message.kind === "success" ? "✓" : "!"}</span><p>{message.text}</p>{message.kind === "error" && <button onClick={() => retryAction === "save" ? void handleSave() : void handleAnalyze()}>Retry</button>}</div>}
        </div>
        <p className="eyebrow demo-label">Offline demo scenarios</p><div className="scenario-grid"><button onClick={() => chooseInstrument(DEMO_INSTRUMENTS.RELIANCE)}><span>Complete</span><strong>RELIANCE</strong><small>Generally positive evidence</small></button><button onClick={() => chooseInstrument(DEMO_INSTRUMENTS.TCS)}><span>Conflict</span><strong>TCS</strong><small>Agents disagree visibly</small></button><button onClick={() => chooseInstrument(DEMO_INSTRUMENTS.INFY)}><span>Degraded</span><strong>INFY</strong><small>Missing sentiment input</small></button></div>
      </section>
    </section>

    {!analysis && !loading && <section className="first-use"><span>✦</span><div><p className="eyebrow">Your first report starts here</p><h2>Select a company and run the four-agent pipeline.</h2><p>The complete report will keep agent evidence, conflicts, citations, risk context, and missing inputs visible.</p></div></section>}

    {analysis && <section className="results" id="results">
      {(analysis.synthesis.conflicts.length > 0 || analysis.synthesis.missing_evidence.length > 0) && <div className="warning-banner"><span>!</span><div><strong>{analysis.synthesis.missing_evidence.length ? "Degraded-data analysis completed" : "Conflicting signals detected"}</strong><p>{analysis.synthesis.missing_evidence.length ? "The pipeline continued, but missing inputs reduced confidence and are disclosed below." : "Independent agents reached different classifications. Review the evidence before interpreting the synthesis."}</p></div></div>}
      <div className="result-heading"><div><p className="eyebrow">Analysis · {analysis.symbol}</p><h2>{analysis.market_snapshot.company_name.replace(" (Simulated)", "")}</h2><p>Generated {formatDate(analysis.generated_at)} · Analysis ID {analysis.analysis_id.slice(0, 8)}</p></div><Tag value={analysis.market_signal}/></div>

      <section className="runtime-strip" aria-label="Active runtime modes"><span>Market: <strong>{titleCase(analysis.metrics.market_data_mode ?? (analysis.market_snapshot.simulated_data ? "simulated" : "live"))}</strong></span><span>Agents: <strong>{titleCase(analysis.metrics.runtime_mode ?? "deterministic_fallback")}</strong></span><span>Retrieval: <strong>{titleCase(analysis.metrics.retrieval_mode ?? "unavailable")}</strong></span>{analysis.market_snapshot.fallback_reason && <span>Fallback: <strong>{analysis.market_snapshot.fallback_reason}</strong></span>}</section>

      <section className="synthesis-card"><div className="synthesis-top"><div><p className="eyebrow">Personalized synthesis</p><div className="synthesis-label"><Tag value={analysis.synthesis.classification}/><strong>{analysis.synthesis.confidence}%</strong><span>confidence</span></div></div><div className="risk-used"><span>Risk profile used</span><strong>{titleCase(analysis.profile.risk_profile)}</strong></div></div>{analysis.synthesis.classification === "insufficient_data" ? <h3>Insufficient verified evidence to produce a supported conclusion.</h3> : <h3>{analysis.synthesis.summary}</h3>}<blockquote>{analysis.synthesis.personalized_guidance}</blockquote><div className="synthesis-grid"><ListBlock title="Conflicting signals" items={analysis.synthesis.conflicts} empty="No directional conflict detected"/><ListBlock title="Risk flags" items={analysis.synthesis.risk_flags}/><ListBlock title="Missing evidence" items={analysis.synthesis.missing_evidence} empty="No required evidence missing"/></div><a className="lab-entry-button" href="#decision-lab">Open Decision Lab <span aria-hidden="true">→</span></a></section>

      <section className="decision-controls"><div><p className="eyebrow">Record your decision</p><h3>What will you do next?</h3></div><div>{(["BUY", "SELL", "WATCH", "IGNORE", "INVESTIGATE"] as DecisionAction[]).map((action) => <button key={action} onClick={() => void decide(action)}>{action}</button>)}</div></section>

      <DecisionLab data={analysis.decision_lab ?? DECISION_LAB_PREVIEW} analysis={analysis} preview={!analysis.decision_lab}/>

      {snapshot && <section className="panel-section"><div className="panel-heading"><div><p className="eyebrow">Market state</p><h3>{titleCase(snapshot.data_mode ?? (snapshot.simulated_data ? "simulated" : "live"))} market snapshot</h3></div><span className="sim-label">◆ {snapshot.provider_name} · {formatDate(snapshot.data_timestamp)}</span></div><div className="snapshot-grid"><Metric label="Current price" value={formatMoney(snapshot.current_price)}/><Metric label="Previous close" value={formatMoney(snapshot.previous_close)}/><Metric label="Available daily return" value={`${dailyReturn >= 0 ? "+" : ""}${dailyReturn.toFixed(2)}%`}/><Metric label="5-day return" value={snapshot.five_day_return == null ? "Unavailable" : `${snapshot.five_day_return >= 0 ? "+" : ""}${snapshot.five_day_return.toFixed(1)}%`}/><Metric label="20-day return" value={snapshot.twenty_day_return == null ? "Unavailable" : `${snapshot.twenty_day_return >= 0 ? "+" : ""}${snapshot.twenty_day_return.toFixed(1)}%`}/><Metric label="Vs. 20-day average" value={snapshot.twenty_day_moving_average == null ? "Unavailable" : `${movingAveragePosition >= 0 ? "+" : ""}${movingAveragePosition.toFixed(2)}%`}/><Metric label="Volume ratio" value={snapshot.average_volume == null ? "Unavailable" : `${volumeRatio.toFixed(2)}×`}/><Metric label="RSI (14)" value={snapshot.rsi == null ? "Unavailable" : snapshot.rsi.toFixed(1)}/><Metric label="Volatility" value={`${snapshot.volatility.toFixed(1)}%`}/><Metric label="Drawdown" value={`${snapshot.drawdown.toFixed(1)}%`}/></div></section>}

      <section className="panel-section"><div className="panel-heading"><div><p className="eyebrow">Independent dimensions</p><h3>Signal classification</h3></div></div><div className="signal-grid"><article><span className="signal-icon">↗</span><div><small>Price momentum</small><Tag value={technical?.classification ?? "insufficient_data"}/><p>{technical?.summary ?? "Technical evidence unavailable."}</p></div><strong>{technical?.confidence ?? 0}%</strong></article><article><span className="signal-icon">≋</span><div><small>Volume anomaly</small><Tag value={volumeRatio >= 1.4 ? "strong" : "neutral"}/><p>{volumeRatio >= 1.4 ? `Volume is elevated at ${volumeRatio.toFixed(2)}× its average.` : `Volume is near its average at ${volumeRatio.toFixed(2)}×.`}</p></div><strong>{technical?.confidence ?? 0}%</strong></article><article><span className="signal-icon">◉</span><div><small>Sentiment</small><Tag value={sentiment?.classification ?? "insufficient_data"}/><p>{sentiment?.summary ?? "No supported sentiment conclusion."}</p></div><strong>{sentiment?.confidence ?? 0}%</strong></article></div></section>

      <section className="panel-section agent-section"><div className="panel-heading"><div><p className="eyebrow">Specialist research</p><h3>Four independent agent reports</h3></div><span>{analysis.metrics.agents_completed}/{analysis.metrics.agents_expected} completed</span></div><div className="agent-grid">{analysis.agents.map((agent) => <AgentCard output={agent} key={agent.agent}/>)}</div></section>

      <section className="two-panel-grid"><div className="panel-section reasoning-panel"><details open><summary><div><p className="eyebrow">Explainability</p><h3>How the agents reached this conclusion</h3></div><span>＋</span></summary><ol>{analysis.reasoning_trace.map((step, index) => { const category = /market|validated/i.test(step) ? "Raw market observations" : /filing|retriev/i.test(step) ? "Retrieved filing evidence" : /concurrent|agent/i.test(step) ? "Independent agent classifications" : /conflict/i.test(step) ? "Conflict detection" : /profile|risk/i.test(step) ? "Risk-profile adjustment" : "Final synthesis"; return <li key={`${step}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><small>{category}</small><p>{step}</p></div></li>; })}</ol></details></div><div className="panel-section metrics-panel"><div className="panel-heading"><div><p className="eyebrow">Observed performance</p><h3>Actual session metrics</h3></div></div><div className="metrics-grid"><Metric label="Total latency" value={`${analysis.metrics.latency_ms.toFixed(2)} ms`}/><Metric label="Retrieval latency" value={`${(analysis.metrics.retrieval_latency_ms ?? 0).toFixed(2)} ms`}/><Metric label="Retrieved chunks" value={`${analysis.metrics.chunks_retrieved ?? 0}`}/><Metric label="Evidence coverage" value={`${(analysis.metrics.evidence_coverage_percent ?? 0).toFixed(0)}%`}/><Metric label="Agent agreement" value={`${(analysis.metrics.agent_agreement_percent ?? 0).toFixed(0)}%`}/><Metric label="Fallback activations" value={`${analysis.metrics.fallback_activations ?? 0}`}/><Metric label="Portfolio concentration" value={analysis.metrics.portfolio_concentration_score.toFixed(1)}/><Metric label="Data completeness" value={`${analysis.metrics.data_completeness_percent.toFixed(0)}%`}/><Metric label="Agents complete" value={`${analysis.metrics.agents_completed} / ${analysis.metrics.agents_expected}`}/><Metric label="Historical accuracy" value={`${analysis.metrics.historical_signal_accuracy_percent.toFixed(1)}%`} note={analysis.metrics.historical_signal_evaluated ? `${analysis.metrics.historical_signal_correct} of ${analysis.metrics.historical_signal_evaluated} fixture signals correct · not live predictive performance` : "Fixture sample unavailable"}/></div></div></section>

      <section className="panel-section sources-panel"><div className="panel-heading"><div><p className="eyebrow">Traceable evidence</p><h3>Sources used in this analysis</h3></div><span>{analysis.sources.length} cited records</span></div>{analysis.sources.length ? <ul className="source-list">{analysis.sources.map((source) => <SourceItem source={source} agents={analysis.agents} key={`${source.document}-${source.chunk_id}`}/>)}</ul> : <div className="empty-panel"><strong>No cited evidence available</strong><p>The interface will not substitute uncited claims.</p></div>}<details className="evidence-drawer"><summary>View all evidence used by synthesis <span>＋</span></summary><ul>{analysis.synthesis.evidence_used.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></details></section>
    </section>}

    <section className="history-section"><div className="panel-heading"><div><p className="eyebrow">Persisted research</p><h3>Analysis history</h3></div><button className="text-button" onClick={() => void refresh()}>↻ Refresh history</button></div>{history.length ? <div className="history-list">{history.map((item) => <button key={item.analysis_id} onClick={() => reopen(item)}><span><strong>{item.symbol}</strong><small>{formatDate(item.generated_at)}</small></span><Tag value={item.synthesis.classification}/><span><strong>{item.synthesis.confidence}%</strong><small>Confidence</small></span><span><strong>{titleCase(item.profile.risk_profile)}</strong><small>Risk profile</small></span><span><strong>{item.metrics.data_completeness_percent.toFixed(0)}%</strong><small>Complete</small></span><b>Open →</b></button>)}</div> : <div className="empty-panel"><span>⌁</span><strong>No saved analyses yet</strong><p>Completed reports will appear here and can be reopened without rerunning the agents.</p></div>}</section>
    <section className="history-section"><div className="panel-heading"><div><p className="eyebrow">Persisted actions</p><h3>Recent decisions</h3></div></div>{decisions.length ? <div className="decision-history">{decisions.slice(0, 8).map((item) => <article key={item.id}><strong>{item.action}</strong><span>{item.ticker}</span><small>{item.current_signal} · {item.confidence}% · {formatDate(item.created_at)}</small></article>)}</div> : <div className="empty-panel"><strong>No decisions recorded</strong><p>Choose an action from a completed analysis.</p></div>}</section>
  </div>;
}
