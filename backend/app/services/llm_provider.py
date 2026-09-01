"""Optional structured OpenAI-compatible reasoning; deterministic execution remains the default."""
import json

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.schemas import AgentOutput


class LLMProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return self.settings.llm_provider == "openai" and bool(self.settings.llm_api_key)

    async def refine(self, role: str, deterministic: AgentOutput) -> AgentOutput:
        if not self.configured:
            return deterministic
        allowed_ids = deterministic.evidence_ids or [source.source_id for source in deterministic.sources if source.source_id]
        prompt = {
            "role": role,
            "instruction": "Return concise JSON matching the supplied AgentOutput. Do not add evidence or source IDs. No chain-of-thought.",
            "allowed_evidence_ids": allowed_ids,
            "deterministic_observation": deterministic.model_dump(mode="json"),
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                    json={"model": self.settings.llm_model, "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": "You are a bounded financial research classifier."},
                                       {"role": "user", "content": json.dumps(prompt)}]})
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            candidate = AgentOutput.model_validate_json(content)
            if (candidate.agent != deterministic.agent or
                    not set(candidate.evidence_ids) <= set(allowed_ids) or
                    not set(candidate.evidence) <= set(deterministic.evidence)):
                raise ValueError("LLM output referenced an invalid role, claim, or evidence ID")
            return candidate.model_copy(update={"runtime_mode": "llm", "sources": deterministic.sources})
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            return deterministic.model_copy(update={"warnings": [*deterministic.warnings,
                f"LLM output degraded safely: {type(exc).__name__}"]})
