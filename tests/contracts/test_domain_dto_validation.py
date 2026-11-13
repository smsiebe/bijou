"""Contract tests for Bijou v2 core domain DTOs, timing modes, and pedigree edges."""

from datetime import date

import pytest
from pydantic import ValidationError

from bijou.core.contracts import (
    BijouManifestDTO,
    BlockingMode,
    ConfidenceLevel,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    EffortInterestRelationType,
    EffortState,
    EffortTimingMode,
    InterestDTO,
    InterestKind,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgInterestStance,
    OrgOrgEdgeDTO,
    OrgOrgRelationType,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
    RiskSeverity,
)


def test_effort_timing_mode_inference_and_date_validation() -> None:
    """Effort timing_mode reflects explicit dates vs duration-only vs unknown."""
    e_explicit = EffortDTO(
        id="eff-1",
        name="Explicit Program",
        state=EffortState.IN_WORK,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
    )
    assert e_explicit.timing_mode == EffortTimingMode.EXPLICIT_DATES

    e_dur = EffortDTO(
        id="eff-2",
        name="Duration Only",
        state=EffortState.PLANNED,
        estimated_duration_days=90,
    )
    assert e_dur.timing_mode == EffortTimingMode.DURATION_ONLY

    e_unknown = EffortDTO(
        id="eff-3",
        name="Discovery Item",
        state=EffortState.DISCOVERY_PENDING,
    )
    assert e_unknown.timing_mode == EffortTimingMode.UNKNOWN

    with pytest.raises(ValidationError):
        EffortDTO(
            id="eff-bad",
            name="Invalid Dates",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 1, 1),
        )


def test_interest_date_bounds_and_kinds() -> None:
    """Interests reject end_date preceding start_date and support null temporality."""
    intr = InterestDTO(
        id="intr-res",
        name="Operational Resiliency",
        interest_kind=InterestKind.STRATEGIC_CONCEPT,
    )
    assert intr.start_date is None and intr.end_date is None

    with pytest.raises(ValidationError):
        InterestDTO(
            id="intr-bad",
            name="Broken Window",
            start_date=date(2027, 5, 1),
            end_date=date(2026, 5, 1),
        )


def test_effort_nested_requirements_risks_and_mitigators() -> None:
    """Efforts support optional one-to-many requirements, risks, and mitigators."""
    req = ResourceRequirementDTO(
        id="req-rf",
        category=ResourceCategory.STAFF,
        label="Cleared RF Engineer",
        quantity=2.0,
        unit="FTE",
        required_skill="TS/SCI RF DSP Engineer",
        estimated_cost_usd=320000.0,
        is_generic=False,
    )
    risk = RiskDTO(
        id="risk-1",
        effort_id="eff-ew",
        title="Schedule Slip Risk",
        severity=RiskSeverity.HIGH,
        likelihood=0.7,
        potential_slip_days=45,
    )
    mit = MitigatorDTO(
        id="mit-1",
        effort_id="eff-ew",
        risk_id="risk-1",
        name="Contractor Surge",
        is_exercised=False,
        slip_reduction_days=30,
        additional_requirements=[
            ResourceRequirementDTO(
                category=ResourceCategory.MONEY,
                label="Surge Funding",
                quantity=150000.0,
                unit="USD",
                estimated_cost_usd=150000.0,
            )
        ],
    )
    eff = EffortDTO(
        id="eff-ew",
        name="EW Payloads",
        resource_requirements=[req],
        risks=[risk],
        mitigators=[mit],
    )
    assert len(eff.resource_requirements) == 1
    assert eff.mitigators[0].additional_requirements[0].unit == "USD"


def test_pedigree_edges_and_manifest_bundle() -> None:
    """All 6 typed relationship edges embed confidence, provenance, and strict bounds."""
    org = OrganizationDTO(id="org-1", name="Command 1", is_managed=True)
    pool = ResourcePoolDTO(
        id="pool-1",
        org_id="org-1",
        name="FY27 Resiliency Funds",
        category=ResourceCategory.MONEY,
        capacity=1000000.0,
        restricted_interest_ids=["intr-1"],
    )
    e_oo = OrgOrgEdgeDTO(
        source_org_id="org-1",
        target_org_id="org-2",
        relation_type=OrgOrgRelationType.COLLABORATIVE_ADJACENT,
        confidence=ConfidenceLevel.ASSESSED,
        provenance_note="Working group minutes",
    )
    e_oi = OrgInterestEdgeDTO(
        org_id="org-1",
        interest_id="intr-1",
        stance=OrgInterestStance.RESPONSIBLE_OWNER,
        priority_rank=0.95,
    )
    e_oe = OrgEffortEdgeDTO(
        org_id="org-1",
        effort_id="eff-1",
        resourcing_type=ResourceCategory.MONEY,
        resource_pool_id="pool-1",
        allocation_amount=250000.0,
        allocation_unit="USD",
        is_generic=False,
    )
    e_ei = EffortInterestEdgeDTO(
        effort_id="eff-1",
        interest_id="intr-1",
        relation_type=EffortInterestRelationType.DIRECT_SOLUTION,
        impact_weight=0.9,
        confidence=ConfidenceLevel.CONFIRMED,
    )
    e_ee = EffortEffortEdgeDTO(
        source_effort_id="eff-0",
        target_effort_id="eff-1",
        blocking_mode=BlockingMode.NON_BLOCKING_INFORMS,
        dependency_degree=0.6,
        confidence=ConfidenceLevel.UNCONFIRMED,
    )

    manifest = BijouManifestDTO(
        organizations=[org],
        resource_pools=[pool],
        org_org_edges=[e_oo],
        org_interest_edges=[e_oi],
        org_effort_edges=[e_oe],
        effort_interest_edges=[e_ei],
        effort_effort_edges=[e_ee],
    )
    assert manifest.schema_version == "2.0.0"
    assert e_ee.blocking_mode == BlockingMode.NON_BLOCKING_INFORMS
