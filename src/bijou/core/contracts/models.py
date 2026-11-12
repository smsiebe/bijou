"""Core domain entities and typed graph edge DTOs for Bijou v2."""

import uuid
from datetime import date, datetime, timezone
from typing import Self

from pydantic import Field, model_validator

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import (
    BlockingMode,
    ConfidenceLevel,
    EffortInterestRelationType,
    EffortState,
    EffortTimingMode,
    InterestInterestRelationType,
    InterestKind,
    OrgInterestStance,
    OrgOrgRelationType,
    ResourceCategory,
    RiskSeverity,
    RiskStatus,
)


class OrganizationDTO(BijouBaseModel):
    """Organization node representing a command, agency, or team (managed or modeled)."""

    id: str = Field(..., alias="id", description="Unique organization identifier")
    name: str = Field(..., alias="name", description="Organization display name")
    description: str = Field(default="", alias="description", description="Organization mission or scope")
    echelon_level: int = Field(default=1, alias="echelon_level", ge=0, description="Organizational tier level")
    is_managed: bool = Field(
        default=False,
        alias="is_managed",
        description="Whether an owner actively manages resource inventories for this org",
    )
    tags: list[str] = Field(default_factory=list, alias="tags", description="Classification tags")


class ResourcePoolDTO(BijouBaseModel):
    """Inventory or designated budget pool owned by an Organization."""

    id: str = Field(..., alias="id", description="Unique resource pool identifier")
    org_id: str = Field(..., alias="org_id", description="Owning organization ID")
    name: str = Field(..., alias="name", description="Pool display name (e.g. 'FY27 Resiliency Funds')")
    category: ResourceCategory = Field(..., alias="category", description="Resource category")
    capacity: float = Field(..., alias="capacity", ge=0.0, description="Total pool capacity")
    unit: str = Field(default="USD", alias="unit", description="Capacity unit (USD, FTE, GPU_HRS, UNITS)")
    skill_tag: str | None = Field(
        default=None,
        alias="skill_tag",
        description="Optional non-transferable skill or compute hardware tag",
    )
    restricted_interest_ids: list[str] = Field(
        default_factory=list,
        alias="restricted_interest_ids",
        description="Color-of-money Interest IDs (inherited down Interest DAG)",
    )
    description: str = Field(default="", alias="description", description="Pool description or appropriation notes")


class InterestDTO(BijouBaseModel):
    """Strategic concept, mission goal, NIPF priority, gap, threat vector, or stakeholder interest."""

    id: str = Field(..., alias="id", description="Unique interest identifier")
    name: str = Field(..., alias="name", description="Interest name")
    description: str = Field(default="", alias="description", description="Detailed description")
    interest_kind: InterestKind = Field(
        default=InterestKind.STRATEGIC_CONCEPT,
        alias="interest_kind",
        description="Categorical classification",
    )
    start_date: date | None = Field(default=None, alias="start_date", description="Optional effective start date")
    end_date: date | None = Field(default=None, alias="end_date", description="Optional effective end date")

    @model_validator(mode="after")
    def _validate_dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Interest end_date cannot precede start_date")
        return self


class ResourceRequirementDTO(BijouBaseModel):
    """Optional one-to-many resource requirement attached to an Effort or Mitigator."""

    id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:8]}", alias="id", description="Requirement ID")
    category: ResourceCategory = Field(..., alias="category", description="Required resource category")
    label: str = Field(..., alias="label", description="Requirement title or role name")
    quantity: float = Field(default=1.0, alias="quantity", ge=0.0, description="Required quantity")
    unit: str = Field(default="USD", alias="unit", description="Unit of measure (USD, FTE, GPU_HRS, etc.)")
    required_skill: str | None = Field(
        default=None,
        alias="required_skill",
        description="Specific non-transferable skill or compute class required",
    )
    estimated_cost_usd: float | None = Field(
        default=None,
        alias="estimated_cost_usd",
        ge=0.0,
        description="Optional monetary valuation in USD",
    )
    is_generic: bool = Field(
        default=True,
        alias="is_generic",
        description="True when modeled generically without specific skill/pool constraints",
    )


class RiskDTO(BijouBaseModel):
    """Delivery, technical, or resource mismatch risk associated with an Effort."""

    id: str = Field(default_factory=lambda: f"risk-{uuid.uuid4().hex[:8]}", alias="id", description="Unique risk ID")
    effort_id: str = Field(..., alias="effort_id", description="Parent Effort ID")
    title: str = Field(..., alias="title", description="Short risk title")
    description: str = Field(default="", alias="description", description="Risk factor description")
    severity: RiskSeverity = Field(default=RiskSeverity.MEDIUM, alias="severity", description="Severity tier")
    likelihood: float = Field(default=0.5, alias="likelihood", ge=0.0, le=1.0, description="Probability (0.0 to 1.0)")
    potential_slip_days: int = Field(
        default=0,
        alias="potential_slip_days",
        ge=0,
        description="Potential schedule slip in days if realized",
    )
    is_skill_mismatch_risk: bool = Field(
        default=False,
        alias="is_skill_mismatch_risk",
        description="True when generated or flagged due to non-transferable skill mismatch",
    )
    status: RiskStatus = Field(default=RiskStatus.ACTIVE, alias="status", description="Current risk status")
    related_requirement_id: str | None = Field(
        default=None,
        alias="related_requirement_id",
        description="Optional linked ResourceRequirement ID",
    )


class MitigatorDTO(BijouBaseModel):
    """Actionable mitigation option (exercised or unexercised) offsetting Risk/slip on an Effort."""

    id: str = Field(default_factory=lambda: f"mit-{uuid.uuid4().hex[:8]}", alias="id", description="Unique mitigator ID")
    effort_id: str = Field(..., alias="effort_id", description="Target Effort ID")
    risk_id: str | None = Field(default=None, alias="risk_id", description="Optional target Risk ID")
    name: str = Field(..., alias="name", description="Mitigator action title")
    description: str = Field(default="", alias="description", description="Mitigation rationale and action")
    is_exercised: bool = Field(
        default=False,
        alias="is_exercised",
        description="True if mitigation option has been committed/exercised",
    )
    slip_reduction_days: int = Field(
        default=0,
        alias="slip_reduction_days",
        ge=0,
        description="Schedule slip days recovered when exercised",
    )
    risk_reduction_factor: float = Field(
        default=0.5,
        alias="risk_reduction_factor",
        ge=0.0,
        le=1.0,
        description="Fractional risk severity/likelihood reduction (0.0 to 1.0)",
    )
    additional_requirements: list[ResourceRequirementDTO] = Field(
        default_factory=list,
        alias="additional_requirements",
        description="Additional resource inputs needed to exercise this mitigator",
    )


class EffortDTO(BijouBaseModel):
    """Work item, capability program, or discovery activity inside the progression tree."""

    id: str = Field(..., alias="id", description="Unique effort identifier")
    name: str = Field(..., alias="name", description="Effort display title")
    description: str = Field(default="", alias="description", description="Scope and deliverable summary")
    state: EffortState = Field(default=EffortState.PLANNED, alias="state", description="Execution state")
    start_date: date | None = Field(default=None, alias="start_date", description="Explicit start date if known")
    end_date: date | None = Field(default=None, alias="end_date", description="Explicit end date if known")
    estimated_duration_days: int | None = Field(
        default=None,
        alias="estimated_duration_days",
        ge=1,
        description="Relative duration in days when explicit dates are unavailable",
    )
    resource_requirements: list[ResourceRequirementDTO] = Field(
        default_factory=list,
        alias="resource_requirements",
        description="Required resources (personnel, compute, money, material)",
    )
    risks: list[RiskDTO] = Field(default_factory=list, alias="risks", description="Known delivery risks")
    mitigators: list[MitigatorDTO] = Field(
        default_factory=list,
        alias="mitigators",
        description="Available or exercised mitigation options",
    )

    @property
    def timing_mode(self) -> EffortTimingMode:
        """Infer timing certainty tier from explicit dates and duration."""
        if self.end_date is not None or (self.start_date is not None and self.estimated_duration_days is not None):
            return EffortTimingMode.EXPLICIT_DATES
        if self.estimated_duration_days is not None:
            return EffortTimingMode.DURATION_ONLY
        return EffortTimingMode.UNKNOWN

    @model_validator(mode="after")
    def _validate_dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Effort end_date cannot precede start_date")
        return self


# --- Six Typed Relationship Edges with Intelligence Pedigree ---


class PedigreeEdgeBase(BijouBaseModel):
    """Base contract carrying intelligence confidence, provenance, and optional temporality."""

    id: str = Field(default_factory=lambda: f"edge-{uuid.uuid4().hex[:8]}", alias="id", description="Edge ID")
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.CONFIRMED,
        alias="confidence",
        description="Intelligence certainty tier",
    )
    provenance_note: str | None = Field(
        default=None,
        alias="provenance_note",
        description="Source attribution or analytical basis",
    )
    effective_start: date | None = Field(default=None, alias="effective_start", description="Optional start date")
    effective_end: date | None = Field(default=None, alias="effective_end", description="Optional end date")


class OrgOrgEdgeDTO(PedigreeEdgeBase):
    """Relationship between two Organizations (hierarchical, formal support, or collaborative)."""

    source_org_id: str = Field(..., alias="source_org_id", description="Source/Parent/Supporting Org ID")
    target_org_id: str = Field(..., alias="target_org_id", description="Target/Child/Supported Org ID")
    relation_type: OrgOrgRelationType = Field(..., alias="relation_type", description="Relationship nature")


class OrgInterestEdgeDTO(PedigreeEdgeBase):
    """Many-to-many link expressing an Organization's stance and priority toward an Interest."""

    org_id: str = Field(..., alias="org_id", description="Organization ID")
    interest_id: str = Field(..., alias="interest_id", description="Interest ID")
    stance: OrgInterestStance = Field(
        default=OrgInterestStance.MISSION_ALIGNED,
        alias="stance",
        description="Role/stance toward the interest",
    )
    priority_rank: float = Field(
        default=0.5,
        alias="priority_rank",
        ge=0.0,
        le=1.0,
        description="Org-defined normalized priority (0.0 to 1.0)",
    )
    allow_hierarchy_inheritance: bool = Field(
        default=True,
        alias="allow_hierarchy_inheritance",
        description="Whether visualization tools may inherit this priority down org hierarchy",
    )


class InterestInterestEdgeDTO(PedigreeEdgeBase):
    """Directed edge in the Interest taxonomy DAG (generic category -> specific interest)."""

    parent_interest_id: str = Field(..., alias="parent_interest_id", description="Broader/parent Interest ID")
    child_interest_id: str = Field(..., alias="child_interest_id", description="Specific/child Interest ID")
    relation_type: InterestInterestRelationType = Field(
        default=InterestInterestRelationType.SPECIALIZES,
        alias="relation_type",
        description="Taxonomy edge type",
    )


class OrgEffortEdgeDTO(PedigreeEdgeBase):
    """Direct resourcing link from an Organization (or ResourcePool) into an Effort."""

    org_id: str = Field(..., alias="org_id", description="Resourcing Organization ID")
    effort_id: str = Field(..., alias="effort_id", description="Target Effort ID")
    resourcing_type: ResourceCategory = Field(
        default=ResourceCategory.GENERIC_SUPPORT,
        alias="resourcing_type",
        description="Type of resource contributed",
    )
    resource_pool_id: str | None = Field(
        default=None,
        alias="resource_pool_id",
        description="Optional linked ResourcePool ID for managed org tracking",
    )
    requirement_id: str | None = Field(
        default=None,
        alias="requirement_id",
        description="Optional satisfied ResourceRequirement ID",
    )
    allocation_amount: float = Field(default=0.0, alias="allocation_amount", ge=0.0, description="Allocated amount")
    allocation_unit: str = Field(default="UNITS", alias="allocation_unit", description="Allocation unit")
    assigned_skill: str | None = Field(
        default=None,
        alias="assigned_skill",
        description="Actual assigned skill or compute tag",
    )
    is_generic: bool = Field(
        default=True,
        alias="is_generic",
        description="True when modeled without explicit managed pool assignment",
    )


class EffortInterestEdgeDTO(PedigreeEdgeBase):
    """Many-to-many link describing how an Effort aligns with or satisfies an Interest."""

    effort_id: str = Field(..., alias="effort_id", description="Effort ID")
    interest_id: str = Field(..., alias="interest_id", description="Interest ID")
    relation_type: EffortInterestRelationType = Field(
        default=EffortInterestRelationType.DIRECT_SOLUTION,
        alias="relation_type",
        description="Contribution alignment type",
    )
    impact_weight: float = Field(
        default=1.0,
        alias="impact_weight",
        ge=0.0,
        le=1.0,
        description="Contribution weight (0.0 to 1.0)",
    )


class EffortEffortEdgeDTO(PedigreeEdgeBase):
    """Causal dependency between an upstream Effort and a downstream Effort."""

    source_effort_id: str = Field(..., alias="source_effort_id", description="Upstream predecessor Effort ID")
    target_effort_id: str = Field(..., alias="target_effort_id", description="Downstream dependent Effort ID")
    blocking_mode: BlockingMode = Field(
        default=BlockingMode.BLOCKING,
        alias="blocking_mode",
        description="Whether upstream blocks downstream schedule or informs it non-blocking",
    )
    dependency_degree: float = Field(
        default=1.0,
        alias="dependency_degree",
        ge=0.0,
        le=1.0,
        description="Strength of technical/operational coupling (0.0 to 1.0)",
    )


class DecisionLogEntryDTO(BijouBaseModel):
    """Audit ledger entry tracking portfolio simulations, risk overrides, and rationale."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="id", description="Unique decision entry ID")
    target_effort_id: str = Field(..., alias="target_effort_id", description="Target Effort ID")
    author: str = Field(..., alias="author", description="Decision maker or analyst perspective")
    justification: str = Field(..., alias="justification", description="Strategic justification or rationale")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="timestamp",
        description="UTC timestamp when decision was recorded",
    )
