"""Abstract repository port for Bijou v2 graph storage."""

from abc import ABC, abstractmethod

from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    DecisionLogEntryDTO,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    InterestInterestEdgeDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    OrganizationDTO,
    ResourcePoolDTO,
)


class IGraphRepository(ABC):
    """Abstract port for ACID relational graph entity and relationship storage.

    Concurrency Model: Thread-safe ACID transactions; write operations acquire exclusive
    transaction scope; read operations return immutable DTO snapshots.
    """

    # --- Organizations ---
    @abstractmethod
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        """Upsert an Organization."""

    @abstractmethod
    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        """Retrieve an Organization by ID."""

    @abstractmethod
    def list_organizations(self) -> list[OrganizationDTO]:
        """List all Organizations."""

    # --- Resource Pools ---
    @abstractmethod
    def upsert_resource_pool(self, pool: ResourcePoolDTO) -> ResourcePoolDTO:
        """Upsert a ResourcePool."""

    @abstractmethod
    def get_resource_pool(self, pool_id: str) -> ResourcePoolDTO | None:
        """Retrieve a ResourcePool by ID."""

    @abstractmethod
    def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePoolDTO]:
        """List ResourcePools, optionally filtered by Organization ID."""

    # --- Interests ---
    @abstractmethod
    def upsert_interest(self, interest: InterestDTO) -> InterestDTO:
        """Upsert an Interest."""

    @abstractmethod
    def get_interest(self, interest_id: str) -> InterestDTO | None:
        """Retrieve an Interest by ID."""

    @abstractmethod
    def list_interests(self) -> list[InterestDTO]:
        """List all Interests."""

    # --- Efforts (with Requirements, Risks, Mitigators) ---
    @abstractmethod
    def upsert_effort(self, effort: EffortDTO) -> EffortDTO:
        """Upsert an Effort with its requirements, risks, and mitigators."""

    @abstractmethod
    def get_effort(self, effort_id: str) -> EffortDTO | None:
        """Retrieve an Effort by ID."""

    @abstractmethod
    def list_efforts(self) -> list[EffortDTO]:
        """List all Efforts."""

    # --- Typed Relationship Edges ---
    @abstractmethod
    def upsert_org_org_edge(self, edge: OrgOrgEdgeDTO) -> OrgOrgEdgeDTO:
        """Upsert an Org-to-Org edge."""

    @abstractmethod
    def upsert_org_interest_edge(self, edge: OrgInterestEdgeDTO) -> OrgInterestEdgeDTO:
        """Upsert an Org-to-Interest edge."""

    @abstractmethod
    def upsert_interest_interest_edge(self, edge: InterestInterestEdgeDTO) -> InterestInterestEdgeDTO:
        """Upsert an Interest-to-Interest edge."""

    @abstractmethod
    def upsert_org_effort_edge(self, edge: OrgEffortEdgeDTO) -> OrgEffortEdgeDTO:
        """Upsert an Org-to-Effort resourcing edge."""

    @abstractmethod
    def upsert_effort_interest_edge(self, edge: EffortInterestEdgeDTO) -> EffortInterestEdgeDTO:
        """Upsert an Effort-to-Interest alignment edge."""

    @abstractmethod
    def upsert_effort_effort_edge(self, edge: EffortEffortEdgeDTO) -> EffortEffortEdgeDTO:
        """Upsert an Effort-to-Effort causal dependency edge."""

    # --- Deletion ---
    @abstractmethod
    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete an entity or typed edge by category and identifier."""

    # --- Manifest Interchange ---
    @abstractmethod
    def export_manifest(self) -> BijouManifestDTO:
        """Export current database contents as a point-in-time BijouManifestDTO."""

    @abstractmethod
    def import_manifest(self, manifest: BijouManifestDTO, replace_all: bool = False) -> dict[str, int]:
        """Import manifest entities and edges atomically."""

    # --- Decision Provenance Ledger ---
    @abstractmethod
    def upsert_decision_log(self, entry: DecisionLogEntryDTO) -> DecisionLogEntryDTO:
        """Upsert a decision log entry."""

    @abstractmethod
    def list_decision_logs(self, target_effort_id: str | None = None) -> list[DecisionLogEntryDTO]:
        """List decision log entries, optionally filtered by Effort ID."""
