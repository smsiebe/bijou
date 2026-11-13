"""Analytical view projection, forecasting, Tri-Partite flow, and Bill of Efforts simulation DTOs."""

from datetime import date

from pydantic import Field

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import (
    AccessMode,
    BlockingMode,
    ConfidenceLevel,
    EffortState,
    EffortTimingMode,
    ForecastHorizonStatus,
)
from bijou.core.contracts.models import (
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    InterestInterestEdgeDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    ResourceCategory,
    ResourcePoolDTO,
    RiskDTO,
)
from bijou.core.contracts.telemetry import TelemetryRollupDTO


class ForecastedEffortNodeDTO(BijouBaseModel):
    """Forecasted Effort node inside the Capability Progression Tree."""

    effort: EffortDTO = Field(..., alias="effort", description="Core Effort entity")
    timing_mode: EffortTimingMode = Field(..., alias="timing_mode", description="Timing certainty mode")
    horizon_status: ForecastHorizonStatus = Field(
        ..., alias="horizon_status", description="Forecast horizon resolution status"
    )
    forecast_start: date | None = Field(
        default=None, alias="forecast_start", description="Resolved calendar start date if known"
    )
    forecast_end: date | None = Field(
        default=None, alias="forecast_end", description="Resolved calendar end date if known"
    )
    relative_offset_days: int | None = Field(
        default=None,
        alias="relative_offset_days",
        description="Relative duration offset days beyond upstream unknown gates",
    )
    blocked_by_effort_ids: list[str] = Field(
        default_factory=list,
        alias="blocked_by_effort_ids",
        description="Upstream blocking Effort IDs holding unknown or open-ended timing",
    )
    informing_effort_ids: list[str] = Field(
        default_factory=list,
        alias="informing_effort_ids",
        description="Non-blocking upstream informing Effort IDs",
    )
    topological_depth: int = Field(default=0, alias="topological_depth", ge=0, description="DAG depth layer")
    slack_days: int | None = Field(
        default=None, alias="slack_days", description="Schedule float/slack if calendar-anchored"
    )
    is_spof: bool = Field(
        default=False, alias="is_spof", description="True if Effort is a critical bottleneck / single point of failure"
    )
    funding_org_ids: list[str] = Field(
        default_factory=list, alias="funding_org_ids", description="Directly resourcing Organizations"
    )
    primary_org_id: str | None = Field(
        default=None, alias="primary_org_id", description="Primary lead resourcing Organization ID"
    )
    aligned_interest_ids: list[str] = Field(
        default_factory=list, alias="aligned_interest_ids", description="Directly aligned Interest IDs"
    )
    indirect_beneficiary_org_ids: list[str] = Field(
        default_factory=list,
        alias="indirect_beneficiary_org_ids",
        description="Organizations benefiting via shared Interests without direct Effort resourcing",
    )
    total_estimated_cost_usd: float = Field(
        default=0.0, alias="total_estimated_cost_usd", ge=0.0, description="Total estimated monetary need"
    )
    resourcing_coverage_ratio: float = Field(
        default=0.0, alias="resourcing_coverage_ratio", ge=0.0, le=1.0, description="Fraction of requirements funded"
    )
    active_risk_count: int = Field(default=0, alias="active_risk_count", ge=0)
    exercised_mitigator_count: int = Field(default=0, alias="exercised_mitigator_count", ge=0)
    unexercised_mitigator_count: int = Field(default=0, alias="unexercised_mitigator_count", ge=0)


class IndirectBenefitPathDTO(BijouBaseModel):
    """Represents an Organization indirectly benefiting from an Effort via a shared Interest."""

    beneficiary_org_id: str = Field(..., alias="beneficiary_org_id", description="Indirect beneficiary Organization ID")
    via_interest_id: str = Field(..., alias="via_interest_id", description="Shared Interest ID")
    effort_id: str = Field(..., alias="effort_id", description="Effort ID servicing that Interest")
    resourcing_org_ids: list[str] = Field(
        default_factory=list, alias="resourcing_org_ids", description="Organizations directly funding the Effort"
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.ASSESSED, alias="confidence", description="Combined pedigree certainty"
    )


class SharedInterestPartnershipDTO(BijouBaseModel):
    """Discovered potential or active partnership between two Orgs sharing an Interest or lineage."""

    org_a_id: str = Field(..., alias="org_a_id")
    org_b_id: str = Field(..., alias="org_b_id")
    shared_interest_ids: list[str] = Field(default_factory=list, alias="shared_interest_ids")
    has_existing_org_link: bool = Field(default=False, alias="has_existing_org_link")
    combined_priority_score: float = Field(default=0.0, alias="combined_priority_score")


class DynamicOrgInterestPriorityDTO(BijouBaseModel):
    """Optional computed Org-Interest priority including hierarchical inheritance."""

    org_id: str = Field(..., alias="org_id")
    interest_id: str = Field(..., alias="interest_id")
    direct_priority: float | None = Field(default=None, alias="direct_priority")
    effective_priority: float = Field(..., alias="effective_priority")
    inherited_from_org_id: str | None = Field(default=None, alias="inherited_from_org_id")


class ResourcePoolBalanceDTO(BijouBaseModel):
    """Resource pool capacity, current commitment, remaining balance, and Interest eligibility."""

    pool: ResourcePoolDTO = Field(..., alias="pool")
    allocated_amount: float = Field(default=0.0, alias="allocated_amount", ge=0.0)
    remaining_amount: float = Field(default=0.0, alias="remaining_amount")
    eligible_interest_ids: list[str] = Field(
        default_factory=list,
        alias="eligible_interest_ids",
        description="Direct restricted interests plus all descendants in Interest DAG",
    )
    color_of_money_violations: list[str] = Field(
        default_factory=list,
        alias="color_of_money_violations",
        description="Violations if pool funds an Effort lacking an eligible Interest",
    )


class SkillMismatchWarningDTO(BijouBaseModel):
    """Warning emitted when a staff/compute assignment skill mismatches the requirement."""

    effort_id: str = Field(..., alias="effort_id")
    requirement_id: str | None = Field(default=None, alias="requirement_id")
    required_skill: str = Field(..., alias="required_skill")
    assigned_skill: str = Field(..., alias="assigned_skill")
    message: str = Field(..., alias="message")
    suggested_slip_penalty_days: int = Field(default=30, alias="suggested_slip_penalty_days", ge=0)
    generated_risk: RiskDTO = Field(..., alias="generated_risk")


class CapabilityTreeViewDTO(BijouBaseModel):
    """Primary Canvas View A & Base Graph: Stateful Capability Progression Tree + Pedigree Layers."""

    as_of_date: date = Field(..., alias="as_of_date")
    nodes: list[ForecastedEffortNodeDTO] = Field(default_factory=list, alias="nodes")
    effort_edges: list[EffortEffortEdgeDTO] = Field(default_factory=list, alias="effort_edges")
    organizations: list[OrganizationDTO] = Field(default_factory=list, alias="organizations")
    resource_pools: list[ResourcePoolDTO] = Field(default_factory=list, alias="resource_pools")
    interests: list[InterestDTO] = Field(default_factory=list, alias="interests")
    org_org_edges: list[OrgOrgEdgeDTO] = Field(default_factory=list, alias="org_org_edges")
    org_interest_edges: list[OrgInterestEdgeDTO] = Field(default_factory=list, alias="org_interest_edges")
    interest_interest_edges: list[InterestInterestEdgeDTO] = Field(
        default_factory=list, alias="interest_interest_edges"
    )
    org_effort_edges: list[OrgEffortEdgeDTO] = Field(default_factory=list, alias="org_effort_edges")
    effort_interest_edges: list[EffortInterestEdgeDTO] = Field(
        default_factory=list, alias="effort_interest_edges"
    )
    effective_priorities: list[DynamicOrgInterestPriorityDTO] = Field(
        default_factory=list, alias="effective_priorities"
    )


class TriPartiteFlowViewDTO(BijouBaseModel):
    """Primary Canvas View B: Tri-Partite Architectural Flow (Orgs <-> Efforts <-> Interests)."""

    as_of_date: date = Field(..., alias="as_of_date")
    capability_tree: CapabilityTreeViewDTO = Field(..., alias="capability_tree")
    pool_balances: list[ResourcePoolBalanceDTO] = Field(default_factory=list, alias="pool_balances")
    indirect_benefits: list[IndirectBenefitPathDTO] = Field(default_factory=list, alias="indirect_benefits")
    shared_interest_partnerships: list[SharedInterestPartnershipDTO] = Field(
        default_factory=list, alias="shared_interest_partnerships"
    )


class SimulatedPoolAllocationDTO(BijouBaseModel):
    """Transient resource allocation action in the Bill of Efforts sandbox."""

    org_id: str = Field(..., alias="org_id")
    pool_id: str | None = Field(default=None, alias="pool_id")
    effort_id: str = Field(..., alias="effort_id")
    requirement_id: str | None = Field(default=None, alias="requirement_id")
    resourcing_type: ResourceCategory = Field(default=ResourceCategory.MONEY, alias="resourcing_type")
    amount: float = Field(default=0.0, alias="amount", ge=0.0)
    unit: str = Field(default="USD", alias="unit")
    assigned_skill: str | None = Field(default=None, alias="assigned_skill")
    is_generic: bool = Field(default=False, alias="is_generic")
    human_slip_penalty_days: int | None = Field(
        default=None,
        alias="human_slip_penalty_days",
        ge=0,
        description="Optional operator-chosen slip penalty when mismatch risk occurs",
    )


class BillOfEffortsSimulationRequestDTO(BijouBaseModel):
    """Request payload for View C / Bill of Efforts transient portfolio simulation."""

    toggle_mitigators: dict[str, bool] = Field(
        default_factory=dict,
        alias="toggle_mitigators",
        description="Map of mitigator_id -> exercised boolean state",
    )
    add_allocations: list[SimulatedPoolAllocationDTO] = Field(
        default_factory=list,
        alias="add_allocations",
        description="Transient new or modified resource allocations",
    )
    remove_edge_ids: list[str] = Field(
        default_factory=list,
        alias="remove_edge_ids",
        description="Existing OrgEffortEdge IDs temporarily removed/reallocated",
    )
    effort_slips: dict[str, int] = Field(
        default_factory=dict,
        alias="effort_slips",
        description="Direct slip shocks applied to Effort IDs (days)",
    )
    cancelled_effort_ids: list[str] = Field(
        default_factory=list,
        alias="cancelled_effort_ids",
        description="Efforts temporarily cancelled in scenario",
    )


class BillOfEffortsSimulationResponseDTO(BijouBaseModel):
    """Live analytical response for Bill of Efforts scenario modeling."""

    projected_tree: CapabilityTreeViewDTO = Field(..., alias="projected_tree")
    pool_balances: list[ResourcePoolBalanceDTO] = Field(default_factory=list, alias="pool_balances")
    skill_mismatch_warnings: list[SkillMismatchWarningDTO] = Field(
        default_factory=list, alias="skill_mismatch_warnings"
    )
    newly_registered_risks: list[RiskDTO] = Field(default_factory=list, alias="newly_registered_risks")
    impacted_effort_ids: list[str] = Field(default_factory=list, alias="impacted_effort_ids")
    interest_coverage_deltas: dict[str, float] = Field(
        default_factory=dict, alias="interest_coverage_deltas"
    )
    total_cost_delta: float = Field(default=0.0, alias="total_cost_delta")
    net_risk_count_delta: int = Field(default=0, alias="net_risk_count_delta")


class EffortFocalDashboardDTO(BijouBaseModel):
    """Deep inspection payload for a single Effort (Puck HUD & Focal View)."""

    forecast: ForecastedEffortNodeDTO = Field(..., alias="forecast")
    upstream_dependencies: list[EffortDTO] = Field(default_factory=list, alias="upstream_dependencies")
    downstream_dependents: list[EffortDTO] = Field(default_factory=list, alias="downstream_dependents")
    resourcing_edges: list[OrgEffortEdgeDTO] = Field(default_factory=list, alias="resourcing_edges")
    aligned_interests: list[InterestDTO] = Field(default_factory=list, alias="aligned_interests")
    ancestor_interest_categories: list[InterestDTO] = Field(
        default_factory=list, alias="ancestor_interest_categories"
    )
    indirect_beneficiaries: list[IndirectBenefitPathDTO] = Field(
        default_factory=list, alias="indirect_beneficiaries"
    )
    telemetry_rollups: list[TelemetryRollupDTO] = Field(default_factory=list, alias="telemetry_rollups")


class OrgFocalDashboardDTO(BijouBaseModel):
    """Deep inspection payload for a single Organization."""

    organization: OrganizationDTO = Field(..., alias="organization")
    pool_balances: list[ResourcePoolBalanceDTO] = Field(default_factory=list, alias="pool_balances")
    direct_funded_efforts: list[ForecastedEffortNodeDTO] = Field(
        default_factory=list, alias="direct_funded_efforts"
    )
    indirect_benefit_paths: list[IndirectBenefitPathDTO] = Field(
        default_factory=list, alias="indirect_benefit_paths"
    )
    org_interest_priorities: list[DynamicOrgInterestPriorityDTO] = Field(
        default_factory=list, alias="org_interest_priorities"
    )
    org_relationships: list[OrgOrgEdgeDTO] = Field(default_factory=list, alias="org_relationships")
    potential_partnerships: list[SharedInterestPartnershipDTO] = Field(
        default_factory=list, alias="potential_partnerships"
    )


class InterestFocalDashboardDTO(BijouBaseModel):
    """Deep inspection payload for a single Interest & its lineage."""

    interest: InterestDTO = Field(..., alias="interest")
    ancestor_interests: list[InterestDTO] = Field(default_factory=list, alias="ancestor_interests")
    descendant_interests: list[InterestDTO] = Field(default_factory=list, alias="descendant_interests")
    eligible_resource_pools: list[ResourcePoolBalanceDTO] = Field(
        default_factory=list, alias="eligible_resource_pools"
    )
    aligned_efforts: list[ForecastedEffortNodeDTO] = Field(default_factory=list, alias="aligned_efforts")
    stakeholder_stances: list[OrgInterestEdgeDTO] = Field(default_factory=list, alias="stakeholder_stances")


class PerspectiveBriefingDTO(BijouBaseModel):
    """Executive 1-Slide Multi-Perspective Briefing for an Organization."""

    subject_org_id: str = Field(..., alias="subject_org_id")
    active_access_mode: AccessMode = Field(default=AccessMode.GLOBAL_ANALYST, alias="active_access_mode")
    include_hierarchy_inheritance: bool = Field(default=True, alias="include_hierarchy_inheritance")
    as_of_date: date = Field(..., alias="as_of_date")
    directly_resourced_efforts: list[ForecastedEffortNodeDTO] = Field(
        default_factory=list, alias="directly_resourced_efforts"
    )
    indirect_benefits: list[IndirectBenefitPathDTO] = Field(default_factory=list, alias="indirect_benefits")
    priority_interests: list[DynamicOrgInterestPriorityDTO] = Field(
        default_factory=list, alias="priority_interests"
    )
    pool_balances: list[ResourcePoolBalanceDTO] = Field(default_factory=list, alias="pool_balances")
    active_risks: list[RiskDTO] = Field(default_factory=list, alias="active_risks")
    partnership_opportunities: list[SharedInterestPartnershipDTO] = Field(
        default_factory=list, alias="partnership_opportunities"
    )
    total_allocated_usd: float = Field(default=0.0, alias="total_allocated_usd", ge=0.0)
    executive_summary_narrative: str | None = Field(default=None, alias="executive_summary_narrative")
    strategic_gaps: list[str] = Field(default_factory=list, alias="strategic_gaps")


class DistantEffortInvestorDTO(BijouBaseModel):
    """Organization invested in or holding an Interest stake on a downstream Effort."""

    effort_id: str = Field(..., alias="effort_id")
    effort_name: str = Field(..., alias="effort_name")
    effort_state: EffortState = Field(..., alias="effort_state")
    hop_distance: int = Field(..., alias="hop_distance", ge=1)
    is_terminal_end: bool = Field(default=False, alias="is_terminal_end")
    path_effort_ids: list[str] = Field(default_factory=list, alias="path_effort_ids")
    path_relation_types: list[BlockingMode] = Field(default_factory=list, alias="path_relation_types")
    investing_org_ids: list[str] = Field(default_factory=list, alias="investing_org_ids")
    investing_org_names: list[str] = Field(default_factory=list, alias="investing_org_names")
    total_invested_usd: float = Field(default=0.0, alias="total_invested_usd", ge=0.0)
    stakeholder_org_ids: list[str] = Field(default_factory=list, alias="stakeholder_org_ids")
    stakeholder_org_names: list[str] = Field(default_factory=list, alias="stakeholder_org_names")


class EffortResourceGapDTO(BijouBaseModel):
    """Unmet resource requirement on an Effort for executive resourcing asks."""

    requirement_id: str = Field(..., alias="requirement_id")
    category: ResourceCategory = Field(..., alias="category")
    required_amount: float = Field(..., alias="required_amount", ge=0.0)
    allocated_amount: float = Field(default=0.0, alias="allocated_amount", ge=0.0)
    shortfall_amount: float = Field(default=0.0, alias="shortfall_amount", ge=0.0)
    unit: str = Field(..., alias="unit")
    required_skill: str | None = Field(default=None, alias="required_skill")


class EffortBriefingDTO(BijouBaseModel):
    """Executive 1-Slide Multi-Hop Effort Briefing with Linkages & Template Hints."""

    subject_effort_id: str = Field(..., alias="subject_effort_id")
    active_access_mode: AccessMode = Field(default=AccessMode.GLOBAL_ANALYST, alias="active_access_mode")
    as_of_date: date = Field(..., alias="as_of_date")
    recommended_template: str = Field(default="EXECUTION_IMPACT", alias="recommended_template")
    forecast: ForecastedEffortNodeDTO = Field(..., alias="forecast")
    organizations: list[OrganizationDTO] = Field(default_factory=list, alias="organizations")
    direct_resourcing_edges: list[OrgEffortEdgeDTO] = Field(
        default_factory=list, alias="direct_resourcing_edges"
    )
    effort_interest_edges: list[EffortInterestEdgeDTO] = Field(
        default_factory=list, alias="effort_interest_edges"
    )
    aligned_interests: list[InterestDTO] = Field(default_factory=list, alias="aligned_interests")
    ancestor_interest_categories: list[InterestDTO] = Field(
        default_factory=list, alias="ancestor_interest_categories"
    )
    upstream_effort_edges: list[EffortEffortEdgeDTO] = Field(
        default_factory=list, alias="upstream_effort_edges"
    )
    downstream_effort_edges: list[EffortEffortEdgeDTO] = Field(
        default_factory=list, alias="downstream_effort_edges"
    )
    chain_efforts: list[ForecastedEffortNodeDTO] = Field(default_factory=list, alias="chain_efforts")
    distant_effort_investors: list[DistantEffortInvestorDTO] = Field(
        default_factory=list, alias="distant_effort_investors"
    )
    resource_gaps: list[EffortResourceGapDTO] = Field(default_factory=list, alias="resource_gaps")
    active_risks: list[RiskDTO] = Field(default_factory=list, alias="active_risks")
    unexercised_mitigators: list[MitigatorDTO] = Field(default_factory=list, alias="unexercised_mitigators")
    exercised_mitigators: list[MitigatorDTO] = Field(default_factory=list, alias="exercised_mitigators")
    indirect_beneficiaries: list[IndirectBenefitPathDTO] = Field(
        default_factory=list, alias="indirect_beneficiaries"
    )
    total_direct_allocated_usd: float = Field(default=0.0, alias="total_direct_allocated_usd", ge=0.0)
    total_mitigation_ask_usd: float = Field(default=0.0, alias="total_mitigation_ask_usd", ge=0.0)
    executive_summary_narrative: str | None = Field(default=None, alias="executive_summary_narrative")
    key_decision_asks: list[str] = Field(default_factory=list, alias="key_decision_asks")


class DiagnosticReportDTO(BijouBaseModel):
    """Pre-flight diagnostic linting report for manifests and portfolio integrity."""

    blockers: list[str] = Field(default_factory=list, alias="blockers")
    warnings: list[str] = Field(default_factory=list, alias="warnings")
    effort_cycles: list[list[str]] = Field(default_factory=list, alias="effort_cycles")
    interest_cycles: list[list[str]] = Field(default_factory=list, alias="interest_cycles")
    color_of_money_violations: list[str] = Field(default_factory=list, alias="color_of_money_violations")
    overallocated_pools: list[str] = Field(default_factory=list, alias="overallocated_pools")
    skill_mismatch_risks: list[str] = Field(default_factory=list, alias="skill_mismatch_risks")


class AccessPerspectiveStateDTO(BijouBaseModel):
    """Current manual demo perspective state and available managed org roles."""

    mode: AccessMode = Field(default=AccessMode.GLOBAL_ANALYST, alias="mode")
    active_org_id: str | None = Field(default=None, alias="active_org_id")
    managed_organizations: list[OrganizationDTO] = Field(
        default_factory=list, alias="managed_organizations"
    )
