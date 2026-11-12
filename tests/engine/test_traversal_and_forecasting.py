"""Unit tests for v2 traversal rules (Color-of-Money, Skill Mismatch, Indirect Benefits) and Forecasting math."""

from datetime import date

import pytest

from bijou.core.contracts import (
    BlockingMode,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    EffortState,
    ForecastHorizonStatus,
    InterestDTO,
    InterestInterestEdgeDTO,
    MitigatorDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgInterestStance,
    OrganizationDTO,
    OrgOrgEdgeDTO,
    OrgOrgRelationType,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
)
from bijou.core.engine.forecasting import detect_cycles_in_graph, resolve_effort_forecasts
from bijou.core.engine.traversal import (
    compute_dynamic_hierarchy_priorities,
    compute_pool_balances,
    discover_indirect_benefits_and_partnerships,
    evaluate_skill_mismatch,
    get_interest_descendants,
)


def test_color_of_money_inherits_down_interest_dag() -> None:
    """An earmarked ResourcePool restricted to a parent Interest is eligible for descendant sub-interests."""
    interests = [
        InterestDTO(id="intr-parent", name="Operational Resiliency"),
        InterestDTO(id="intr-child", name="Optical Crosslink Resiliency"),
        InterestDTO(id="intr-unrelated", name="Unrelated Mission"),
    ]
    interest_edges = [
        InterestInterestEdgeDTO(parent_interest_id="intr-parent", child_interest_id="intr-child")
    ]
    pools = [
        ResourcePoolDTO(
            id="pool-resiliency",
            org_id="org-a",
            name="Resiliency Money",
            category=ResourceCategory.MONEY,
            capacity=500000.0,
            unit="USD",
            restricted_interest_ids=["intr-parent"],
        )
    ]
    efforts = [
        EffortDTO(id="eff-eligible", name="Optical Mesh"),
        EffortDTO(id="eff-violating", name="Unrelated Effort"),
    ]
    effort_interest_edges = [
        EffortInterestEdgeDTO(effort_id="eff-eligible", interest_id="intr-child"),
        EffortInterestEdgeDTO(effort_id="eff-violating", interest_id="intr-unrelated"),
    ]
    org_effort_edges = [
        OrgEffortEdgeDTO(
            id="oe-good",
            org_id="org-a",
            effort_id="eff-eligible",
            resourcing_type=ResourceCategory.MONEY,
            resource_pool_id="pool-resiliency",
            allocation_amount=200000.0,
            allocation_unit="USD",
            is_generic=False,
        ),
        OrgEffortEdgeDTO(
            id="oe-bad",
            org_id="org-a",
            effort_id="eff-violating",
            resourcing_type=ResourceCategory.MONEY,
            resource_pool_id="pool-resiliency",
            allocation_amount=100000.0,
            allocation_unit="USD",
            is_generic=False,
        ),
    ]

    descendants = get_interest_descendants("intr-parent", interest_edges)
    assert "intr-parent" in descendants
    assert "intr-child" in descendants

    balances = compute_pool_balances(
        pools=pools,
        efforts=efforts,
        org_effort_edges=org_effort_edges,
        effort_interest_edges=effort_interest_edges,
        interest_edges=interest_edges,
    )
    assert len(balances) == 1
    pb = balances[0]
    assert pb.allocated_amount == pytest.approx(300000.0)
    assert pb.remaining_amount == pytest.approx(200000.0)
    assert "intr-child" in pb.eligible_interest_ids
    # Only eff-violating triggers Color-of-Money violation; eff-eligible inherits eligibility cleanly!
    assert len(pb.color_of_money_violations) == 1
    assert "Unrelated Effort" in pb.color_of_money_violations[0]


def test_skill_mismatch_emits_warning_and_customizable_risk() -> None:
    """Assigning a non-matching skill emits a warning and generates a human-adjustable slip Risk."""
    req = ResourceRequirementDTO(
        id="req-rf",
        category=ResourceCategory.STAFF,
        label="Cleared RF Engineer",
        quantity=1.0,
        unit="FTE",
        required_skill="TS/SCI RF DSP Engineer",
        is_generic=False,
    )
    warning = evaluate_skill_mismatch(
        effort_id="eff-x",
        assigned_skill="General Systems Analyst",
        requirement=req,
        is_generic=False,
        human_slip_penalty_days=45,
    )
    assert warning is not None
    assert warning.suggested_slip_penalty_days == 45
    assert warning.generated_risk.is_skill_mismatch_risk is True
    assert warning.generated_risk.potential_slip_days == 45

    # Exact match emits None
    assert evaluate_skill_mismatch("eff-x", "TS/SCI RF DSP Engineer", req) is None


def test_indirect_benefits_and_shared_interest_partnerships() -> None:
    """Orgs sharing an Interest with an Effort they do not directly fund appear as indirect beneficiaries & partnership candidates."""
    orgs = [
        OrganizationDTO(id="org-funder", name="Funder"),
        OrganizationDTO(id="org-beneficiary", name="Beneficiary"),
    ]
    org_interest_edges = [
        OrgInterestEdgeDTO(org_id="org-funder", interest_id="intr-shared", priority_rank=0.9),
        OrgInterestEdgeDTO(
            org_id="org-beneficiary",
            interest_id="intr-shared",
            stance=OrgInterestStance.BENEFICIARY,
            priority_rank=0.85,
        ),
    ]
    org_effort_edges = [
        OrgEffortEdgeDTO(org_id="org-funder", effort_id="eff-tracker", allocation_amount=100000.0)
    ]
    effort_interest_edges = [
        EffortInterestEdgeDTO(effort_id="eff-tracker", interest_id="intr-shared")
    ]

    indirect, partnerships = discover_indirect_benefits_and_partnerships(
        orgs=orgs,
        org_interest_edges=org_interest_edges,
        org_effort_edges=org_effort_edges,
        effort_interest_edges=effort_interest_edges,
        interest_edges=[],
        org_org_edges=[],
    )
    assert len(indirect) == 1
    assert indirect[0].beneficiary_org_id == "org-beneficiary"
    assert indirect[0].effort_id == "eff-tracker"

    assert len(partnerships) == 1
    assert partnerships[0].has_existing_org_link is False
    assert "intr-shared" in partnerships[0].shared_interest_ids


def test_optional_org_hierarchy_priority_inheritance() -> None:
    """Visualization priority inheritance flows parent -> child only when toggle enabled."""
    orgs = [
        OrganizationDTO(id="org-parent", name="Parent Cmd"),
        OrganizationDTO(id="org-child", name="Child Wing"),
    ]
    org_org_edges = [
        OrgOrgEdgeDTO(
            source_org_id="org-parent",
            target_org_id="org-child",
            relation_type=OrgOrgRelationType.HIERARCHICAL_PARENT,
        )
    ]
    org_interest_edges = [
        OrgInterestEdgeDTO(
            org_id="org-parent",
            interest_id="intr-1",
            priority_rank=0.9,
            allow_hierarchy_inheritance=True,
        )
    ]

    with_inherit = compute_dynamic_hierarchy_priorities(
        orgs=orgs,
        org_org_edges=org_org_edges,
        org_interest_edges=org_interest_edges,
        enable_inheritance=True,
    )
    assert any(
        p.org_id == "org-child"
        and p.inherited_from_org_id == "org-parent"
        and p.effective_priority == pytest.approx(0.81)
        for p in with_inherit
    )

    without_inherit = compute_dynamic_hierarchy_priorities(
        orgs=orgs,
        org_org_edges=org_org_edges,
        org_interest_edges=org_interest_edges,
        enable_inheritance=False,
    )
    assert not any(p.org_id == "org-child" for p in without_inherit)


def test_state_aware_and_non_blocking_forecasting_math() -> None:
    """Verifies completed bypass, open-ended active, relative dependency, non-blocking informs, and mitigator acceleration."""
    efforts = [
        EffortDTO(
            id="eff-done",
            name="Completed Baseline",
            state=EffortState.COMPLETED,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 5, 1),
        ),
        EffortDTO(
            id="eff-active",
            name="Open-Ended In-Work",
            state=EffortState.IN_WORK,
            start_date=date(2026, 6, 1),
            end_date=None,
        ),
        EffortDTO(
            id="eff-downstream-blocked",
            name="Blocked By Active",
            state=EffortState.PLANNED,
            estimated_duration_days=90,
            risks=[RiskDTO(id="r1", effort_id="eff-downstream-blocked", title="Delay", potential_slip_days=30)],
            mitigators=[
                MitigatorDTO(
                    id="m1",
                    effort_id="eff-downstream-blocked",
                    risk_id="r1",
                    name="Fast Track",
                    is_exercised=True,
                    slip_reduction_days=20,
                )
            ],
        ),
        EffortDTO(
            id="eff-informed-only",
            name="Non-Blocking Independent",
            state=EffortState.PLANNED,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 9, 1),
        ),
    ]
    effort_edges = [
        EffortEffortEdgeDTO(
            source_effort_id="eff-done",
            target_effort_id="eff-active",
            blocking_mode=BlockingMode.BLOCKING,
        ),
        EffortEffortEdgeDTO(
            source_effort_id="eff-active",
            target_effort_id="eff-downstream-blocked",
            blocking_mode=BlockingMode.BLOCKING,
        ),
        EffortEffortEdgeDTO(
            source_effort_id="eff-active",
            target_effort_id="eff-informed-only",
            blocking_mode=BlockingMode.NON_BLOCKING_INFORMS,
        ),
    ]

    cycles = detect_cycles_in_graph(
        [e.id for e in efforts],
        [(e.source_effort_id, e.target_effort_id) for e in effort_edges],
    )
    assert cycles == []

    forecasts = resolve_effort_forecasts(
        efforts=efforts,
        effort_edges=effort_edges,
        org_effort_edges=[],
        effort_interest_edges=[],
        indirect_paths=[],
        as_of_date=date(2026, 11, 1),
    )
    by_id = {f.effort.id: f for f in forecasts}

    assert by_id["eff-done"].horizon_status == ForecastHorizonStatus.COMPLETED_HISTORICAL
    assert by_id["eff-active"].horizon_status == ForecastHorizonStatus.OPEN_ENDED_ACTIVE
    assert by_id["eff-active"].forecast_end is None

    # Blocked by open-ended eff-active -> stays relative rather than inventing a fake date!
    down = by_id["eff-downstream-blocked"]
    assert down.horizon_status == ForecastHorizonStatus.RELATIVE_TO_DEPENDENCY
    assert "eff-active" in down.blocked_by_effort_ids
    # 90d duration + (30d risk - 20d mitigator reduction = 10d net slip) = 100d relative offset
    assert down.relative_offset_days == 100

    # NON_BLOCKING_INFORMS does NOT turn explicit schedule into relative wait
    inf = by_id["eff-informed-only"]
    assert inf.horizon_status == ForecastHorizonStatus.EXPLICIT_SCHEDULE
    assert "eff-active" in inf.informing_effort_ids
