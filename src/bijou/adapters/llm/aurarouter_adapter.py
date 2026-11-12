"""Authentic AuraRouter LLM reasoning broker adapter for Bijou v2."""

import json
from typing import Any

import httpx

from bijou.core.contracts.views import (
    BillOfEffortsSimulationResponseDTO,
    PerspectiveBriefingDTO,
)
from bijou.core.ports.exceptions import ServiceUnavailableError
from bijou.core.ports.reasoning import IReasoningBroker


class AuraRouterAdapter(IReasoningBroker):
    """Connects to AuraRouter via HTTP transport to synthesize executive briefings & recommendations."""

    def __init__(
        self,
        aurarouter_url: str | None = None,
        model: str = "bijou-strategic-reasoner",
        timeout: float = 10.0,
    ) -> None:
        self._url = aurarouter_url
        self._model = model
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Dispose of HTTP transport client."""
        self._client.close()

    def synthesize_executive_briefing(
        self,
        briefing: PerspectiveBriefingDTO,
        org_mission: str,
    ) -> tuple[str, list[str]]:
        """Synthesize an executive narrative summary and identify strategic gaps."""
        if not self._url:
            raise ServiceUnavailableError("AuraRouter URL is not configured")

        prompt_payload = {
            "model": self._model,
            "mission_statement": org_mission,
            "subject_org_id": briefing.subject_org_id,
            "total_allocated_usd": briefing.total_allocated_usd,
            "direct_efforts": [n.effort.name for n in briefing.directly_resourced_efforts],
            "indirect_benefits_count": len(briefing.indirect_benefits),
            "active_risks": [r.title for r in briefing.active_risks],
        }

        try:
            resp = self._client.post(
                f"{self._url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a strategic decision-support analyst. "
                                "Return JSON with keys 'executive_summary' (string) and 'strategic_gaps' (list of strings)."
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt_payload)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code != 200:
                raise ServiceUnavailableError(f"AuraRouter returned HTTP {resp.status_code}: {resp.text}")

            result: dict[str, Any] = resp.json()
            choices = result.get("choices", [])
            if not choices:
                raise ServiceUnavailableError("AuraRouter response missing choices")

            content = choices[0].get("message", {}).get("content", "{}")
            parsed = json.loads(content)
            return parsed.get("executive_summary", ""), parsed.get("strategic_gaps", [])

        except (httpx.HTTPError, OSError) as err:
            raise ServiceUnavailableError(f"AuraRouter connection to '{self._url}' failed: {err}") from err

    def recommend_portfolio_tradeoff(
        self,
        simulation: BillOfEffortsSimulationResponseDTO,
    ) -> str:
        """Provide strategic recommendation on simulated Bill of Efforts adjustments."""
        if not self._url:
            raise ServiceUnavailableError("AuraRouter URL is not configured")

        try:
            summary = {
                "impacted_efforts": simulation.impacted_effort_ids,
                "total_cost_delta": simulation.total_cost_delta,
                "net_risk_count_delta": simulation.net_risk_count_delta,
                "skill_warnings": [w.message for w in simulation.skill_mismatch_warnings],
            }
            resp = self._client.post(
                f"{self._url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a portfolio optimization advisor. Provide a concise 2-sentence recommendation.",
                        },
                        {"role": "user", "content": json.dumps(summary)},
                    ],
                },
            )
            if resp.status_code != 200:
                raise ServiceUnavailableError(f"AuraRouter returned HTTP {resp.status_code}: {resp.text}")

            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except (httpx.HTTPError, OSError) as err:
            raise ServiceUnavailableError(f"AuraRouter connection to '{self._url}' failed: {err}") from err
