"""Abstract repository port for graph entity storage."""

from abc import ABC, abstractmethod

from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    CausalGateDTO,
    ConcernDTO,
    EffectDTO,
    GraphEdgeDTO,
    OrganizationDTO,
    ThingDTO,
)


class IGraphRepository(ABC):
    """Abstract port for ACID relational graph entity storage.

    Concurrency Model: Thread-safe ACID transactions; write operations acquire exclusive
    transaction scope; read operations return immutable DTO snapshots.
    """

    @abstractmethod
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        """Upsert an Organization."""

    @abstractmethod
    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        """Retrieve an Organization by ID."""

    @abstractmethod
    def list_organizations(self) -> list[OrganizationDTO]:
        """List all Organizations."""

    @abstractmethod
    def upsert_concern(self, concern: ConcernDTO) -> ConcernDTO:
        """Upsert a Concern."""

    @abstractmethod
    def get_concern(self, concern_id: str) -> ConcernDTO | None:
        """Retrieve a Concern by ID."""

    @abstractmethod
    def list_concerns(self) -> list[ConcernDTO]:
        """List all Concerns."""

    @abstractmethod
    def upsert_thing(self, thing: ThingDTO) -> ThingDTO:
        """Upsert a Thing and its Milestones."""

    @abstractmethod
    def get_thing(self, thing_id: str) -> ThingDTO | None:
        """Retrieve a Thing by ID with its Milestones."""

    @abstractmethod
    def list_things(self) -> list[ThingDTO]:
        """List all Things."""

    @abstractmethod
    def upsert_causal_gate(self, gate: CausalGateDTO) -> CausalGateDTO:
        """Upsert a Causal Gate."""

    @abstractmethod
    def get_causal_gate(self, gate_id: str) -> CausalGateDTO | None:
        """Retrieve a Causal Gate by ID."""

    @abstractmethod
    def list_causal_gates(self) -> list[CausalGateDTO]:
        """List all Causal Gates."""

    @abstractmethod
    def upsert_effect(self, effect: EffectDTO) -> EffectDTO:
        """Upsert an Effect."""

    @abstractmethod
    def get_effect(self, effect_id: str) -> EffectDTO | None:
        """Retrieve an Effect by ID."""

    @abstractmethod
    def list_effects(self) -> list[EffectDTO]:
        """List all Effects."""

    @abstractmethod
    def upsert_edge(self, edge: GraphEdgeDTO) -> GraphEdgeDTO:
        """Upsert a Graph Edge."""

    @abstractmethod
    def get_edge(self, edge_id: str) -> GraphEdgeDTO | None:
        """Retrieve a Graph Edge by ID."""

    @abstractmethod
    def list_edges(self) -> list[GraphEdgeDTO]:
        """List all Graph Edges."""

    @abstractmethod
    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete an entity by type and identifier."""

    @abstractmethod
    def export_manifest(self) -> BijouManifestDTO:
        """Export current database contents as a point-in-time BijouManifestDTO."""

    @abstractmethod
    def import_manifest(self, manifest: BijouManifestDTO, replace_all: bool = False) -> dict[str, int]:
        """Import manifest entities, atomically replacing all existing entities if requested."""
