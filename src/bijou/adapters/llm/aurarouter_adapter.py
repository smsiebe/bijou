"""Authentic AuraRouter LLM reasoning broker adapter."""

from typing import Any

import httpx

from bijou.core.contracts.views import (
    PerspectiveBriefingDTO,
    TradeoffProposalComparisonDTO,
)
from bijou.core.ports.exceptions import ServiceUnavailableError
from bijou.core.ports.reasoning import IReasoningBroker


class AuraRouterAdapter(IReasoningBroker):
    """Authentic AuraRouter LLM reasoning adapter.

    Connects to AuraRouter via HTTP transport and synthesizes executive takeaways.
    Raises ServiceUnavailableError when unconfigured or unreachable (Rule 10).
    """

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
        """Synthesize an executive narrative summary and identify strategic blind-spots."""
        if not self._url:
            raise ServiceUnavailableError("AuraRouter URL is not configured")

        prompt_payload = {
            "model": self._model,
            "mission_statement": org_mission,
            "subject_org_id": briefing.subject_org_id,
            "perspective_org_id": briefing.perspective_org_id,
            "portfolio_roi_score": briefing.portfolio_roi_score,
            "total_committed_cost": briefing.total_committed_cost,
            "supported_concerns": [
                {
                    "concern_id": c.concern_id,
                    "name": c.concern_name,
                    "coverage_score": c.coverage_score,
                }
                for c in briefing.supported_concerns
            ],
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
                        {"role": "user", "content": str(prompt_payload)},
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
            import json
            parsed = json.loads(content)
            narrative = parsed.get("executive_summary", "")
            gaps = parsed.get("strategic_gaps", [])
            return narrative, gaps

        except (httpx.HTTPError, OSError) as err:
            raise ServiceUnavailableError(f"AuraRouter connection to '{self._url}' failed: {err}") from err

    def recommend_portfolio_tradeoff(
        self,
        comparison: TradeoffProposalComparisonDTO,
    ) -> str:
        """Provide strategic recommendation on portfolio funding trade-off proposals."""
        if not self._url:
            raise ServiceUnavailableError("AuraRouter URL is not configured")

        try:
            resp = self._client.post(
                f"{self._url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a portfolio optimization advisor. Provide a 2-sentence funding recommendation.",
                        },
                        {"role": "user", "content": comparison.model_dump_json()},
                    ],
                },
            )
            if resp.status_code != 200:
                raise ServiceUnavailableError(f"AuraRouter returned HTTP {resp.status_code}: {resp.text}")

            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except (httpx.HTTPError, OSError) as err:
            raise ServiceUnavailableError(f"AuraRouter connection to '{self._url}' failed: {err}") from err
