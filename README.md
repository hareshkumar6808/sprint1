# FinSync Intelligence

FinSync Intelligence is a local-first, multi-agent financial research application for retail investors. It combines current or visibly simulated market data, local evidence, and a stored investor profile into a traceable educational report. It does not provide trading execution, direct buy/sell instructions, or guaranteed outcomes.

## Problem and solution

Retail investors often see isolated price signals without the evidence, conflicts, suitability context, or data-quality limitations behind them. FinSync runs four independent agents concurrently, uses local semantic embeddings when a cached model is available, falls back explicitly to TF-IDF, preserves every agent result, and synthesizes only cited evidence. Optional LLM and live-market modes never replace the reliable offline demonstration.

The `agents` array remains the stable four-agent frontend contract. `analytical_units` is additive and records all 12 A–Z units: the four original specialists; concurrent Regulatory, Macro/Regime, and Portfolio Risk specialists; Devil's Advocate, Missing Information, Evidence Verification, and Committee/Conflict review; and bounded Synthesis. Unavailable benchmark or regulatory material produces `insufficient_data` rather than inferred facts.

## Architecture and data flow

```mermaid
flowchart LR
  M[Yahoo / Upstox / Simulated Market Data] --> S1[Stage 1 concurrent specialists]
  N[Attributed News] --> S1
  F[Local Text/PDF Corpus] --> R[MiniLM semantic retrieval / TF-IDF fallback] --> S1
  P[Profile + Portfolio + Decisions] --> S1
  S1 --> C[Four-agent compatibility response]
  S1 --> S2[Stage 2 adversarial and evidence review]
  S2 --> S3[Stage 3 bounded synthesis]
  C --> API[Typed FastAPI response]
  S3 --> API
  API --> D[Next.js dashboard]
  API --> L[SQLite investigations, events, journals, predictions]
```

1. The frontend saves a risk profile, portfolio, watchlist, and interaction context.
2. The API validates the stored user and selected symbol.
3. Local market, news, and filing fixtures are loaded without filling missing values.
4. Four deterministic base agents run through `asyncio.gather()` with timestamps, latency, evidence IDs, and per-agent failure isolation. If configured, bounded LLM refinement is validated back through the same Pydantic contract.
5. Filing queries retrieve traceable semantic chunks for revenue, profitability, debt, guidance, and risk. If the local embedding model cannot load, the response reports `tfidf_fallback`.
6. Regulatory, Macro/Regime, and Portfolio Risk specialists run concurrently as additional Stage 1 units. Stage 2 performs adversarial review, missing-information assessment, citation verification, and committee voting.
7. Deterministic synthesis detects agreement, conflict, missing evidence, freshness, and profile constraints. An optional validated LLM refinement cannot introduce evidence IDs or claims outside the deterministic result.
8. The complete typed response is logged in SQLite and rendered by the dashboard. Evidence-derived events and unevaluated predictions are stored separately for later reliability assessment.

## Agent roles and decision logic

| Agent | Role | Output labels |
|---|---|---|
| Technical | Scores 5-day/20-day momentum, moving-average position, volume ratio, volatility, and drawdown. | `bullish`, `neutral`, `bearish` |
| Sentiment | Aggregates only local synthetic news records and preserves record-level attribution. | `positive`, `neutral`, `negative`, or `insufficient_data` |
| Fundamental/RAG | Classifies only text returned by the filing retriever; every claim maps to a document and chunk ID. | `strong`, `mixed`, `weak`, or `insufficient_data` |
| Behavioral | Compares volatility, horizon, risk profile, interaction history, and portfolio concentration. | `suitable`, `neutral`, `unsuitable` |

The additive committee units are:

| Stage | Unit | Behavior when evidence is missing |
|---|---|---|
| 1 | Regulatory Intelligence | Returns `insufficient_data` without instrument-associated regulatory evidence. |
| 1 | Macro and Market Regime | Returns the `unknown` regime without benchmark/macro series. |
| 1 | Portfolio Risk | Uses supplied holdings only; returns `insufficient_data` when holdings are absent. |
| 2 | Devil's Advocate | Selects the strongest sourced counterargument; does not invent an opposing thesis. |
| 2 | Missing Information | Lists unavailable inputs and their confidence impact. |
| 2 | Evidence Verification | Maps claims to supplied evidence IDs and flags unsupported claims. |
| 2 | Committee/Conflict | Records supportive, opposing, and neutral votes plus consensus/fragility. |
| 3 | Synthesis | Reuses structured outputs and cannot introduce new facts. |

The synthesis layer maps agent classifications to deterministic directional scores. Missing agents reduce confidence by fixed penalties; conflicting directions also reduce confidence. If no cited evidence exists, synthesis returns `insufficient_data` and produces no uncited conclusion. Guidance uses educational language such as “consider,” “monitor,” and “investigate further.”

Historical accuracy is calculated only from `historical_signals.json` as correct fixture outcomes divided by evaluated fixture outcomes. The response includes both counts, and the dashboard explicitly distinguishes this small synthetic evaluation from live predictive performance.

## Retrieval and citations

`FilingRetriever` splits each local synthetic or explicitly ingested filing into paragraph chunks. When the configured local MiniLM sentence-transformer is cached, normalized semantic embeddings are persisted in `backend/app/data/filing_vectors.json` with a corpus fingerprint and queried by cosine similarity. Each result retains source ID, title, document, chunk ID, excerpt, and relevance score. Candidate selection is isolated by symbol before ranking, preventing one company's document from being retrieved for another. If the model/dependency cannot load, the same interface uses TF-IDF and truthfully reports `tfidf_fallback`; it is never described as vector retrieval. Bundled documents remain synthetic demonstration material, while ingested documents retain their supplied attribution.

## Dynamic NSE/BSE market provider

FinSync synchronizes all supported ordinary NSE/BSE equity instruments returned by the configured Upstox BOD catalogue; it does not claim every security listed by either exchange independently of that provider catalogue. The official Upstox JSON master is normalized into SQLite using `instrument_key` as the stable identity, then searched locally by symbol, name, ISIN, and exchange. Exact symbols rank first. The UI debounces search and never embeds or renders the complete catalogue.

Provider flow:

1. `POST /api/v1/instruments/refresh?force=true` downloads the official complete JSON master and upserts only `NSE_EQ`/`BSE_EQ` records whose `instrument_type` is `EQ`.
2. `GET /api/v1/instruments/search?q=...&exchange=NSE` searches indexed SQLite data without a remote keystroke request.
3. `GET /api/v1/market/quote/{instrument_key}` retrieves one selected quote. `GET /api/v1/market/quotes?instrument_keys=...` batches visible watchlist keys where Upstox is active.
4. Analysis downloads and caches daily candles on demand, validates and orders them, removes duplicate timestamps, and calculates returns, moving average, volume anomaly, volatility, drawdown, and RSI only when enough history exists.
5. Quote results are cached for `QUOTE_CACHE_SECONDS`; candles are cached for `CANDLE_CACHE_SECONDS`. Upstox standard API limits are documented by Upstox as 50 requests/second, 500/minute and 2,000/30 minutes. FinSync does not poll continuously.

### Free Yahoo Finance mode (default)

Upstox quotes require an authenticated, KYC-verified brokerage account. For users who do not want to supply brokerage credentials, FinSync uses Yahoo Finance's public chart service on demand without an API key. The synchronized Upstox master remains the searchable universe; only the selected instrument and visible watchlist/portfolio instruments are queried remotely.

```dotenv
MARKET_DATA_MODE=free
MARKET_DATA_PROVIDER=yahoo
YAHOO_FINANCE_ENABLED=true
YAHOO_QUOTE_CACHE_SECONDS=30
YAHOO_CANDLE_CACHE_SECONDS=900
```

NSE symbols map to `<trading_symbol>.NS` and BSE symbols to `<trading_symbol>.BO`; the internal `instrument_key` is never changed. Returned Yahoo metadata must identify the exact mapped symbol. Company-stock (`INE`) and ETF/fund (`INF`) categories are exposed as a useful, explicitly fallible ISIN heuristic; raw instrument type is retained and unknown EQ records remain searchable under “All supported.”

Yahoo Finance is an unofficial market-data provider. Its delay is not guaranteed or independently verified, market-closed values are the latest available close/trade, and data is labelled `unverified_delay` or `cached`—never exchange-certified, broker data, or guaranteed live. It must not be used for trading or order execution.

Provider priority is explicit: free mode uses Yahoo, then a recent Yahoo cache, then simulated data only for the original offline fixtures; arbitrary instruments never receive a fixture price. Upstox mode uses authenticated Upstox, its cache, optional Yahoo fallback when `YAHOO_ALLOW_FALLBACK=true`, and finally the same fixture-only fallback. Quotes use limited retries, request coalescing, short caches, and a failure cooldown; daily candles use a longer cache and include adjusted close when available.

Arbitrary catalogue instruments can still run the full pipeline. Technical evidence uses their quote/history; Fundamental and Sentiment degrade to `insufficient_data` when no associated document or attributed news exists, rather than borrowing another company's evidence.

Official references: [Upstox instruments](https://upstox.com/developer/api-documentation/instruments/), [full market quotes](https://upstox.com/developer/api-documentation/get-full-market-quote/), [historical candle V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/), and [rate limits](https://upstox.com/developer/api-documentation/rate-limiting/).

### Upstox developer setup

Create an Upstox developer application and complete Upstox OAuth outside FinSync to obtain an access token. FinSync does not implement login, store refresh tokens, or expose tokens to the browser. Put the access token only in the private `backend/.env` runtime file:

```dotenv
MARKET_DATA_MODE=live
MARKET_DATA_PROVIDER=upstox
UPSTOX_ACCESS_TOKEN=
```

An empty token keeps the app in the guaranteed offline mode. Upstox access tokens can expire; a 401/403 is reported as invalid/expired, 429 as rate-limited, timeouts as unavailable, and malformed/partial responses as provider errors. For original demo symbols only, failures can fall back to visibly simulated fixtures. Arbitrary instruments without live data return an explicit error rather than borrowed or fabricated data.

### Market-data status meanings

| Mode | Exact meaning |
|---|---|
| `live` | A quote was obtained directly from an authenticated provider that reports it as live. Yahoo never uses this label. |
| `delayed` | Provider metadata explicitly identifies delayed data. FinSync never infers this label. |
| `unverified_delay` | Yahoo current data whose delay cannot be independently guaranteed. |
| `cached` | A recent previously retrieved quote was reused within the configured TTL. |
| `simulated` | The bundled local fixture was used and is not market data. |

Backend connectivity, provider name, market-data mode/freshness, agent runtime, retrieval mode, and agent completeness are displayed separately. “API connected” never means a quote is live.

### Local document ingestion

Administrators can `POST /api/v1/documents` with `instrument_key`, matching symbol/company metadata, title, source date, document type, attribution, and either UTF-8 text or base64 PDF content. FinSync validates the key/symbol and media type, enforces `DOCUMENT_MAX_BYTES`, normalizes extracted text, stores the association in SQLite, and writes a local text source for chunking. Retrieval filters by the selected symbol and tests prevent cross-company citation leakage. There is no automatic regulatory-site scraper; only explicitly supplied local documents and the three richer demo filings are available.

## Persistence

SQLite stores profiles, normalized holdings/watchlists, decisions, complete serialized investigations, document associations, deduplicated events, journals, predictions/outcomes, catalogue state, and audit-ready metadata. Startup migrations are additive: existing databases gain missing columns/tables without destructive recreation. Catalogue migration also recovers omitted ISIN values from stable Upstox instrument keys so valid `INE` stocks and `INF` funds remain visible under category filters. History endpoints validate saved analysis responses through Pydantic, and new response fields have defaults so older records remain readable.

## Technology

- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, built-in `sqlite3`
- Orchestration: Python `asyncio`
- Retrieval: optional sentence-transformer semantic embeddings with a persistent JSON vector store; scikit-learn TF-IDF fallback
- Optional reasoning: xAI or legacy OpenAI-compatible Chat Completions, bounded by schema validation, evidence allowlists, concurrency, timeout, retry, budget, and cooldown controls
- Market data: free no-key Yahoo Finance, optional authenticated Upstox, legacy Alpha Vantage, and offline fixtures
- Tests: pytest, FastAPI TestClient/httpx

## Folder structure

```text
backend/
  app/agents/       Four specialist agents and shared contract exports
  app/services/     Market provider, retrieval, orchestration, synthesis, metrics
  app/routes/       Health, stocks, profiles, analysis, and logs endpoints
  app/data/         Simulated market/news/history fixtures and synthetic filings
  tests/            Agent, API, scenario, metrics, retrieval, and persistence tests
frontend/
  app/              Next.js route, metadata, icon, and responsive theme
  components/       Complete interactive dashboard
  lib/              Typed API client
  types/            Backend-aligned TypeScript response types
```

## Installation

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
cp .env.example backend/.env
```

No API keys or external accounts are required for the offline demo. Semantic retrieval uses MiniLM only when the model is already cached locally; otherwise the backend reports `tfidf_fallback`. To cache MiniLM once while online:

```bash
source .venv/bin/activate
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

Runtime environment variables are documented in the root `.env.example`. Because the backend starts with `backend/` as its working directory and uses `SettingsConfigDict(env_file=".env")`, copy that example to the private runtime file `backend/.env`. Secrets are read only by the backend; never place real credentials in `.env.example`, frontend variables, browser storage, or Git.

### Runtime configurations

| Goal | Required settings | Credentials |
|---|---|---|
| Fully offline demo | `MARKET_DATA_MODE=simulated` | None |
| Free selected-instrument data | `MARKET_DATA_MODE=free`, `MARKET_DATA_PROVIDER=yahoo`, `YAHOO_FINANCE_ENABLED=true` | None |
| Authenticated Upstox data | `MARKET_DATA_MODE=live`, `MARKET_DATA_PROVIDER=upstox`, `UPSTOX_ACCESS_TOKEN=...` | Upstox access token |
| Deterministic agents only | Leave LLM keys empty | None |
| xAI refinement | `LLM_PROVIDER=xai`, `XAI_API_KEY=...`, `XAI_MODEL=...` | xAI API key and an account-accessible model |
| Legacy OpenAI-compatible refinement | `LLM_PROVIDER=openai`, `LLM_API_KEY=...`, `LLM_MODEL=...` | Provider API key |

Recommended no-key configuration:

```dotenv
MARKET_DATA_MODE=free
MARKET_DATA_PROVIDER=yahoo
YAHOO_FINANCE_ENABLED=true
LLM_PROVIDER=xai
XAI_API_KEY=
XAI_MODEL=
SEMANTIC_RETRIEVAL_ENABLED=true
```

With empty xAI credentials, analysis remains operational and reports the LLM runtime as `disabled`; it does not pretend Grok was used.

## Run locally

Backend terminal:

```bash
cd /Users/pavans/Desktop/sprint1
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```bash
cd /Users/pavans/Desktop/sprint1/frontend
npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000`. API documentation is at `http://127.0.0.1:8000/docs`.

Verify both services:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/system/status
curl -I http://127.0.0.1:3000
```

If a port is already occupied, check for an existing development server before starting a duplicate process.

## Tests and build

```bash
cd /Users/pavans/Desktop/sprint1/backend
../.venv/bin/pytest
../.venv/bin/python -m compileall -q app tests

cd /Users/pavans/Desktop/sprint1/frontend
npm run lint
npm run typecheck
npm run build
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API identity |
| GET | `/health` | Service health and version |
| GET | `/api/v1/stocks` | Validated simulated market snapshots |
| GET | `/api/v1/instruments/search` | Search the synchronized NSE/BSE equity catalogue |
| GET | `/api/v1/instruments/status` | Catalogue count and last synchronization result |
| POST | `/api/v1/instruments/refresh` | Refresh/upsert the official catalogue; `force=true` bypasses TTL |
| GET | `/api/v1/market/quote/{instrument_key}` | Selected-instrument quote with provider/freshness metadata |
| GET | `/api/v1/market/quotes` | Batch visible watchlist quote lookup |
| GET | `/api/v1/market/candles/{instrument_key}` | Normalized, ordered historical candles |
| GET | `/api/v1/market/status` | Active market provider and honest access/data status |
| POST | `/api/v1/documents` | Ingest an attributed local instrument document |
| POST | `/api/v1/profiles` | Create or update a user profile |
| GET | `/api/v1/profiles/{user_id}` | Load a stored profile |
| POST | `/api/v1/analyze` | Run and persist the four-agent pipeline |
| GET | `/api/v1/logs/{user_id}` | Load complete saved analyses |
| POST | `/api/v1/decisions` | Persist BUY/SELL/WATCH/IGNORE/INVESTIGATE |
| GET | `/api/v1/decisions/{user_id}` | Load recent user decisions |
| GET | `/api/v1/system/status` | Sanitized backend, market, retrieval, and LLM runtime configuration |
| GET | `/api/v1/investigations` | Paginated investigation history for a user |
| GET | `/api/v1/investigations/{analysis_id}` | Complete typed investigation detail |
| GET | `/api/v1/investigations/{analysis_id}/committee` | Committee units, weights, and regime detail |
| POST | `/api/v1/investigations/{analysis_id}/source-removal` | Deterministic source-sensitivity simulation |
| POST | `/api/v1/investigations/{analysis_id}/confidence-stress` | Apply explicit confidence penalties; confidence cannot increase |
| POST | `/api/v1/portfolio/simulate` | Before/after allocation and concentration simulation |
| POST | `/api/v1/portfolio/shock` | Linear disclosed-assumption portfolio shock simulation |
| GET | `/api/v1/time-travel/{symbol}` | Analyses stored at or before `as_of`; excludes look-ahead records |
| POST | `/api/v1/journals` | Persist a thesis/action journal entry |
| GET | `/api/v1/journals/{user_id}` | Load journal history |
| GET | `/api/v1/behavior/{user_id}` | Evidence-thresholded behavioral patterns or insufficient history |
| GET | `/api/v1/events` | Filterable deduplicated event history |
| GET | `/api/v1/predictions` | Stored predictions and available outcome fields |
| GET | `/api/v1/agent-performance` | Reliability only after the configured evaluated sample minimum |

Example profile:

```json
{
  "user_id": "demo-user",
  "risk_profile": "conservative",
  "investment_horizon_years": 8,
  "maximum_volatility": 15,
  "portfolio": [
    {"symbol": "TCS", "weight": 70},
    {"symbol": "RELIANCE", "weight": 30}
  ],
  "watchlist": ["TCS"],
  "interaction_history": [{"action": "viewed", "symbol": "TCS"}]
}
```

Example analysis request:

```json
{"user_id": "demo-user", "symbol": "TCS"}
```

Copy-paste API flow:

```bash
# Create/update a profile.
curl -X POST http://127.0.0.1:8000/api/v1/profiles \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"demo-user","risk_profile":"moderate","investment_horizon_years":8,"maximum_volatility":25,"portfolio":[{"symbol":"TCS","weight":70},{"symbol":"RELIANCE","weight":30}],"watchlist":["TCS"],"interaction_history":[]}'

# Search the local catalogue. The category filter is optional.
curl 'http://127.0.0.1:8000/api/v1/instruments/search?q=HDFCBANK&category=stock&limit=12'

# Run analysis for a bundled offline scenario.
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"demo-user","symbol":"TCS"}'

# Inspect saved investigations and runtime truthfulness.
curl 'http://127.0.0.1:8000/api/v1/investigations?user_id=demo-user'
curl http://127.0.0.1:8000/api/v1/system/status
```

For arbitrary catalogue instruments, include the selected stable key:

```json
{
  "user_id": "demo-user",
  "symbol": "HDFCBANK",
  "instrument_key": "NSE_EQ|INE040A01034"
}
```

The response keeps the frontend-compatible `agents` array at four units and adds the complete committee under `analytical_units`. `runtime_mode`, `retrieval_mode`, `market_snapshot.data_mode`, `fallback_reason`, warnings, evidence IDs, and source metadata must be interpreted independently. Backend connectivity alone does not prove that market data or an LLM call is live.

The authoritative generated contract is [`backend/openapi-a-z.json`](backend/openapi-a-z.json). Interactive request/response schemas are available from `/docs` while the API is running.

## Demonstration scenarios

- **RELIANCE — complete:** generally positive evidence, 4/4 completed agents, 100% data completeness, and traceable market/news/filing/profile sources.
- **TCS — conflict:** favorable technical momentum conflicts with weaker retrieved fundamentals and profile suitability. Confidence is reduced. Switching between conservative and aggressive profiles changes Behavioral Agent output and personalized guidance for the same market snapshot.
- **INFY — degraded:** no synthetic news records exist. Sentiment returns `unavailable` and `insufficient_data`; the other three agents complete, completeness is 75%, confidence is reduced, and missing evidence remains visible.

### Live judge sequence

1. Configure a valid Upstox access token, use live mode, start the backend, and force one catalogue refresh.
2. Search a company or symbol, select its NSE/BSE listing, and verify the Upstox/provider timestamp and `live` or `cached` badge.
3. Add the instrument key to the watchlist or portfolio, save, and run analysis.
4. Inspect candle-derived technical evidence. If no local filing/news exists, point out the degraded Fundamental/Sentiment agents, lower confidence, sources, and Decision Laboratory gaps.

### Offline judge sequence

Use `MARKET_DATA_MODE=simulated` for a network-free run. The bundled six-equity catalogue fixture supports search UI demonstrations. Run RELIANCE, TCS, and INFY from “Offline demo scenarios” to show complete, conflicting, and degraded behavior. Non-fixture instruments are never silently assigned simulated prices.

## Two-minute demo

1. Start both services and open the dashboard.
2. Confirm the green API status and persistent simulated-data label.
3. Save the default conservative profile and run RELIANCE to show the complete evidence path.
4. Run TCS and point out the conflict banner, agent classifications, citations, and fixture sample size.
5. Change the profile to Aggressive, save, and rerun TCS to show different suitability guidance.
6. Run INFY to demonstrate graceful degradation and missing sentiment evidence.
7. Reopen an item from Analysis History without rerunning the pipeline.

## Requirement compliance audit

| Requirement | Implementation | Demo evidence | Status |
|---|---|---|---|
| Price, volume, technical data | `market_data.json`, `market_data.py`, `/api/v1/stocks` | Three validated simulated snapshots | Complete |
| Financial document corpus | `app/data/filings/*.txt` | One synthetic multi-section filing per company | Complete |
| Semantic relevance retrieval | `services/retrieval.py` | MiniLM embeddings when locally available; explicit TF-IDF fallback | Optional semantic runtime / complete fallback |
| Multi-agent orchestration | `services/orchestrator.py` | Four results preserved through `asyncio.gather()` | Complete |
| Behavioral profiling | `agents/behavioral.py`, `/api/v1/profiles` | Conservative/aggressive TCS results differ | Complete |
| Visualization/interface | `frontend/components/Dashboard.tsx` | Responsive profile, signals, agents, evidence, metrics, history | Complete |
| Logging and persistence | `database.py`, `/api/v1/logs/{user_id}` | Complete typed responses reopen from SQLite | Complete |
| Three independent dimensions | Dashboard signal panel and agent outputs | Momentum, volume anomaly, sentiment shown separately | Complete |
| Momentum signal | `agents/technical.py` | 5/20-day returns and moving-average position | Complete |
| Volume-anomaly signal | `calculate_features`, Technical Agent | Volume ratio shown with label and explanation | Complete |
| Sentiment signal | `agents/sentiment.py` | Positive/neutral/negative or explicit unavailable | Complete |
| Labels and confidence | Shared `AgentOutput` contract | Every agent card shows both | Complete |
| Cited reasoning | `Source`, evidence arrays, reasoning trace | Claims connect to local feeds/chunks | Complete |
| RAG-grounded output | `retrieval.py`, `fundamental.py` | Fundamental claims contain retrieved chunk IDs | Complete |
| Visible attribution | Analysis `sources`; Sources panel | Title, document, date, chunk, associated agent | Complete |
| Three agents in parallel | Four agents in `run_agents` | Concurrency/failure-isolation test | Complete |
| Structured contracts | `schemas.py`, `types/analysis.ts` | Pydantic and TypeScript shapes align | Complete |
| Synthesis layer | `services/synthesizer.py` | Deterministic classification/conflict/confidence | Complete |
| Profile personalization | Behavioral Agent and synthesis guidance | Identical TCS input differs by risk profile | Complete |
| Portfolio/watchlist | Profile schema and dashboard editor | Editable holdings, allocation validation, watchlist | Complete |
| Current market signals | Snapshot and signal panels | Price, returns, average, volume, volatility, drawdown | Complete |
| Agent reasoning | Agent evidence plus `reasoning_trace` | Expandable ordered explanation | Complete |
| Execution metrics | `AnalysisMetrics` | Total/per-agent/retrieval latency, chunks, coverage, agreement, concentration, fallbacks and modes | Complete |
| User decisions | `routes/decisions.py`, SQLite | Controls and recent-decision history | Complete |
| Optional LLM agents | `services/llm_provider.py` | Runtime labels and safe deterministic fallback | Optional configuration |
| Live-data fallback | `services/market_data.py` | Provider, freshness and fallback reason | Optional live configuration / complete fallback |
| End-to-end scenario | `/api/v1/analyze`; RELIANCE | Profile → agents → synthesis → SQLite → dashboard | Complete |
| Degraded scenario | INFY missing news | 3/4, 75%, sentiment unavailable | Complete |
| Conflicting scenario | TCS fixture | Conflict banner and confidence penalty | Complete |
| No uncited conclusion | `synthesize()` guard | No sources returns `insufficient_data` | Complete |
| Architecture/logic summary | This README and Mermaid diagram | Written flow, roles, retrieval, synthesis, safety | Complete |

## A–Z backend additions and integration

The generated, sanitized integration contract is `backend/openapi-a-z.json`. The frontend branch can continue consuming all old fields and optionally adopt `analytical_units`, `regime`, and `synthesis_weights`. It should generate types from this contract after merge rather than copying backend enums by hand.

Additional endpoints include:

- `GET /api/v1/system/status`, `/api/v1/market/status`, and `/api/v1/market/candles/{instrument_key}` for explicit runtime and provider state.
- `GET /api/v1/investigations`, investigation detail, committee detail, source-removal, and confidence-stress routes.
- `POST /api/v1/portfolio/simulate` and `/api/v1/portfolio/shock`, with assumptions and `insufficient_data` where risk inputs are absent.
- `GET /api/v1/time-travel/{symbol}`, `/api/v1/events`, `/api/v1/predictions`, and `/api/v1/agent-performance`.
- `POST/GET /api/v1/journals` and `GET /api/v1/behavior/{user_id}`. Behavioral patterns require at least five stored actions; reliability requires `RELIABILITY_MIN_SAMPLES` evaluated predictions.

SQLite startup migrations add `events`, `journals`, `predictions`, and `audit_events`, plus additive expanded profile JSON. Analysis writes deduplicated evidence-derived events and unevaluated predictions. It does not calculate accuracy until actual outcomes have been stored.

### Grok/xAI setup

Set `LLM_PROVIDER=xai`, `XAI_API_KEY`, and an account-accessible `XAI_MODEL` only in `backend/.env`. The default base URL is `https://api.x.ai/v1`. Requests use structured JSON Schema output, Pydantic validation, timeouts, bounded concurrency, transient retry, a daily-call budget, and cooldown after rate limiting. With a missing key or model the runtime is `disabled`; malformed/refused/provider-failed calls are `degraded` and retain deterministic output. No real xAI credential or call is used by the test suite. The endpoint and structured-output shape were selected from the official [xAI structured outputs documentation](https://docs.x.ai/developers/model-capabilities/text/structured-outputs).

### Document ingestion

`POST /api/v1/documents` accepts normalized UTF-8 text or base64 PDF content, enforces `DOCUMENT_MAX_BYTES`, validates instrument identity and media type, and keeps retrieval isolated by symbol. PDF extraction uses `pypdf`. MiniLM is used only when the configured model is already available locally; otherwise retrieval explicitly reports `tfidf_fallback`.

### Two-person demo handoff

1. Backend developer starts in simulated mode, creates a profile, and runs RELIANCE, TCS, and INFY.
2. Frontend developer shows the unchanged four-agent interface, then optionally renders the additive committee and Decision Lab fields.
3. Backend developer opens system status, an investigation's committee detail, source-removal stress, event history, and reliability status.
4. Both identify fixture data as simulated, Yahoo as unofficial/unverified-delay, xAI as disabled unless an authenticated request succeeds, and historical reliability as insufficient until the minimum evaluated sample exists.

### A–Z implementation status

| Capability | Status | Exact boundary |
|---|---|---|
| Simulated, Yahoo, and Upstox providers | Implemented | Yahoo/Upstox external responses are mock-tested; availability and credentials remain external. |
| Catalogue normalization and category filtering | Implemented | Supports provider catalogue records; category is an ISIN-prefix heuristic and raw type is retained. |
| xAI structured refinement | Implemented, optional | Disabled without both key and model; no real credential was used in automated verification. |
| 12-unit committee audit trail | Implemented | Four-agent frontend contract remains separate and stable. |
| MiniLM/TF-IDF RAG and citation isolation | Implemented | MiniLM requires a locally cached model; no regulatory web scraper exists. |
| Events, journals, predictions, reliability | Implemented | Outcome accuracy remains unavailable until sufficient real evaluations are stored. |
| Decision Lab simulations | Implemented | Deterministic and assumption-labelled; no unsupported sensitivities are invented. |
| Expanded profile persistence | Implemented additively | Existing profile payloads and SQLite databases remain compatible. |
| OpenAPI integration contract | Implemented | Regenerate after future schema/route changes. |
| Order execution or guaranteed recommendations | Intentionally not implemented | FinSync is educational research software. |

## Troubleshooting

- **A searched stock says “No supported instruments found.”** Clear or change the Exchange/Category filters and check `/api/v1/instruments/status`. Current startup migration recovers `INE`/`INF` identities from Upstox instrument keys so records such as HDFCBANK remain visible as stocks.
- **A previous company remains in “Selected instrument.”** Search results do not automatically replace the selection. Click the desired result before running analysis.
- **“Upstox live mode is not configured.”** This is an honest fallback message. Configure a valid access token, use Yahoo free mode, or choose simulated mode.
- **`runtime_mode` is `disabled` or `degraded`.** Confirm `LLM_PROVIDER`, key, model, credits, and network access. Deterministic analysis continues safely.
- **`retrieval_mode` is `tfidf_fallback`.** Cache the configured MiniLM model locally and restart the backend, or keep the explicit lexical fallback.
- **An arbitrary symbol has no filing/news analysis.** Ingest attributed material for that exact instrument. FinSync will not borrow evidence from another company.
- **Port 3000 or 8000 is already in use.** Reuse or stop the existing development process rather than starting another server.

## Limitations and disclaimers

- All bundled market records, news, filing summaries, and historical outcomes are synthetic and visibly marked simulated.
- Fixture-based historical accuracy uses a very small sample and is not evidence of live-market predictive performance.
- The local synthetic corpus is deliberately small and is not a substitute for verified regulatory filings. Semantic mode depends on a locally available embedding model; otherwise the UI reports TF-IDF fallback.
- xAI, legacy OpenAI-compatible refinement, Alpha Vantage, and Upstox modes are optional and inactive without credentials. No transaction execution or external citation service is provided.
- Yahoo and xAI behavior is mock-verified only in automated tests; no live provider request was used for this implementation. Yahoo availability depends on its unofficial public chart service. Upstox depends on a valid user-supplied token.
- Regime remains `unknown` without benchmark data. Portfolio risk, sector exposure, correlations, and shock sensitivity remain `insufficient_data` unless supplied; deterministic simulations state their assumptions.
- The local catalogue fixture contains six equity listings (four NSE and two BSE) plus one deliberately filtered futures record. A real catalogue count depends on the latest successful Upstox synchronization.
- Live quote/candle behavior requires a valid Upstox access token. No real credential was used by the offline automated tests; provider responses are mocked.
- Market-open status is reported `closed` outside ordinary session hours/weekends and otherwise `unknown`, because FinSync does not fabricate holiday/session status without an authoritative status response.
- A missing feed or agent reduces completeness and confidence; without cited evidence the system returns `insufficient_data`.

FinSync Intelligence is educational research software, not personalized financial advice. It does not guarantee returns or issue direct buy/sell instructions.
