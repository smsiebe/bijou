"""Core graph entity and causal gate DTOs for Bijou."""

from datetime import date
from typing import Self

from pydantic import Field, model_validator

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import (
    AccumulatorPattern,
    CausalMechanismType,
    EffectTier,
    LifecycleStatus,
    MilestoneStatus,
    RelationshipType,
)


class ConcernSatisfactionLinkDTO(BijouBaseModel):
    """Link defining an Effect's contribution to satisfying a Concern."""

    concern_id: str = Field(..., alias="concern_id", description="Target Concern ID")
    weight: float = Field(..., alias="weight", ge=0.0, le=1.0, description="Satisfaction weight")
    confidence: float = Field(default=1.0, alias="confidence", ge=0.0, le=1.0, description="Confidence score")


class OrganizationDTO(BijouBaseModel):
    """Organization echelon node representing a command, agency, or team."""

    id: str = Field(..., alias="id", description="Organization ID")
    name: str = Field(..., alias="name", description="Organization name")
    echelon_level: int = Field(..., alias="echelon_level", ge=0, description="Echelon level")
    mission_statement: str = Field(..., alias="mission_statement", description="Mission statement")
    parent_org_id: str | None = Field(default=None, alias="parent_org_id", description="Parent organization ID")
    peer_org_ids: list[str] = Field(default_factory=list, alias="peer_org_ids", description="Peer organization IDs")
    tags: list[str] = Field(default_factory=list, alias="tags", description="Tags")


class ConcernDTO(BijouBaseModel):
    """Strategic intent, requirement, or mission thread owned by an organization."""

    id: str = Field(..., alias="id", description="Concern ID")
    name: str = Field(..., alias="name", description="Concern name")
    description: str = Field(..., alias="description", description="Concern description")
    owner_org_id: str = Field(..., alias="owner_org_id", description="Owner organization ID")
    parent_concern_id: str | None = Field(default=None, alias="parent_concern_id", description="Parent concern ID")
    priority: float = Field(..., alias="priority", ge=0.0, le=1.0, description="Priority score between 0.0 and 1.0")
    target_metric_sla: float | None = Field(default=None, alias="target_metric_sla", description="Target metric SLA")


class MilestoneDTO(BijouBaseModel):
    """Phased temporal evolution of a Thing unlocking capabilities."""

    id: str = Field(..., alias="id", description="Milestone ID")
    thing_id: str = Field(..., alias="thing_id", description="Parent Thing ID")
    sequence_index: int = Field(..., alias="sequence_index", ge=0, description="Sequence index")
    name: str = Field(..., alias="name", description="Milestone name")
    description: str = Field(..., alias="description", description="Milestone description")
    target_date: date = Field(..., alias="target_date", description="Target completion date")
    actual_date: date | None = Field(default=None, alias="actual_date", description="Actual completion date")
    status: MilestoneStatus = Field(..., alias="status", description="Milestone status")
    cost_delta: float = Field(default=0.0, alias="cost_delta", ge=0.0, description="Cost delta")
    lane: str = Field(..., alias="lane", description="Domain swimlane")
    trl: int = Field(..., alias="trl", ge=1, le=9, description="Technology Readiness Level (1-9)")


class ThingDTO(BijouBaseModel):
    """Deliverable, program, proposal, or software/hardware asset."""

    id: str = Field(..., alias="id", description="Thing ID")
    name: str = Field(..., alias="name", description="Thing name")
    description: str = Field(..., alias="description", description="Thing description")
    lifecycle: LifecycleStatus = Field(..., alias="lifecycle", description="Lifecycle status")
    owner_org_id: str = Field(..., alias="owner_org_id", description="Owner organization ID")
    estimated_cost: float = Field(..., alias="estimated_cost", ge=0.0, description="Estimated total cost")
    risk_factor: float = Field(..., alias="risk_factor", ge=1.0, le=10.0, description="Risk factor (1.0 to 10.0)")
    milestones: list[MilestoneDTO] = Field(default_factory=list, alias="milestones", description="Phased milestones")


class CausalContributorDTO(BijouBaseModel):
    """Contribution from a Thing and optional Milestone to a Causal Gate."""

    thing_id: str = Field(..., alias="thing_id", description="Contributing Thing ID")
    milestone_id: str | None = Field(default=None, alias="milestone_id", description="Required Milestone ID")
    contribution_weight: float = Field(default=1.0, alias="contribution_weight", ge=0.0, le=1.0, description="Contribution weight")


class CausalGateDTO(BijouBaseModel):
    """Gate combining contributions from multiple Things/Milestones."""

    id: str = Field(..., alias="id", description="Causal Gate ID")
    name: str = Field(..., alias="name", description="Gate name")
    mechanism: CausalMechanismType = Field(..., alias="mechanism", description="Causal mechanism type")
    threshold_k: int | None = Field(default=None, alias="threshold_k", ge=1, description="Threshold K for THRESHOLD_K_OF_N")
    contributors: list[CausalContributorDTO] = Field(default_factory=list, alias="contributors", description="List of contributors")

    @model_validator(mode="after")
    def validate_threshold(self) -> Self:
        """Ensure threshold_k is specified when mechanism is THRESHOLD_K_OF_N."""
        if self.mechanism == CausalMechanismType.THRESHOLD_K_OF_N and self.threshold_k is None:
            raise ValueError("threshold_k is required when mechanism is THRESHOLD_K_OF_N")
        return self


class FederationSpecDTO(BijouBaseModel):
    """Specification for querying external federated telemetry endpoints."""

    connector_id: str = Field(..., alias="connector_id", description="Connector ID")
    query_template: str = Field(..., alias="query_template", description="Query template")
    params: dict[str, str | int | float] = Field(default_factory=dict, alias="params", description="Query parameters")
    accumulator: AccumulatorPattern = Field(..., alias="accumulator", description="Accumulator pattern")
    sla_target: float | None = Field(default=None, alias="sla_target", description="SLA target")
    cache_ttl_seconds: int = Field(default=300, alias="cache_ttl_seconds", ge=0, description="Cache TTL in seconds")


class EffectDTO(BijouBaseModel):
    """Observable outcome evaluated against target strategic Concerns."""

    id: str = Field(..., alias="id", description="Effect ID")
    name: str = Field(..., alias="name", description="Effect name")
    description: str = Field(..., alias="description", description="Effect description")
    tier: EffectTier = Field(..., alias="tier", description="Effect tier")
    causal_gate_id: str | None = Field(default=None, alias="causal_gate_id", description="Causal gate ID")
    accumulator: AccumulatorPattern = Field(default=AccumulatorPattern.SUM, alias="accumulator", description="Accumulator pattern")
    observed_value: float | None = Field(default=None, alias="observed_value", description="Observed metric value")
    target_threshold: float | None = Field(default=None, alias="target_threshold", description="Target metric threshold")
    satisfies_concerns: list[ConcernSatisfactionLinkDTO] = Field(default_factory=list, alias="satisfies_concerns", description="Concerns satisfied")
    federation_spec: FederationSpecDTO | None = Field(default=None, alias="federation_spec", description="Federation specification if virtual")


class GraphEdgeDTO(BijouBaseModel):
    """Typed relationship edge between nodes in the Bijou graph."""

    id: str = Field(..., alias="id", description="Edge ID")
    source_id: str = Field(..., alias="source_id", description="Source entity ID")
    target_id: str = Field(..., alias="target_id", description="Target entity ID")
    relationship: RelationshipType = Field(..., alias="relationship", description="Relationship type")
    weight: float = Field(default=1.0, alias="weight", ge=0.0, le=1.0, description="Edge weight")
    source_milestone_id: str | None = Field(default=None, alias="source_milestone_id", description="Source milestone anchor ID")
    target_milestone_id: str | None = Field(default=None, alias="target_milestone_id", description="Target milestone anchor ID")
    effective_start: date | None = Field(default=None, alias="effective_start", description="Effective start date")
    effective_end: date | None = Field(default=None, alias="effective_end", description="Effective end date")
