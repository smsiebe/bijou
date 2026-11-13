"""Tests for InMemoryGraphProjectionEngine (Views A, B, C, Focal Dashboards, Briefing, Diagnostics)."""

from datetime import date

from bijou.core.contracts import (
    AccessMode,
    BijouManifestDTO,
    BillOfEffortsSimulationRequestDTO,
    ConfidenceLevel,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    EffortState,
    InterestDTO,
    InterestInterestEdgeDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    SimulatedPoolAllocationDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine


def _sample_manifest() -> BijouManifestDTO:
    return BijouManifestDTO(
        organizations=[
            OrganizationDTO(id="org-lead", name="Lead Directorate", is_managed=True),
            OrganizationDTO(id="org-partner", name="Partner Wing", is_managed=False),
        ],
        interests=[
            InterestDTO(id="intr-top", name="Resiliency"),
            InterestDTO(id="intr-sub", name="Optical Comms Resiliency"),
        ],
        interest_interest_edges=[
            InterestInterestEdgeDTO(
                parent_interest_id="intr-top",
                child_interest_id="intr-sub",
                confidence=ConfidenceLevel.CONFIRMED,
            )
        ],
        resource_pools=[
            ResourcePoolDTO(
                id="pool-top",
                org_id="org-lead",
                name="Resiliency Fund",
                category=ResourceCategory.MONEY,
                capacity=500000.0,
                unit="USD",
                restricted_interest_ids=["intr-top"],
            ),
            ResourcePoolDTO(
                id="pool-staff",
                org_id="org-lead",
                name="General Engineers",
                category=ResourceCategory.STAFF,
                capacity=2.0,
                unit="FTE",
                skill_tag="General Systems Engineer",
            ),
        ],
        efforts=[
            EffortDTO(
                id="eff-1",
                name="Optical Relay",
                state=EffortState.IN_WORK,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 12, 1),
                resource_requirements=[
                    ResourceRequirementDTO(
                        id="req-dsp",
                        category=ResourceCategory.STAFF,
                        label="DSP Specialist",
                        quantity=1.0,
                        unit="FTE",
                        required_skill="TS/SCI RF DSP Engineer",
                        estimated_cost_usd=200000.0,
                        is_generic=False,
                    )
                ],
                mitigators=[
                    MitigatorDTO(
                        id="mit-accel",
                        effort_id="eff-1",
                        name="Accelerate Testbench",
                        slip_reduction_days=30,
                        is_exercised=False,
                    )
                ],
            ),
            EffortDTO(
                id="eff-2",
                name="Downstream Fusion",
                state=EffortState.PLANNED,
                start_date=date(2027, 1, 1),
                end_date=date(2027, 6, 1),
            ),
        ],
        effort_interest_edges=[
            EffortInterestEdgeDTO(effort_id="eff-1", interest_id="intr-sub", confidence=ConfidenceLevel.CONFIRMED),
            EffortInterestEdgeDTO(effort_id="eff-2", interest_id="intr-top", confidence=ConfidenceLevel.UNCONFIRMED),
        ],
        org_interest_edges=[
            OrgInterestEdgeDTO(org_id="org-lead", interest_id="intr-top", priority_rank=0.9),
            OrgInterestEdgeDTO(org_id="org-partner", interest_id="intr-sub", priority_rank=0.8),
        ],
        org_effort_edges=[
            OrgEffortEdgeDTO(org_id="org-lead", effort_id="eff-1", allocation_amount=100000.0, allocation_unit="USD")
        ],
        effort_effort_edges=[
            EffortEffortEdgeDTO(source_effort_id="eff-1", target_effort_id="eff-2", confidence=ConfidenceLevel.CONFIRMED)
        ],
    )


def test_views_a_b_c_and_pedigree_filtering() -> None:
    engine = InMemoryGraphProjectionEngine()
    engine.rebuild_projection(_sample_manifest())

    view_a = engine.build_capability_tree_view(as_of_date=date(2026, 11, 1), min_confidence=ConfidenceLevel.CONFIRMED)
    assert len(view_a.nodes) == 2
    # UNCONFIRMED effort-interest edge on eff-2 is filtered out when min_confidence=CONFIRMED
    assert len(view_a.effort_interest_edges) == 1

    view_b = engine.build_tripartite_flow_view(as_of_date=date(2026, 11, 1))
    assert len(view_b.indirect_benefits) >= 1
    assert any(b.beneficiary_org_id == "org-partner" for b in view_b.indirect_benefits)

    # View C: Simulate Bill of Efforts exercising mitigator + mismatched staff + slip shock
    sim = engine.simulate_bill_of_efforts(
        BillOfEffortsSimulationRequestDTO(
            toggle_mitigators={"mit-accel": True},
            add_allocations=[
                SimulatedPoolAllocationDTO(
                    org_id="org-lead",
                    pool_id="pool-staff",
                    effort_id="eff-1",
                    requirement_id="req-dsp",
                    resourcing_type=ResourceCategory.STAFF,
                    amount=1.0,
                    unit="FTE",
                    assigned_skill="General Systems Engineer",
                    is_generic=False,
                    human_slip_penalty_days=25,
                )
            ],
            effort_slips={"eff-1": 40},
        ),
        as_of_date=date(2026, 11, 1),
    )
    assert len(sim.skill_mismatch_warnings) == 1
    assert sim.skill_mismatch_warnings[0].suggested_slip_penalty_days == 25
    assert len(sim.newly_registered_risks) == 1
    assert "eff-1" in sim.impacted_effort_ids
    assert "eff-2" in sim.impacted_effort_ids


def test_focal_dashboards_briefing_and_diagnostics() -> None:
    engine = InMemoryGraphProjectionEngine()
    engine.rebuild_projection(_sample_manifest())

    ef_focal = engine.build_effort_focal_dashboard("eff-1", telemetry_rollups=[], as_of_date=date(2026, 11, 1))
    assert len(ef_focal.downstream_dependents) == 1
    assert any(i.id == "intr-top" for i in ef_focal.ancestor_interest_categories)

    org_focal = engine.build_org_focal_dashboard("org-lead", as_of_date=date(2026, 11, 1))
    assert len(org_focal.pool_balances) == 2
    assert len(org_focal.potential_partnerships) == 1

    intr_focal = engine.build_interest_focal_dashboard("intr-sub", as_of_date=date(2026, 11, 1))
    # pool-top is restricted to intr-top -> inherits down to intr-sub!
    assert any(pb.pool.id == "pool-top" for pb in intr_focal.eligible_resource_pools)

    briefing = engine.build_perspective_briefing(
        subject_org_id="org-lead",
        active_access_mode=AccessMode.MANAGED_ORG_OWNER,
        include_hierarchy_inheritance=True,
        as_of_date=date(2026, 11, 1),
    )
    assert briefing.total_allocated_usd == 100000.0
    assert briefing.active_access_mode == AccessMode.MANAGED_ORG_OWNER

    diag = engine.validate_manifest_diagnostics()
    assert diag.effort_cycles == []
    assert diag.interest_cycles == []
