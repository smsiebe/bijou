"""Abstract port for Bijou v2 graph projection, forecasting, and Bill of Efforts simulation engine."""

from abc import ABC, abstractmethod
from datetime import date

from bijou.core.contracts.enums import AccessMode, ConfidenceLevel
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.telemetry import TelemetryRollupDTO
from bijou.core.contracts.views import (
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    DiagnosticReportDTO,
    EffortFocalDashboardDTO,
    InterestFocalDashboardDTO,
    OrgFocalDashboardDTO,
    PerspectiveBriefingDTO,
    TriPartiteFlowViewDTO,
)


class IGraphProjectionEngine(ABC):
    """Abstract port for deterministic graph projection, traversal, and simulation analysis.

    Concurrency Model: Thread-safe via reentrant read-write lock (RLock); snapshot reads
    execute concurrently; rebuild_projection acquires exclusive write lock.
    """

    @abstractmethod
    def rebuild_projection(self, manifest: BijouManifestDTO) -> None:
        """Rebuild the in-memory graph projection from a complete manifest snapshot."""

    @abstractmethod
    def validate_dag_acyclic(self) -> dict[str, list[list[str]]]:
        """Verify Effort and Interest DAGs are acyclic, returning detected cycles by graph."""

    @abstractmethod
    def build_capability_tree_view(
        self,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
        org_filter: str | None = None,
    ) -> CapabilityTreeViewDTO:
        """Construct the stateful capability progression tree projection (View A)."""

    @abstractmethod
    def build_tripartite_flow_view(
        self,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
    ) -> TriPartiteFlowViewDTO:
        """Construct the Orgs <-> Efforts <-> Interests Tri-Partite flow projection (View B)."""

    @abstractmethod
    def simulate_bill_of_efforts(
        self,
        request: BillOfEffortsSimulationRequestDTO,
        as_of_date: date,
    ) -> BillOfEffortsSimulationResponseDTO:
        """Evaluate transient Mitigator toggles, ResourcePool assignments, and slip shocks (View C)."""

    @abstractmethod
    def build_effort_focal_dashboard(
        self,
        effort_id: str,
        as_of_date: date,
        telemetry_rollups: list[TelemetryRollupDTO],
    ) -> EffortFocalDashboardDTO:
        """Generate a deep focal dashboard for a single Effort."""

    @abstractmethod
    def build_org_focal_dashboard(
        self,
        org_id: str,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
    ) -> OrgFocalDashboardDTO:
        """Generate a deep focal dashboard for an Organization."""

    @abstractmethod
    def build_interest_focal_dashboard(
        self,
        interest_id: str,
        as_of_date: date,
    ) -> InterestFocalDashboardDTO:
        """Generate a deep focal dashboard for an Interest and its taxonomy lineage."""

    @abstractmethod
    def build_perspective_briefing(
        self,
        subject_org_id: str,
        active_access_mode: AccessMode,
        include_hierarchy_inheritance: bool,
        as_of_date: date,
    ) -> PerspectiveBriefingDTO:
        """Assemble an executive Multi-Perspective 1-Slide Briefing projection."""

    @abstractmethod
    def validate_manifest_diagnostics(
        self,
        manifest: BijouManifestDTO | None = None,
    ) -> DiagnosticReportDTO:
        """Perform topological, Color-of-Money, pool balance, and skill risk diagnostics."""
