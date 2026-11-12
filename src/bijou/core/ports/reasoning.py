"""Abstract port for AuraRouter strategic LLM reasoning broker."""

from abc import ABC, abstractmethod

from bijou.core.contracts.views import (
    BillOfEffortsSimulationResponseDTO,
    PerspectiveBriefingDTO,
)


class IReasoningBroker(ABC):
    """Abstract port for non-deterministic AI synthesis and strategic gap analysis."""

    @abstractmethod
    def synthesize_executive_briefing(
        self,
        briefing: PerspectiveBriefingDTO,
        org_mission: str,
    ) -> tuple[str, list[str]]:
        """Synthesize an executive narrative summary and identify strategic blind-spots."""

    @abstractmethod
    def recommend_portfolio_tradeoff(
        self,
        simulation: BillOfEffortsSimulationResponseDTO,
    ) -> str:
        """Provide strategic recommendation on simulated Bill of Efforts adjustments."""
