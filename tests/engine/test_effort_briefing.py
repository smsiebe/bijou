"""Tests for Effort-level 1-slide executive briefings, multi-hop distant investors, and template hints."""

from datetime import date

from bijou.core.contracts.enums import (
    AccessMode,
    BlockingMode,
    EffortState,
    ResourceCategory,
    RiskSeverity,
    RiskStatus,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    ResourceRequirementDTO,
    RiskDTO,
)
from bijou.core.engine.projection import InMemoryGraphProjectionEngine


def test_effort_briefing_traces_multi_hop_distant_investors_and_risk_mitigation_ask() -> None:
    manifest = BijouManifestDTO(
        organizations=[
            OrganizationDTO(id="org-fund", name="Core Sponsor Org"),
            OrganizationDTO(id="org-distant-inv", name="Terminal Investor Org"),
            OrganizationDTO(id="org-distant-stake", name="Terminal Mission Stakeholder"),
        ],
        interests=[
            InterestDTO(id="intr-core", name="Sensor Fusion"),
            InterestDTO(id="intr-end", name="Theater Situational Awareness"),
        ],
        efforts=[
            EffortDTO(
                id="eff-a",
                name="Core Pipeline",
                state=EffortState.IN_WORK,
                resource_requirements=[
                    ResourceRequirementDTO(
                        id="req-eng",
                        category=ResourceCategory.MONEY,
                        label="Pipeline Integration",
                        quantity=200000.0,
                        unit="USD",
                    )
                ],
                risks=[
                    RiskDTO(
                        id="risk-1",
                        effort_id="eff-a",
                        title="Compiler Bottleneck",
                        severity=RiskSeverity.HIGH,
                        status=RiskStatus.ACTIVE,
                        potential_slip_days=45,
                    )
                ],
                mitigators=[
                    MitigatorDTO(
                        id="mit-1",
                        effort_id="eff-a",
                        risk_id="risk-1",
                        name="Parallelize Kernel Build",
                        is_exercised=False,
                        slip_reduction_days=30,
                        additional_requirements=[
                            ResourceRequirementDTO(
                                id="req-mit",
                                category=ResourceCategory.MONEY,
                                label="Burst Compute Contract",
                                quantity=75000.0,
                                unit="USD",
                                estimated_cost_usd=75000.0,
                            )
                        ],
                    )
                ],
            ),
            EffortDTO(id="eff-b", name="Middle Relay", state=EffortState.PLANNED),
            EffortDTO(id="eff-c", name="Distant End Capability", state=EffortState.PLANNED),
        ],
        org_effort_edges=[
            OrgEffortEdgeDTO(
                id="oe-1",
                org_id="org-fund",
                effort_id="eff-a",
                resourcing_type=ResourceCategory.MONEY,
                allocation_amount=120000.0,
                allocation_unit="USD",
            ),
            OrgEffortEdgeDTO(
                id="oe-2",
                org_id="org-distant-inv",
                effort_id="eff-c",
                resourcing_type=ResourceCategory.MONEY,
                allocation_amount=500000.0,
                allocation_unit="USD",
            ),
        ],
        effort_interest_edges=[
            EffortInterestEdgeDTO(id="ei-1", effort_id="eff-a", interest_id="intr-core"),
            EffortInterestEdgeDTO(id="ei-2", effort_id="eff-c", interest_id="intr-end"),
        ],
        org_interest_edges=[
            OrgInterestEdgeDTO(id="oi-1", org_id="org-distant-stake", interest_id="intr-end"),
        ],
        effort_effort_edges=[
            EffortEffortEdgeDTO(
                id="ee-1",
                source_effort_id="eff-a",
                target_effort_id="eff-b",
                blocking_mode=BlockingMode.BLOCKING,
            ),
            EffortEffortEdgeDTO(
                id="ee-2",
                source_effort_id="eff-b",
                target_effort_id="eff-c",
                blocking_mode=BlockingMode.BLOCKING,
            ),
        ],
    )

    engine = InMemoryGraphProjectionEngine()
    engine.rebuild_projection(manifest)

    brief = engine.build_effort_briefing(
        effort_id="eff-a",
        active_access_mode=AccessMode.GLOBAL_ANALYST,
        as_of_date=date(2026, 6, 1),
    )

    assert brief.recommended_template == "RISK_MITIGATION_ASK"
    assert brief.total_direct_allocated_usd == 120000.0
    assert brief.total_mitigation_ask_usd == 75000.0
    assert len(brief.resource_gaps) == 1
    assert brief.resource_gaps[0].shortfall_amount == 80000.0

    # Distant end effort (hop 2) should surface both Terminal Investor Org & Terminal Mission Stakeholder
    assert len(brief.distant_effort_investors) == 2
    end_node = next(d for d in brief.distant_effort_investors if d.effort_id == "eff-c")
    assert end_node.is_terminal_end is True
    assert end_node.hop_distance == 2
    assert end_node.path_effort_ids == ["eff-a", "eff-b", "eff-c"]
    assert end_node.investing_org_ids == ["org-distant-inv"]
    assert end_node.stakeholder_org_ids == ["org-distant-stake"]
    assert end_node.total_invested_usd == 500000.0


def test_effort_briefing_recommends_investment_opportunity_for_unfunded_planned_effort() -> None:
    manifest = BijouManifestDTO(
        efforts=[EffortDTO(id="eff-future", name="Next-Gen Radar", state=EffortState.PLANNED)],
    )
    engine = InMemoryGraphProjectionEngine()
    engine.rebuild_projection(manifest)

    brief = engine.build_effort_briefing(
        effort_id="eff-future",
        active_access_mode=AccessMode.GLOBAL_ANALYST,
        as_of_date=date(2026, 6, 1),
    )
    assert brief.recommended_template == "INVESTMENT_OPPORTUNITY"
