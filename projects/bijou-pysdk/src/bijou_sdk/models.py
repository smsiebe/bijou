"""Client-side wire models matching the Bijou v2 contracts and OpenAPI specification."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EffortState(str, Enum):
    COMPLETED = "COMPLETED"
    IN_WORK = "IN_WORK"
    BACKLOGGED = "BACKLOGGED"
    PLANNED = "PLANNED"
    DISCOVERY_PENDING = "DISCOVERY_PENDING"
    CANCELLED = "CANCELLED"


class EffortTimingMode(str, Enum):
    EXPLICIT_DATES = "EXPLICIT_DATES"
    DURATION_ONLY = "DURATION_ONLY"
    UNKNOWN = "UNKNOWN"


class ForecastHorizonStatus(str, Enum):
    COMPLETED_HISTORICAL = "COMPLETED_HISTORICAL"
    EXPLICIT_SCHEDULE = "EXPLICIT_SCHEDULE"
    OPEN_ENDED_ACTIVE = "OPEN_ENDED_ACTIVE"
    RELATIVE_TO_DEPENDENCY = "RELATIVE_TO_DEPENDENCY"
    UNSCHEDULED_PLAN = "UNSCHEDULED_PLAN"
    CANCELLED = "CANCELLED"


class InterestKind(str, Enum):
    STRATEGIC_CONCEPT = "STRATEGIC_CONCEPT"
    MISSION_GOAL = "MISSION_GOAL"
    NIPF_PRIORITY = "NIPF_PRIORITY"
    THREAT_VECTOR = "THREAT_VECTOR"
    INTELLIGENCE_GAP = "INTELLIGENCE_GAP"
    CUSTOMER = "CUSTOMER"
    INVESTMENT = "INVESTMENT"
    COUNTRY = "COUNTRY"
    CAPABILITY_AREA = "CAPABILITY_AREA"
    OTHER = "OTHER"


class ConfidenceLevel(str, Enum):
    CONFIRMED = "CONFIRMED"
    ASSESSED = "ASSESSED"
    UNCONFIRMED = "UNCONFIRMED"


class ResourceCategory(str, Enum):
    MONEY = "MONEY"
    STAFF = "STAFF"
    COMPUTE = "COMPUTE"
    MATERIAL = "MATERIAL"
    GENERIC_SUPPORT = "GENERIC_SUPPORT"


class OrgOrgRelationType(str, Enum):
    HIERARCHICAL_PARENT = "HIERARCHICAL_PARENT"
    FORMAL_SUPPORTING = "FORMAL_SUPPORTING"
    COLLABORATIVE_ADJACENT = "COLLABORATIVE_ADJACENT"
    CO_SPONSOR = "CO_SPONSOR"


class OrgInterestStance(str, Enum):
    RESPONSIBLE_OWNER = "RESPONSIBLE_OWNER"
    DIRECT_INVESTOR = "DIRECT_INVESTOR"
    BENEFICIARY = "BENEFICIARY"
    PERCEIVED_GAP = "PERCEIVED_GAP"
    MISSION_ALIGNED = "MISSION_ALIGNED"


class InterestInterestRelationType(str, Enum):
    SPECIALIZES = "SPECIALIZES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    RELATED_TO = "RELATED_TO"


class EffortInterestRelationType(str, Enum):
    DIRECT_SOLUTION = "DIRECT_SOLUTION"
    INDIRECT_ENABLER = "INDIRECT_ENABLER"
    FUNDED_FOR = "FUNDED_FOR"
    PARTIAL_ALIGNMENT = "PARTIAL_ALIGNMENT"


class BlockingMode(str, Enum):
    BLOCKING = "BLOCKING"
    NON_BLOCKING_INFORMS = "NON_BLOCKING_INFORMS"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MITIGATED = "MITIGATED"
    REALIZED = "REALIZED"


class AccessMode(str, Enum):
    GLOBAL_ANALYST = "GLOBAL_ANALYST"
    MANAGED_ORG_OWNER = "MANAGED_ORG_OWNER"


class BijouSdkBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)


class Organization(BijouSdkBaseModel):
    id: str
    name: str
    description: str = ""
    echelon_level: int = 1
    is_managed: bool = False
    tags: list[str] = Field(default_factory=list)


class ResourcePool(BijouSdkBaseModel):
    id: str
    org_id: str
    name: str
    category: ResourceCategory
    capacity: float
    unit: str = "USD"
    skill_tag: str | None = None
    restricted_interest_ids: list[str] = Field(default_factory=list)
    description: str = ""


class Interest(BijouSdkBaseModel):
    id: str
    name: str
    description: str = ""
    interest_kind: InterestKind = InterestKind.STRATEGIC_CONCEPT
    start_date: date | None = None
    end_date: date | None = None


class ResourceRequirement(BijouSdkBaseModel):
    id: str
    category: ResourceCategory
    label: str
    quantity: float = 1.0
    unit: str = "USD"
    required_skill: str | None = None
    estimated_cost_usd: float | None = None
    is_generic: bool = True


class Risk(BijouSdkBaseModel):
    id: str
    effort_id: str
    title: str
    description: str = ""
    severity: RiskSeverity = RiskSeverity.MEDIUM
    likelihood: float = 0.5
    potential_slip_days: int = 0
    is_skill_mismatch_risk: bool = False
    status: RiskStatus = RiskStatus.ACTIVE
    related_requirement_id: str | None = None


class Mitigator(BijouSdkBaseModel):
    id: str
    effort_id: str
    risk_id: str | None = None
    name: str
    description: str = ""
    is_exercised: bool = False
    slip_reduction_days: int = 0
    risk_reduction_factor: float = 0.5
    additional_requirements: list[ResourceRequirement] = Field(default_factory=list)


class Effort(BijouSdkBaseModel):
    id: str
    name: str
    description: str = ""
    state: EffortState = EffortState.PLANNED
    start_date: date | None = None
    end_date: date | None = None
    estimated_duration_days: int | None = None
    resource_requirements: list[ResourceRequirement] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    mitigators: list[Mitigator] = Field(default_factory=list)


class PedigreeEdge(BijouSdkBaseModel):
    id: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.CONFIRMED
    provenance_note: str | None = None
    effective_start: date | None = None
    effective_end: date | None = None


class OrgOrgEdge(PedigreeEdge):
    source_org_id: str
    target_org_id: str
    relation_type: OrgOrgRelationType


class OrgInterestEdge(PedigreeEdge):
    org_id: str
    interest_id: str
    stance: OrgInterestStance = OrgInterestStance.MISSION_ALIGNED
    priority_rank: float = 0.5
    allow_hierarchy_inheritance: bool = True


class InterestInterestEdge(PedigreeEdge):
    parent_interest_id: str
    child_interest_id: str
    relation_type: InterestInterestRelationType = InterestInterestRelationType.SPECIALIZES


class OrgEffortEdge(PedigreeEdge):
    org_id: str
    effort_id: str
    resourcing_type: ResourceCategory = ResourceCategory.GENERIC_SUPPORT
    resource_pool_id: str | None = None
    requirement_id: str | None = None
    allocation_amount: float = 0.0
    allocation_unit: str = "UNITS"
    assigned_skill: str | None = None
    is_generic: bool = True


class EffortInterestEdge(PedigreeEdge):
    effort_id: str
    interest_id: str
    relation_type: EffortInterestRelationType = EffortInterestRelationType.DIRECT_SOLUTION
    impact_weight: float = 1.0


class EffortEffortEdge(PedigreeEdge):
    source_effort_id: str
    target_effort_id: str
    blocking_mode: BlockingMode = BlockingMode.BLOCKING
    dependency_degree: float = 1.0


class ManifestPayload(BijouSdkBaseModel):
    schema_version: str = "2.0.0"
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    organizations: list[Organization] = Field(default_factory=list)
    resource_pools: list[ResourcePool] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    efforts: list[Effort] = Field(default_factory=list)
    org_org_edges: list[OrgOrgEdge] = Field(default_factory=list)
    org_interest_edges: list[OrgInterestEdge] = Field(default_factory=list)
    interest_interest_edges: list[InterestInterestEdge] = Field(default_factory=list)
    org_effort_edges: list[OrgEffortEdge] = Field(default_factory=list)
    effort_interest_edges: list[EffortInterestEdge] = Field(default_factory=list)
    effort_effort_edges: list[EffortEffortEdge] = Field(default_factory=list)


class ForecastedEffortNode(BijouSdkBaseModel):
    effort: Effort
    timing_mode: EffortTimingMode
    horizon_status: ForecastHorizonStatus
    forecast_start: date | None = None
    forecast_end: date | None = None
    relative_offset_days: int | None = None
    blocked_by_effort_ids: list[str] = Field(default_factory=list)
    informing_effort_ids: list[str] = Field(default_factory=list)
    topological_depth: int = 0
    slack_days: int | None = None
    is_spof: bool = False
    funding_org_ids: list[str] = Field(default_factory=list)
    primary_org_id: str | None = None
    aligned_interest_ids: list[str] = Field(default_factory=list)
    indirect_beneficiary_org_ids: list[str] = Field(default_factory=list)
    total_estimated_cost_usd: float = 0.0
    resourcing_coverage_ratio: float = 0.0
    active_risk_count: int = 0
    exercised_mitigator_count: int = 0
    unexercised_mitigator_count: int = 0


class CapabilityTreeView(BijouSdkBaseModel):
    as_of_date: date
    nodes: list[ForecastedEffortNode] = Field(default_factory=list)
    effort_edges: list[EffortEffortEdge] = Field(default_factory=list)
    organizations: list[Organization] = Field(default_factory=list)
    resource_pools: list[ResourcePool] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    org_org_edges: list[OrgOrgEdge] = Field(default_factory=list)
    org_interest_edges: list[OrgInterestEdge] = Field(default_factory=list)
    interest_interest_edges: list[InterestInterestEdge] = Field(default_factory=list)
    org_effort_edges: list[OrgEffortEdge] = Field(default_factory=list)
    effort_interest_edges: list[EffortInterestEdge] = Field(default_factory=list)
    effective_priorities: list[dict[str, Any]] = Field(default_factory=list)


class TriPartiteFlowView(BijouSdkBaseModel):
    as_of_date: date
    capability_tree: CapabilityTreeView
    pool_balances: list[dict[str, Any]] = Field(default_factory=list)
    indirect_benefits: list[dict[str, Any]] = Field(default_factory=list)
    shared_interest_partnerships: list[dict[str, Any]] = Field(default_factory=list)


class BillOfEffortsSimulationResult(BijouSdkBaseModel):
    projected_tree: CapabilityTreeView
    pool_balances: list[dict[str, Any]] = Field(default_factory=list)
    skill_mismatch_warnings: list[dict[str, Any]] = Field(default_factory=list)
    newly_registered_risks: list[Risk] = Field(default_factory=list)
    impacted_effort_ids: list[str] = Field(default_factory=list)
    interest_coverage_deltas: dict[str, float] = Field(default_factory=dict)
    total_cost_delta: float = 0.0
    net_risk_count_delta: int = 0
