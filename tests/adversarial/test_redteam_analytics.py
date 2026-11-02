"""Adversarial and red-team torture tests for Pareto optimization and manifest diagnostic linter."""

from datetime import date

from bijou.core.contracts import (
    AccumulatorPattern,
    BijouManifestDTO,
    CausalContributorDTO,
    CausalGateDTO,
    CausalMechanismType,
    ConcernDTO,
    ConcernSatisfactionLinkDTO,
    EffectDTO,
    EffectTier,
    GraphEdgeDTO,
    LifecycleStatus,
    MilestoneDTO,
    MilestoneStatus,
    OrganizationDTO,
    RelationshipType,
    ThingDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine


def test_pareto_frontier_rejects_suboptimal_and_respects_ceiling() -> None:
    """Provide 5 candidate Things with realistic costs ($10M-$120M) and assert Pareto non-domination and budget ceiling."""
    org = OrganizationDTO(
        id="org-aerospace-acquisitions",
        name="Aerospace Strategic Systems Acquisition Command",
        echelon_level=1,
        mission_statement="Develop next-generation sovereign orbital and theater capabilities",
    )
    con_surveillance = ConcernDTO(
        id="con-theater-surveillance",
        name="Persistent Theater Surveillance",
        description="Persistent low-latency multispectral observation",
        owner_org_id="org-aerospace-acquisitions",
        priority=0.95,
    )
    con_comms = ConcernDTO(
        id="con-mesh-comms",
        name="Anti-Jam Tactical Communications",
        description="High-bandwidth electronic warfare resilient data links",
        owner_org_id="org-aerospace-acquisitions",
        priority=0.85,
    )

    # 1. Candidate Alpha: Efficient, low-cost optical payload ($15,000,000)
    ms_alpha = MilestoneDTO(
        id="ms-alpha",
        thing_id="th-alpha",
        sequence_index=0,
        name="Alpha Optical Article",
        description="Optical sensor delivery",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 15),
        status=MilestoneStatus.ACHIEVED,
        lane="Optics",
        trl=7,
    )
    th_alpha = ThingDTO(
        id="th-alpha",
        name="Alpha High-Res Optical SmallSat",
        description="Low-cost rapid optical imaging satellite",
        lifecycle=LifecycleStatus.PROPOSED,
        owner_org_id="org-aerospace-acquisitions",
        estimated_cost=15000000.0,
        risk_factor=1.0,
        milestones=[ms_alpha],
    )
    gate_alpha = CausalGateDTO(
        id="gate-alpha",
        name="Alpha Integration Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-alpha", milestone_id="ms-alpha", contribution_weight=1.0)],
    )
    eff_alpha = EffectDTO(
        id="eff-alpha",
        name="Alpha Spatial Surveillance Effect",
        description="Provides persistent imagery",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-alpha",
        accumulator=AccumulatorPattern.SUM,
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-theater-surveillance", weight=0.75, confidence=1.0)],
    )

    # 2. Candidate Beta: Mid-cost comms bus ($30,000,000)
    ms_beta = MilestoneDTO(
        id="ms-beta",
        thing_id="th-beta",
        sequence_index=0,
        name="Beta Comms Bus Delivery",
        description="Anti-jam antenna assembly",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Comms",
        trl=7,
    )
    th_beta = ThingDTO(
        id="th-beta",
        name="Beta Tactical Mesh Node",
        description="Dedicated anti-jam comms satellite",
        lifecycle=LifecycleStatus.PROPOSED,
        owner_org_id="org-aerospace-acquisitions",
        estimated_cost=30000000.0,
        risk_factor=1.1,
        milestones=[ms_beta],
    )
    gate_beta = CausalGateDTO(
        id="gate-beta",
        name="Beta Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-beta", milestone_id="ms-beta", contribution_weight=1.0)],
    )
    eff_beta = EffectDTO(
        id="eff-beta",
        name="Beta Tactical Comms Effect",
        description="Provides anti-jam tactical crosslinks",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-beta",
        accumulator=AccumulatorPattern.SUM,
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-mesh-comms", weight=0.85, confidence=1.0)],
    )

    # 3. Candidate Gamma: Highly efficient dual-mission system ($40,000,000)
    ms_gamma = MilestoneDTO(
        id="ms-gamma",
        thing_id="th-gamma",
        sequence_index=0,
        name="Gamma Integrated Payload",
        description="Dual sensor-crosslink integration",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 25),
        status=MilestoneStatus.ACHIEVED,
        lane="Multi-Mission",
        trl=8,
    )
    th_gamma = ThingDTO(
        id="th-gamma",
        name="Gamma Integrated ISR/Comms Platform",
        description="Combined surveillance and mesh routing platform",
        lifecycle=LifecycleStatus.PROPOSED,
        owner_org_id="org-aerospace-acquisitions",
        estimated_cost=40000000.0,
        risk_factor=1.0,
        milestones=[ms_gamma],
    )
    gate_gamma = CausalGateDTO(
        id="gate-gamma",
        name="Gamma Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-gamma", milestone_id="ms-gamma", contribution_weight=1.0)],
    )
    eff_gamma = EffectDTO(
        id="eff-gamma",
        name="Gamma Multi-Domain Effect",
        description="Satisfies both surveillance and communications",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-gamma",
        accumulator=AccumulatorPattern.SUM,
        satisfies_concerns=[
            ConcernSatisfactionLinkDTO(concern_id="con-theater-surveillance", weight=0.90, confidence=1.0),
            ConcernSatisfactionLinkDTO(concern_id="con-mesh-comms", weight=0.90, confidence=1.0),
        ],
    )

    # 4. Candidate Delta: Suboptimal bloated architecture ($55,000,000)
    # Expensive with negligible yield, strictly dominated by Gamma and Alpha+Beta
    ms_delta = MilestoneDTO(
        id="ms-delta",
        thing_id="th-delta",
        sequence_index=0,
        name="Delta Legacy Article",
        description="Legacy hardware spin",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 28),
        status=MilestoneStatus.ACHIEVED,
        lane="Legacy",
        trl=5,
    )
    th_delta = ThingDTO(
        id="th-delta",
        name="Delta Bloated Prototype",
        description="High-cost prototype with minimal capability yield",
        lifecycle=LifecycleStatus.PROPOSED,
        owner_org_id="org-aerospace-acquisitions",
        estimated_cost=55000000.0,
        risk_factor=1.8,
        milestones=[ms_delta],
    )
    gate_delta = CausalGateDTO(
        id="gate-delta",
        name="Delta Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-delta", milestone_id="ms-delta", contribution_weight=1.0)],
    )
    eff_delta = EffectDTO(
        id="eff-delta",
        name="Delta Marginal Effect",
        description="Provides marginal sensor resolution",
        tier=EffectTier.TIER_2_OPERATIONAL,
        causal_gate_id="gate-delta",
        accumulator=AccumulatorPattern.SUM,
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-theater-surveillance", weight=0.08, confidence=1.0)],
    )

    # 5. Candidate Epsilon: Massive program breaching the budget ceiling ($120,000,000)
    ms_epsilon = MilestoneDTO(
        id="ms-epsilon",
        thing_id="th-epsilon",
        sequence_index=0,
        name="Epsilon Constellation Lead Ship",
        description="Flagship mega-platform",
        target_date=date(2026, 12, 1),
        actual_date=date(2026, 11, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Flagship",
        trl=7,
    )
    th_epsilon = ThingDTO(
        id="th-epsilon",
        name="Epsilon Deep-Space Constellation",
        description="Extremely costly flagship architecture",
        lifecycle=LifecycleStatus.PROPOSED,
        owner_org_id="org-aerospace-acquisitions",
        estimated_cost=120000000.0,
        risk_factor=1.2,
        milestones=[ms_epsilon],
    )
    gate_epsilon = CausalGateDTO(
        id="gate-epsilon",
        name="Epsilon Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-epsilon", milestone_id="ms-epsilon", contribution_weight=1.0)],
    )
    eff_epsilon = EffectDTO(
        id="eff-epsilon",
        name="Epsilon Comprehensive Effect",
        description="High capability yield at massive cost",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-epsilon",
        accumulator=AccumulatorPattern.SUM,
        satisfies_concerns=[
            ConcernSatisfactionLinkDTO(concern_id="con-theater-surveillance", weight=1.0, confidence=1.0),
            ConcernSatisfactionLinkDTO(concern_id="con-mesh-comms", weight=1.0, confidence=1.0),
        ],
    )

    manifest = BijouManifestDTO(
        organizations=[org],
        concerns=[con_surveillance, con_comms],
        things=[th_alpha, th_beta, th_gamma, th_delta, th_epsilon],
        causal_gates=[gate_alpha, gate_beta, gate_gamma, gate_delta, gate_epsilon],
        effects=[eff_alpha, eff_beta, eff_gamma, eff_delta, eff_epsilon],
        edges=[],
    )

    engine = InMemoryGraphProjectionEngine(manifest)

    # Evaluate Pareto frontier with a strict $60M budget ceiling
    budget_ceiling = 60000000.0
    frontier = engine.evaluate_pareto_frontier(budget_ceiling=budget_ceiling, as_of_date=date(2026, 6, 1))

    # Assert budget ceiling contract
    assert frontier.budget_ceiling == budget_ceiling
    assert len(frontier.optimal_portfolios) > 0

    # Assert strict budget compliance across all optimal candidates
    for portfolio in frontier.optimal_portfolios:
        assert portfolio.total_cost <= budget_ceiling, f"Portfolio exceeded budget ceiling: {portfolio.total_cost}"
        # Assert Candidate Epsilon ($120M) is completely excluded
        assert "th-epsilon" not in portfolio.proposed_thing_ids

    # Assert Delta alone ($55M, low yield) is dominated and rejected from the frontier
    assert not any(
        portfolio.proposed_thing_ids == ["th-delta"]
        for portfolio in frontier.optimal_portfolios
    ), "Suboptimal candidate Delta was not rejected from Pareto frontier!"

    # Assert Gamma ($40M, high yield) is present on the frontier
    gamma_portfolio = next(
        (p for p in frontier.optimal_portfolios if "th-gamma" in p.proposed_thing_ids),
        None,
    )
    assert gamma_portfolio is not None
    assert gamma_portfolio.aggregate_roi > 0.0

    # Assert non-domination property holds for all returned portfolios
    for i, p1 in enumerate(frontier.optimal_portfolios):
        for j, p2 in enumerate(frontier.optimal_portfolios):
            if i != j:
                is_strictly_dominated = (
                    p2.total_cost <= p1.total_cost
                    and p2.aggregate_roi >= p1.aggregate_roi
                    and (p2.total_cost < p1.total_cost or p2.aggregate_roi > p1.aggregate_roi)
                )
                assert not is_strictly_dominated, f"Portfolio {p1} is dominated by {p2}!"


def test_manifest_linter_detects_isolated_orphans_and_cycles() -> None:
    """Provide a manifest with a 4-node cycle and 2 orphaned nodes, asserting exact cycle paths in blockers and orphans in warnings."""
    # 4 Nodes in a circular dependency loop: C1 -> C2 -> C3 -> C4 -> C1
    th_c1 = ThingDTO(id="th-c1", name="Loop Node 1", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=1000000.0, risk_factor=1.0)
    th_c2 = ThingDTO(id="th-c2", name="Loop Node 2", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=1000000.0, risk_factor=1.0)
    th_c3 = ThingDTO(id="th-c3", name="Loop Node 3", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=1000000.0, risk_factor=1.0)
    th_c4 = ThingDTO(id="th-c4", name="Loop Node 4", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=1000000.0, risk_factor=1.0)

    cycle_edges = [
        GraphEdgeDTO(id="e-c1-c2", source_id="th-c1", target_id="th-c2", relationship=RelationshipType.DEPENDS_ON),
        GraphEdgeDTO(id="e-c2-c3", source_id="th-c2", target_id="th-c3", relationship=RelationshipType.DEPENDS_ON),
        GraphEdgeDTO(id="e-c3-c4", source_id="th-c3", target_id="th-c4", relationship=RelationshipType.DEPENDS_ON),
        GraphEdgeDTO(id="e-c4-c1", source_id="th-c4", target_id="th-c1", relationship=RelationshipType.DEPENDS_ON),
    ]

    # 2 Completely isolated orphan nodes (degree == 0)
    th_orphan_a = ThingDTO(id="th-orphan-a", name="Orphan Alpha", description="", lifecycle=LifecycleStatus.PROPOSED, owner_org_id="org1", estimated_cost=5000000.0, risk_factor=1.0)
    th_orphan_b = ThingDTO(id="th-orphan-b", name="Orphan Beta", description="", lifecycle=LifecycleStatus.PROPOSED, owner_org_id="org1", estimated_cost=7500000.0, risk_factor=1.0)

    # 2 Connected non-orphan nodes
    th_valid_src = ThingDTO(id="th-valid-src", name="Valid Source", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=2000000.0, risk_factor=1.0)
    th_valid_dst = ThingDTO(id="th-valid-dst", name="Valid Target", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="org1", estimated_cost=3000000.0, risk_factor=1.0)
    valid_edge = GraphEdgeDTO(id="e-valid", source_id="th-valid-src", target_id="th-valid-dst", relationship=RelationshipType.SUPPORTS)

    manifest = BijouManifestDTO(
        things=[th_c1, th_c2, th_c3, th_c4, th_orphan_a, th_orphan_b, th_valid_src, th_valid_dst],
        edges=[*cycle_edges, valid_edge],
    )

    engine = InMemoryGraphProjectionEngine(manifest)
    diagnostics = engine.validate_manifest_diagnostics(manifest)

    # Assert cycle detection in blockers and cycles_detected
    assert len(diagnostics.cycles_detected) >= 1
    found_cycle = diagnostics.cycles_detected[0]
    for cycle_node in ["th-c1", "th-c2", "th-c3", "th-c4"]:
        assert cycle_node in found_cycle

    assert len(diagnostics.blockers) >= 1
    assert any("th-c1" in b and "th-c2" in b for b in diagnostics.blockers)

    # Assert orphan warnings identify the two isolated nodes
    assert any("th-orphan-a" in w for w in diagnostics.warnings)
    assert any("th-orphan-b" in w for w in diagnostics.warnings)

    # Assert connected nodes are not falsely reported as orphans
    assert not any("th-valid-src" in w for w in diagnostics.warnings)
    assert not any("th-c1" in w for w in diagnostics.warnings)
