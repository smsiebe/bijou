"""Analytical view projection, tech tree, and simulation wire DTOs."""

from datetime import date

from pydantic import Field, model_validator
from typing_extensions import Self

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import (
    CausalMechanismType,
    TechTreeNodeState,
    TechTreeStratificationMode,
)
from bijou.core.contracts.models import EffectDTO, GraphEdgeDTO, ThingDTO
from bijou.core.contracts.telemetry import TelemetryRollupDTO


class ConcernCoverageItemDTO(BijouBaseModel):
    """Coverage of a strategic Concern by Things and Effects."""

    concern_id: str = Field(..., alias="concern_id", description="Concern ID")
    concern_name: str = Field(..., alias="concern_name", description="Concern name")
    owner_org_id: str = Field(..., alias="owner_org_id", description="Owner organization ID")
    priority: float = Field(..., alias="priority", ge=0.0, le=1.0, description="Concern priority")
    coverage_score: float = Field(..., alias="coverage_score", ge=0.0, le=1.0, description="Coverage score")
    contributing_thing_ids: list[str] = Field(default_factory=list, alias="contributing_thing_ids", description="Contributing Thing IDs")
    satisfied_by_effect_ids: list[str] = Field(default_factory=list, alias="satisfied_by_effect_ids", description="Satisfied by Effect IDs")


class PerspectiveBriefingDTO(BijouBaseModel):
    """Executive 1-Slide Multi-Perspective Briefing projection."""

    subject_org_id: str = Field(..., alias="subject_org_id", description="Subject organization ID")
    perspective_org_id: str | None = Field(default=None, alias="perspective_org_id", description="Perspective organization ID")
    include_descendants: bool = Field(default=True, alias="include_descendants", description="Include subordinate organizations")
    as_of_date: date = Field(..., alias="as_of_date", description="Evaluation as-of date")
    owned_things: list[ThingDTO] = Field(default_factory=list, alias="owned_things", description="Owned Things")
    supported_concerns: list[ConcernCoverageItemDTO] = Field(default_factory=list, alias="supported_concerns", description="Supported Concerns")
    cross_org_dependencies: list[GraphEdgeDTO] = Field(default_factory=list, alias="cross_org_dependencies", description="Cross-organization dependencies")
    portfolio_roi_score: float = Field(default=0.0, alias="portfolio_roi_score", description="Portfolio aggregate ROI score")
    total_committed_cost: float = Field(default=0.0, alias="total_committed_cost", ge=0.0, description="Total committed cost")
    executive_summary_narrative: str | None = Field(default=None, alias="executive_summary_narrative", description="Executive narrative synthesized by AuraRouter")
    strategic_gaps: list[str] = Field(default_factory=list, alias="strategic_gaps", description="Strategic blind-spots or gaps")


class TechTreeNodeDTO(BijouBaseModel):
    """Node in the 4X game-style Tech Tree DAG representing a Thing Milestone."""

    node_id: str = Field(..., alias="node_id", description="Unique node ID in {thing_id}:{milestone_id} format")
    thing_id: str = Field(..., alias="thing_id", description="Thing ID")
    milestone_id: str = Field(..., alias="milestone_id", description="Milestone ID")
    title: str = Field(..., alias="title", description="Milestone title")
    thing_name: str = Field(..., alias="thing_name", description="Parent Thing name")
    owner_org_id: str = Field(..., alias="owner_org_id", description="Owner organization ID")
    tier_id: str = Field(..., alias="tier_id", description="Tier identifier")
    tier_order: int = Field(..., alias="tier_order", ge=0, description="Tier column order")
    lane_id: str = Field(..., alias="lane_id", description="Swimlane identifier")
    state: TechTreeNodeState = Field(..., alias="state", description="Tech tree node state")
    target_date: date = Field(..., alias="target_date", description="Target completion date")
    actual_date: date | None = Field(default=None, alias="actual_date", description="Actual completion date")
    cost_estimate: float = Field(default=0.0, alias="cost_estimate", ge=0.0, description="Cost estimate")
    trl: int = Field(..., alias="trl", ge=1, le=9, description="Technology Readiness Level (1-9)")
    unlocked_effect_ids: list[str] = Field(default_factory=list, alias="unlocked_effect_ids", description="Unlocked Effect IDs")
    slack_days: int = Field(default=0, alias="slack_days", description="CPM schedule float/slack in days")
    centrality_score: float = Field(default=0.0, alias="centrality_score", description="Betweenness centrality score")
    is_spof: bool = Field(default=False, alias="is_spof", description="Whether node is a Single Point of Failure choke point")


class TechTreeEdgeDTO(BijouBaseModel):
    """Dependency bus edge connecting nodes in the Tech Tree."""

    edge_id: str = Field(..., alias="edge_id", description="Tech tree edge ID")
    source_node_id: str = Field(..., alias="source_node_id", description="Source node ID")
    target_node_id: str = Field(..., alias="target_node_id", description="Target node ID")
    gate_type: CausalMechanismType = Field(default=CausalMechanismType.ADDITIVE, alias="gate_type", description="Gate mechanism")
    is_satisfied: bool = Field(default=False, alias="is_satisfied", description="Is dependency satisfied")
    is_critical_path: bool = Field(default=False, alias="is_critical_path", description="Is part of critical path")


class TechTreeViewDTO(BijouBaseModel):
    """Complete 4X Game-Style Tech Tree layout projection."""

    as_of_date: date = Field(..., alias="as_of_date", description="Evaluation date")
    stratification_mode: TechTreeStratificationMode = Field(..., alias="stratification_mode", description="Stratification mode")
    tiers: list[dict[str, str | int]] = Field(default_factory=list, alias="tiers", description="Stratification tier definitions")
    lanes: list[dict[str, str]] = Field(default_factory=list, alias="lanes", description="Swimlane definitions")
    nodes: list[TechTreeNodeDTO] = Field(default_factory=list, alias="nodes", description="Tech tree nodes")
    edges: list[TechTreeEdgeDTO] = Field(default_factory=list, alias="edges", description="Tech tree edges")


class SlipSimulationRequestDTO(BijouBaseModel):
    """Request payload to simulate milestone slip or cancellation."""

    simulated_slips: dict[str, int] = Field(
        default_factory=dict,
        alias="simulated_slips",
        description="Mapping of milestone IDs to slip days",
    )
    cancelled_milestone_ids: list[str] = Field(
        default_factory=list,
        alias="cancelled_milestone_ids",
        description="List of milestone IDs cancelled",
    )
    milestone_id: str | None = Field(
        default=None,
        alias="milestone_id",
        description="Legacy single milestone ID to slip",
    )
    slip_days: int | None = Field(
        default=None,
        alias="slip_days",
        ge=1,
        description="Legacy days to slip (minimum 1)",
    )
    simulate_cancellation: bool = Field(
        default=False,
        alias="simulate_cancellation",
        description="Legacy simulate cancellation flag",
    )

    @model_validator(mode="after")
    def _validate_and_sync_slips(self) -> Self:
        for ms_id, days in self.simulated_slips.items():
            if days < 1:
                raise ValueError(f"Slip days for {ms_id} must be at least 1, got {days}")
        if (
            self.milestone_id is not None
            and self.slip_days is not None
            and self.milestone_id not in self.simulated_slips
        ):
            self.simulated_slips[self.milestone_id] = self.slip_days
        if (
            self.milestone_id is not None
            and self.simulate_cancellation
            and self.milestone_id not in self.cancelled_milestone_ids
        ):
            self.cancelled_milestone_ids.append(self.milestone_id)
        return self


class SlipSimulationResponseDTO(BijouBaseModel):
    """Response payload detailing blast radius of a milestone slip."""

    slipped_milestone_id: str = Field(..., alias="slipped_milestone_id", description="Slipped milestone ID")
    slip_days: int = Field(..., alias="slip_days", description="Slip days")
    cancelled: bool = Field(default=False, alias="cancelled", description="Whether cancelled")
    impacted_node_states: dict[str, TechTreeNodeState] = Field(default_factory=dict, alias="impacted_node_states", description="Impacted node states")
    degraded_effect_ids: list[str] = Field(default_factory=list, alias="degraded_effect_ids", description="Degraded effect IDs")
    broken_concern_ids: list[str] = Field(default_factory=list, alias="broken_concern_ids", description="Broken concern IDs")
    roi_delta: float = Field(default=0.0, alias="roi_delta", description="ROI delta")


class TradeoffProposalComparisonDTO(BijouBaseModel):
    """Comparison matrix between proposed funding alternatives."""

    proposed_thing_ids: list[str] = Field(..., alias="proposed_thing_ids", description="Proposed Thing IDs")
    total_cost: float = Field(..., alias="total_cost", ge=0.0, description="Total cost")
    aggregate_roi: float = Field(..., alias="aggregate_roi", description="Aggregate ROI")
    concern_coverage_deltas: dict[str, float] = Field(default_factory=dict, alias="concern_coverage_deltas", description="Coverage deltas by concern")
    unlocked_effect_ids: list[str] = Field(default_factory=list, alias="unlocked_effect_ids", description="Unlocked effect IDs")
    reasoning_recommendation: str | None = Field(default=None, alias="reasoning_recommendation", description="Strategic reasoning recommendation")


class ThingFocalDashboardDTO(BijouBaseModel):
    """2-hop focal ego-network and telemetry dashboard around a single Thing."""

    thing: ThingDTO = Field(..., alias="thing", description="Target focal Thing")
    upstream_dependencies: list[ThingDTO] = Field(default_factory=list, alias="upstream_dependencies", description="Upstream dependencies")
    downstream_dependents: list[ThingDTO] = Field(default_factory=list, alias="downstream_dependents", description="Downstream dependents")
    produced_effects: list[EffectDTO] = Field(default_factory=list, alias="produced_effects", description="Produced effects")
    telemetry_rollups: list[TelemetryRollupDTO] = Field(default_factory=list, alias="telemetry_rollups", description="Telemetry rollups")
    impacted_concerns: list[ConcernCoverageItemDTO] = Field(default_factory=list, alias="impacted_concerns", description="Impacted concerns")
    direct_roi: float = Field(default=0.0, alias="direct_roi", description="Direct ROI score")
