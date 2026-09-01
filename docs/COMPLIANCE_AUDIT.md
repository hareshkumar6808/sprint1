# Sprint 1 internal compliance audit

This checklist maps the supplied Sprint 1 requirements to executable evidence after the compliance upgrade. “Optional” means the implementation is complete but activation requires explicitly configured credentials or a locally cached model; the offline fallback remains the default.

| Requirement | Implementation | Endpoint/UI | Automated proof | Status |
|---|---|---|---|---|
| Four distinct agents | `backend/app/agents/` | `POST /api/v1/analyze`, agent cards | `test_all_four_agents_and_degraded_sentiment` | Complete |
| Concurrent orchestration and isolation | `services/orchestrator.py` | Analysis replay/metrics | `test_orchestrator_runs_in_parallel_and_isolates_failure` | Complete |
| Structured outputs | `schemas.py`, `llm_provider.py` | Analysis JSON | Pydantic construction throughout; malformed-output test | Complete |
| Semantic RAG and persistent vectors | `services/retrieval.py` | Retrieval/source mode and source cards | `test_semantic_retrieval_and_explicit_tfidf_fallback` | Complete when local MiniLM model is available |
| Truthful TF-IDF fallback | `services/retrieval.py` | `metrics.retrieval_mode` | Same retrieval test | Complete |
| Optional real LLM reasoning | `services/llm_provider.py` | Agent/runtime labels | missing-key and malformed-output test | Optional configuration |
| Simulated and optional live market providers | `services/market_data.py` | Stock/analysis provider metadata | existing market-provider tests | Complete; live activation optional |
| Profile and portfolio persistence | `database.py`, `routes/profiles.py` | Profile editor | API and personalization tests | Complete |
| Material personalization without changing market signal | `agents/behavioral.py`, `synthesizer.py` | Guidance and suitability | `test_conservative_and_aggressive_personalization_differs` | Complete |
| User decisions and history | `routes/decisions.py`, `user_decisions` table | Decision controls/recent decisions | `test_decisions_and_execution_metrics_persist` | Complete |
| Measured execution metrics | `routes/analysis.py`, serialized analysis log | Actual session metrics | persistence/metrics tests | Complete |
| Citation-only synthesis | `services/synthesizer.py` | Sources and evidence drawer | `test_no_uncited_recommendation_and_confidence_reduction` | Complete |
| Complete/conflict/degraded demos | local fixtures and agents | Scenario controls | scenario and Decision Lab tests | Complete |
| Transparent UI runtime state | response types and `Dashboard.tsx` | Runtime strip, connection badge, degraded cards | frontend typecheck/build | Complete |
| Dynamic NSE/BSE catalogue | `services/instruments.py`, SQLite instruments | instrument search/status/refresh APIs | dynamic market tests | Complete; real count depends on sync |
| Official Upstox market adapter | `services/upstox.py` | quote/batch quote and dynamic analysis | mocked auth/rate/cache/candle tests | Optional live configuration |
| Arbitrary instrument identity | profile holding/watchlist tables and instrument keys | search/select/watch/portfolio UI | persistence and dynamic analysis tests | Complete |
| Safe arbitrary document ingestion | `routes/documents.py`, document association table | admin API | ingestion/leakage test | Complete local ingestion |
| Educational safety | synthesis guard, disclaimer | persistent disclaimer | synthesis tests | Complete |

The supplied request references a PDF but no PDF file was present in the repository or attachment set. This audit therefore maps the explicit requirements in the supplied task text and does not claim coverage of unseen material.
