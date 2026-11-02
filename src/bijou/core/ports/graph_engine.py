"""Abstract port for in-memory graph projection, tech-tree layout, and ROI engine."""

from abc import ABC, abstractmethod
from datetime import date

from bijou.core.contracts.enums import TechTreeStratificationMode
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.telemetry import TelemetryRollupDTO
from bijou.core.contracts.views import (
    PerspectiveBriefingDTO,
    SlipSimulationRequestDTO,
    SlipSimulationResponseDTO,
    TechTreeViewDTO,
    ThingFocalDashboardDTO,
    TradeoffProposalComparisonDTO,
)


class IGraphProjectionEngine(ABC):
    """Abstract port for deterministic graph projection and mathematical analysis.

    Concurrency Model: Thread-safe via reentrant read-write lock (RLock); snapshot reads
    execute concurrently; rebuild_projection acquires exclusive write lock.
    """

    @abstractmethod
    def rebuild_projection(self, manifest: BijouManifestDTO) -> None:
        """Rebuild the in-memory graph projection from a complete manifest snapshot."""

    @abstractmethod
    def validate_dag_acyclic(self) -> list[list[str]]:
        """Verify the milestone dependency graph is acyclic and return any detected cycles."""

    @abstractmethod
    def calculate_thing_roi(self, thing_id: str, as_of_date: date) -> float:
        """Calculate the direct return-on-investment score for a given Thing."""

    @abstractmethod
    def build_perspective_briefing(
        self,
        subject_org_id: str,
        perspective_org_id: str | None,
        include_descendants: bool,
        as_of_date: date,
    ) -> PerspectiveBriefingDTO:
        """Assemble an executive Multi-Perspective 1-Slide Briefing projection."""

    @abstractmethod
    def build_tech_tree_view(
        self,
        as_of_date: date,
        stratification_mode: TechTreeStratificationMode,
        org_filter: str | None = None,
    ) -> TechTreeViewDTO:
        """Construct the stratified 4X Game-Style Tech Tree layout."""

    @abstractmethod
    def simulate_milestone_slip(
        self,
        request: SlipSimulationRequestDTO,
        as_of_date: date,
    ) -> SlipSimulationResponseDTO:
        """Simulate milestone slip or cancellation and calculate blast radius."""

    @abstractmethod
    def evaluate_tradeoff_matrix(
        self,
        proposed_thing_ids: list[str],
        as_of_date: date,
    ) -> TradeoffProposalComparisonDTO:
        """Evaluate portfolio tradeoff between competing subsets of Things."""

    @abstractmethod
    def build_thing_focal_dashboard(
        self,
        thing_id: str,
        as_of_date: date,
        telemetry_rollups: list[TelemetryRollupDTO],
    ) -> ThingFocalDashboardDTO:
        """Generate a 2-hop focal dashboard centered on a single Thing."""
