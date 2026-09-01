"""Bounded structured LLM refinement with truthful deterministic fallback."""
import asyncio
import json
from datetime import date
from time import monotonic
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.schemas import AgentOutput


class LLMProvider:
    _calls_by_day: dict[str, int] = {}
    _cooldown_until: float = 0

    def __init__(self) -> None:
        self.settings = get_settings()
        self._semaphore = asyncio.Semaphore(max(1, self.settings.xai_max_concurrency))

    @property
    def configured(self) -> bool:
        if self.settings.llm_provider == "xai":
            return bool(self.settings.xai_api_key and self.settings.xai_model)
        return self.settings.llm_provider == "openai" and bool(self.settings.llm_api_key)

    def _configuration(self) -> tuple[str, str, str, float, int, str]:
        if self.settings.llm_provider == "xai":
            return (str(self.settings.xai_api_key), self.settings.xai_base_url.rstrip("/"), str(self.settings.xai_model),
                    self.settings.xai_timeout_seconds, self.settings.xai_max_retries, "xai")
        return (str(self.settings.llm_api_key), "https://api.openai.com/v1", self.settings.llm_model,
                self.settings.llm_timeout_seconds, 0, "llm")

    def _budget_available(self) -> bool:
        limit = self.settings.xai_daily_budget_calls if self.settings.llm_provider == "xai" else None
        return limit is None or self._calls_by_day.get(date.today().isoformat(), 0) < limit

    async def refine(self, role: str, deterministic: AgentOutput) -> AgentOutput:
        if not self.configured:
            return deterministic.model_copy(update={"runtime_mode": "disabled" if self.settings.llm_provider == "xai" else "deterministic_fallback",
                                                     "fallback_reason": "LLM credentials/model are not configured"})
        if monotonic() < self._cooldown_until or not self._budget_available():
            reason = "LLM provider cooldown is active" if monotonic() < self._cooldown_until else "Daily LLM call budget reached"
            return deterministic.model_copy(update={"runtime_mode": "degraded", "fallback_reason": reason,
                                                     "warnings": [*deterministic.warnings, reason]})
        allowed_ids = deterministic.evidence_ids or [source.source_id for source in deterministic.sources if source.source_id]
        prompt = {"role": role, "instruction": "Return only concise validated JSON. Do not add facts, sources, advice, or chain-of-thought.",
                  "allowed_evidence_ids": allowed_ids, "deterministic_observation": deterministic.model_dump(mode="json")}
        api_key, base_url, model, timeout, retries, runtime = self._configuration()
        failure: Exception | None = None
        async with self._semaphore:
            for attempt in range(retries + 1):
                try:
                    today = date.today().isoformat()
                    self._calls_by_day[today] = self._calls_by_day.get(today, 0) + 1
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}"},
                            json={"model": model, "response_format": {"type": "json_schema", "json_schema": {"name": "agent_output", "strict": True, "schema": AgentOutput.model_json_schema()}},
                                  "messages": [{"role": "system", "content": "You are a bounded financial research classifier."},
                                               {"role": "user", "content": json.dumps(prompt)}]})
                    response.raise_for_status()
                    body: dict[str, Any] = response.json()
                    message = body["choices"][0]["message"]
                    if message.get("refusal"):
                        raise ValueError("Provider refused the structured request")
                    candidate = AgentOutput.model_validate_json(message["content"])
                    if candidate.agent != deterministic.agent or not set(candidate.evidence_ids) <= set(allowed_ids) or not set(candidate.evidence) <= set(deterministic.evidence):
                        raise ValueError("LLM output referenced an invalid role, claim, or evidence ID")
                    usage = body.get("usage") or {}
                    return candidate.model_copy(update={"runtime_mode": runtime, "model": body.get("model", model), "sources": deterministic.sources,
                        "warnings": [*candidate.warnings, *([f"LLM usage: {usage}"] if usage else [])]})
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
                    failure = exc
                    transient = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {429, 500, 502, 503, 504})
                    if transient and attempt < retries:
                        await asyncio.sleep(min(1.0, .1 * (2 ** attempt)))
                        continue
                    break
        if isinstance(failure, httpx.HTTPStatusError) and failure.response.status_code == 429:
            type(self)._cooldown_until = monotonic() + self.settings.llm_cooldown_seconds
        label = type(failure).__name__ if failure else "UnknownError"
        return deterministic.model_copy(update={"runtime_mode": "degraded" if self.settings.llm_provider == "xai" else "deterministic_fallback", "fallback_reason": label,
            "warnings": [*deterministic.warnings, f"LLM output degraded safely: {label}"]})
