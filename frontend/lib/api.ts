import type { AnalysisResponse, Candle, DecisionAction, HealthResponse, Instrument, MarketQuote, MarketSnapshot, Profile, ProfileInput, UserDecision } from "@/types/analysis";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
export class ApiError extends Error { constructor(message: string, public status?: number) { super(message); this.name = "ApiError"; } }
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new ApiError("The FinSync backend is unavailable. Start the API and try again."); }
  const text = await response.text(); let data: unknown = null;
  if (text) { try { data = JSON.parse(text); } catch { throw new ApiError("The backend returned an unreadable response.", response.status); } }
  if (!response.ok) { const detail = typeof data === "object" && data && "detail" in data ? String((data as { detail: unknown }).detail) : `Request failed (${response.status})`; throw new ApiError(detail, response.status); }
  return data as T;
}
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const root = API_URL === "/api/v1" ? "" : API_URL.replace(/\/api\/v1\/?$/, ""); let response: Response;
  try { response = await fetch(`${root}/health`, { cache: "no-store", signal }); } catch { throw new ApiError("The FinSync backend is unavailable. Start the API and retry."); }
  if (!response.ok) throw new ApiError(`Health check failed (${response.status})`, response.status);
  try { return await response.json() as HealthResponse; } catch { throw new ApiError("The health response was not valid JSON."); }
}
export const listStocks = (signal?: AbortSignal) => request<MarketSnapshot[]>("/stocks", { signal });
export const saveProfile = (profile: ProfileInput, signal?: AbortSignal) => request<Profile>("/profiles", { method: "POST", body: JSON.stringify(profile), signal });
export const runAnalysis = (userId: string, symbol: string, instrumentKey?: string, signal?: AbortSignal) => request<AnalysisResponse>("/analyze", { method: "POST", body: JSON.stringify({ user_id: userId, symbol, instrument_key: instrumentKey }), signal });
export const loadAnalysisHistory = (userId: string, signal?: AbortSignal) => request<AnalysisResponse[]>(`/logs/${encodeURIComponent(userId)}`, { signal });
export const recordDecision = (analysis: AnalysisResponse, action: DecisionAction) => request<UserDecision>("/decisions", { method: "POST", body: JSON.stringify({ user_id: analysis.profile.user_id, ticker: analysis.symbol, action, analysis_id: analysis.analysis_id, current_signal: analysis.market_signal, confidence: analysis.synthesis.confidence }) });
export const loadDecisions = (userId: string, signal?: AbortSignal) => request<UserDecision[]>(`/decisions/${encodeURIComponent(userId)}`, { signal });
export const searchInstruments = (query: string, signal?: AbortSignal) => request<Instrument[]>(`/instruments/search?q=${encodeURIComponent(query)}&limit=12`, { signal });
export const getQuote = (instrumentKey: string, signal?: AbortSignal) => request<MarketQuote>(`/market/quote/${encodeURIComponent(instrumentKey)}`, { signal });
export const getQuotes = (instrumentKeys: string[], signal?: AbortSignal) => request<MarketQuote[]>(`/market/quotes?instrument_keys=${encodeURIComponent(instrumentKeys.join(","))}`, { signal });
export const getCandles = (instrumentKey: string, signal?: AbortSignal) => request<Candle[]>(`/market/candles/${encodeURIComponent(instrumentKey)}`, { signal });
