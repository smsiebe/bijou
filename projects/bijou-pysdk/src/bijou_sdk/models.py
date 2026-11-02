"""Client-side wire models matching the Bijou contracts and OpenAPI specification."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LifecycleStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    DELIVERED = "DELIVERED"
    DEPRECATED = "DEPRECATED"
    CANCELLED = "CANCELLED"


class MilestoneStatus(str, Enum):
    ESTIMATED = "ESTIMATED"
    COMMITTED = "COMMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    SLIPPED = "SLIPPED"
    BLOCKED = "BLOCKED"


class CausalMechanismType(str, Enum):
    ADDITIVE = "ADDITIVE"
    COMBINATORIAL_AND = "COMBINATORIAL_AND"
    THRESHOLD_K_OF_N = "THRESHOLD_K_OF_N"


class EffectTier(str, Enum):
    TIER_1_STRATEGIC = "TIER_1_STRATEGIC"
    TIER_2_OPERATIONAL = "TIER_2_OPERATIONAL"
    FEDERATED_VIRTUAL = "FEDERATED_VIRTUAL"


class TechTreeNodeState(str, Enum):
    ACHIEVED = "ACHIEVED"
    ACTIVE = "ACTIVE"
    UNLOCKED_READY = "UNLOCKED_READY"
    LOCKED = "LOCKED"
    BLOCKED = "BLOCKED"


class TechTreeStratificationMode(str, Enum):
    TRL_TIERS = "TRL_TIERS"
    FISCAL_ERA = "FISCAL_ERA"
    TOPOLOGICAL_DEPTH = "TOPOLOGICAL_DEPTH"


class BijouSdkBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )


class Organization(BijouSdkBaseModel):
    id: str
    name: str
    echelon_level: int
    mission_statement: str
    parent_org_id: str | None = None
    peer_org_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Concern(BijouSdkBaseModel):
    id: str
    name: str
    description: str
    owner_org_id: str
    parent_concern_id: str | None = None
    priority: float
    target_metric_sla: float | None = None


class Milestone(BijouSdkBaseModel):
    id: str
    thing_id: str
    sequence_index: int
    name: str
    description: str
    target_date: date
    actual_date: date | None = None
    status: MilestoneStatus
    cost_delta: float = 0.0
    lane: str
    trl: int


class Thing(BijouSdkBaseModel):
    id: str
    name: str
    description: str
    lifecycle: LifecycleStatus
    owner_org_id: str
    estimated_cost: float
    risk_factor: float
    milestones: list[Milestone] = Field(default_factory=list)


class AccumulatorPattern(str, Enum):
    SUM = "SUM"
    SLA_THRESHOLD = "SLA_THRESHOLD"
    CASCADE_DEPTH = "CASCADE_DEPTH"
    YIELD_RATIO = "YIELD_RATIO"


class RelationshipType(str, Enum):
    PARENT_OF = "PARENT_OF"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    PEER_OF = "PEER_OF"
    SUB_CONCERN_OF = "SUB_CONCERN_OF"
    OWNS = "OWNS"
    SUPPORTS = "SUPPORTS"
    IMPACTS = "IMPACTS"
    SATISFIES = "SATISFIES"
    DEPENDS_ON = "DEPENDS_ON"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    REPLACES = "REPLACES"


class ConcernSatisfactionLink(BijouSdkBaseModel):
    concern_id: str
    weight: float = 1.0


class FederationSpec(BijouSdkBaseModel):
    connector_id: str
    query_template: str
    params: dict[str, str | int | float] = Field(default_factory=dict)
    accumulator: AccumulatorPattern
    sla_target: float | None = None
    cache_ttl_seconds: int = 300


class CausalContributor(BijouSdkBaseModel):
    thing_id: str
    milestone_id: str | None = None
    contribution_weight: float = 1.0


class CausalGate(BijouSdkBaseModel):
    id: str
    name: str
    mechanism: CausalMechanismType
    threshold_k: int | None = None
    contributors: list[CausalContributor] = Field(default_factory=list)


class Effect(BijouSdkBaseModel):
    id: str
    name: str
    description: str
    tier: EffectTier
    causal_gate_id: str | None = None
    accumulator: AccumulatorPattern = AccumulatorPattern.SUM
    observed_value: float | None = None
    target_threshold: float | None = None
    satisfies_concerns: list[ConcernSatisfactionLink] = Field(default_factory=list)
    federation_spec: FederationSpec | None = None


class GraphEdge(BijouSdkBaseModel):
    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    weight: float = 1.0
    source_milestone_id: str | None = None
    target_milestone_id: str | None = None
    effective_start: date | None = None
    effective_end: date | None = None


class ManifestPayload(BijouSdkBaseModel):
    schema_version: str = "1.0.0"
    exported_at: datetime
    organizations: list[Organization] = Field(default_factory=list)
    concerns: list[Concern] = Field(default_factory=list)
    things: list[Thing] = Field(default_factory=list)
    causal_gates: list[CausalGate] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class TechTreeNode(BijouSdkBaseModel):
    node_id: str
    thing_id: str
    milestone_id: str
    title: str
    thing_name: str
    owner_org_id: str
    tier_id: str
    tier_order: int
    lane_id: str
    state: TechTreeNodeState
    target_date: date
    actual_date: date | None = None
    cost_estimate: float
    trl: int
    unlocked_effect_ids: list[str] = Field(default_factory=list)
    slack_days: int = 0
    centrality_score: float = 0.0
    is_spof: bool = False


class TechTreeEdge(BijouSdkBaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    gate_type: CausalMechanismType
    is_satisfied: bool
    is_critical_path: bool


class TechTreeView(BijouSdkBaseModel):
    as_of_date: date
    stratification_mode: TechTreeStratificationMode
    tiers: list[dict[str, Any]] = Field(default_factory=list)
    lanes: list[dict[str, Any]] = Field(default_factory=list)
    nodes: list[TechTreeNode] = Field(default_factory=list)
    edges: list[TechTreeEdge] = Field(default_factory=list)


class SlipSimulationRequest(BijouSdkBaseModel):
    simulated_slips: dict[str, int] = Field(default_factory=dict)
    cancelled_milestone_ids: list[str] = Field(default_factory=list)
    milestone_id: str | None = None
    slip_days: int | None = None
    simulate_cancellation: bool = False


class SlipSimulationResult(BijouSdkBaseModel):
    slipped_milestone_id: str
    slip_days: int
    cancelled: bool
    impacted_node_states: dict[str, TechTreeNodeState] = Field(default_factory=dict)
    degraded_effect_ids: list[str] = Field(default_factory=list)
    broken_concern_ids: list[str] = Field(default_factory=list)
    roi_delta: float = 0.0


class PerspectiveBriefing(BijouSdkBaseModel):
    subject_org_id: str
    perspective_org_id: str | None = None
    include_descendants: bool = True
    as_of_date: date
    owned_things: list[Thing] = Field(default_factory=list)
    supported_concerns: list[dict[str, Any]] = Field(default_factory=list)
    cross_org_dependencies: list[GraphEdge] = Field(default_factory=list)
    portfolio_roi_score: float = 0.0
    total_committed_cost: float = 0.0
    executive_summary_narrative: str | None = None
    strategic_gaps: list[str] = Field(default_factory=list)


class ThingFocalDashboard(BijouSdkBaseModel):
    thing: Thing
    upstream_dependencies: list[Thing] = Field(default_factory=list)
    downstream_dependents: list[Thing] = Field(default_factory=list)
    produced_effects: list[Effect] = Field(default_factory=list)
    telemetry_rollups: list[dict[str, Any]] = Field(default_factory=list)
    impacted_concerns: list[dict[str, Any]] = Field(default_factory=list)
    direct_roi: float = 0.0


class TradeoffProposalComparison(BijouSdkBaseModel):
    proposed_thing_ids: list[str] = Field(default_factory=list)
    total_cost: float = 0.0
    aggregate_roi: float = 0.0
    concern_coverage_deltas: dict[str, float] = Field(default_factory=dict)
    unlocked_effect_ids: list[str] = Field(default_factory=list)
    reasoning_recommendation: str | None = None


class DecisionLogEntry(BijouSdkBaseModel):
    id: str
    target_milestone_id: str
    author: str
    justification: str
    timestamp: datetime


class ParetoFrontier(BijouSdkBaseModel):
    budget_ceiling: float
    optimal_portfolios: list[TradeoffProposalComparison] = Field(default_factory=list)


class DiagnosticReport(BijouSdkBaseModel):
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    cycles_detected: list[list[str]] = Field(default_factory=list)

