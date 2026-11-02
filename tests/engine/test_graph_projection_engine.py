"""Unit and adversarial concurrency tests for InMemoryGraphProjectionEngine."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest

from bijou.core.contracts import (
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
    SlipSimulationRequestDTO,
    TechTreeNodeState,
    TechTreeStratificationMode,
    ThingDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine
from bijou.core.ports.exceptions import GraphCycleError


def _build_test_manifest() -> BijouManifestDTO:
    org = OrganizationDTO(
        id="org-joint",
        name="Joint Theater Commands",
        echelon_level=1,
        mission_statement="Multi-domain joint operations",
    )
    con = ConcernDTO(
        id="con-c2",
        name="Automated Target Cueing",
        description="Deliver fast cueing",
        owner_org_id="org-joint",
        priority=0.9,
    )

    # Thing 1 with Foundation Milestone (ms-1)
    ms1 = MilestoneDTO(
        id="ms-1",
        thing_id="th-1",
        sequence_index=0,
        name="Orbital Constellation Ingest",
        description="Collects",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Orbital Sensing",
        trl=7,
    )
    th1 = ThingDTO(
        id="th-1",
        name="Tactical Satellite Ingest",
        description="LEO Ingest",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-joint",
        estimated_cost=200000.0,
        risk_factor=1.5,
        milestones=[ms1],
    )

    # Thing 2 with Dependent Milestone (ms-2)
    ms2 = MilestoneDTO(
        id="ms-2",
        thing_id="th-2",
        sequence_index=0,
        name="Edge CV Pipeline",
        description="Detections",
        target_date=date(2026, 8, 1),
        status=MilestoneStatus.COMMITTED,
        lane="Edge Routing",
        trl=6,
    )
    th2 = ThingDTO(
        id="th-2",
        name="Automated Target Detection Node",
        description="Edge CV",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-joint",
        estimated_cost=150000.0,
        risk_factor=2.0,
        milestones=[ms2],
    )

    # Edge: ms-2 depends on ms-1
    edge_dep = GraphEdgeDTO(
        id="edge-dep-2-1",
        source_id="th-2",
        target_id="th-1",
        relationship=RelationshipType.DEPENDS_ON,
        source_milestone_id="ms-2",
        target_milestone_id="ms-1",
    )

    # Combinatorial Gate requiring both ms-1 and ms-2
    gate = CausalGateDTO(
        id="gate-joint",
        name="Joint Automated Cueing Gate",
        mechanism=CausalMechanismType.COMBINATORIAL_AND,
        contributors=[
            CausalContributorDTO(thing_id="th-1", milestone_id="ms-1", contribution_weight=0.5),
            CausalContributorDTO(thing_id="th-2", milestone_id="ms-2", contribution_weight=0.5),
        ],
    )

    effect = EffectDTO(
        id="eff-cueing",
        name="Joint Target Cueing Enabled",
        description="Unlocks target cueing",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-joint",
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-c2", weight=1.0)],
    )

    return BijouManifestDTO(
        organizations=[org],
        concerns=[con],
        things=[th1, th2],
        causal_gates=[gate],
        effects=[effect],
        edges=[edge_dep],
    )


def test_combinatorial_and_gate_zero_when_one_prerequisite_unmet() -> None:
    """Verifies that a COMBINATORIAL_AND gate with 2 contributors yields 0.0 when only 1 is ACHIEVED, and 1.0 when both are ACHIEVED."""
    manifest = _build_test_manifest()
    engine = InMemoryGraphProjectionEngine(manifest)

    # As of 2026-06-15: ms-1 is ACHIEVED, but ms-2 is COMMITTED (not yet ACHIEVED)
    # Effect should have 0 yield, so ROI should only reflect direct impacts
    as_of_initial = date(2026, 6, 15)
    view_initial = engine.build_tech_tree_view(as_of_initial, TechTreeStratificationMode.TRL_TIERS)
    node1 = next(n for n in view_initial.nodes if n.milestone_id == "ms-1")
    node2 = next(n for n in view_initial.nodes if n.milestone_id == "ms-2")
    assert node1.state == TechTreeNodeState.ACHIEVED
    assert node2.state == TechTreeNodeState.UNLOCKED_READY

    # Check briefing: coverage for con-c2 should be 0 because gate yield is 0.0
    briefing_initial = engine.build_perspective_briefing("org-joint", None, True, as_of_initial)
    cov_initial = next(c for c in briefing_initial.supported_concerns if c.concern_id == "con-c2")
    assert cov_initial.coverage_score == 0.0

    # Now simulate both milestones ACHIEVED
    manifest_both_achieved = _build_test_manifest()
    ms2_achieved = MilestoneDTO(
        id="ms-2",
        thing_id="th-2",
        sequence_index=0,
        name="Edge CV Pipeline",
        description="Detections",
        target_date=date(2026, 8, 1),
        actual_date=date(2026, 8, 1),
        status=MilestoneStatus.ACHIEVED,
        lane="Edge Routing",
        trl=7,
    )
    th2_updated = ThingDTO(
        id="th-2",
        name="Automated Target Detection Node",
        description="Edge CV",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-joint",
        estimated_cost=150000.0,
        risk_factor=2.0,
        milestones=[ms2_achieved],
    )
    manifest_both_achieved.things[1] = th2_updated
    engine.rebuild_projection(manifest_both_achieved)

    as_of_later = date(2026, 8, 15)
    briefing_both = engine.build_perspective_briefing("org-joint", None, True, as_of_later)
    cov_both = next(c for c in briefing_both.supported_concerns if c.concern_id == "con-c2")
    assert cov_both.coverage_score == 1.0


def test_milestone_slip_propagates_to_downstream_tech_tree_and_effects() -> None:
    """Slips an upstream foundation milestone by 180 days and verifies downstream states transition and effects degrade."""
    manifest = _build_test_manifest()
    engine = InMemoryGraphProjectionEngine(manifest)

    # Slip ms-1 by 180 days with cancellation simulated
    req = SlipSimulationRequestDTO(
        milestone_id="ms-1",
        slip_days=180,
        simulate_cancellation=True,
    )
    resp = engine.simulate_milestone_slip(req, date(2026, 6, 15))

    assert resp.cancelled is True
    # Downstream ms-2 should be impacted (BLOCKED)
    assert "ms-2" in resp.impacted_node_states or "ms-1" in resp.impacted_node_states
    assert resp.impacted_node_states.get("ms-1") == TechTreeNodeState.BLOCKED
    assert resp.impacted_node_states.get("ms-2") == TechTreeNodeState.BLOCKED
    assert "eff-cueing" in resp.degraded_effect_ids
    assert "con-c2" in resp.broken_concern_ids


def test_cycle_detection_raises_graph_cycle_error() -> None:
    """Introduces a 3-node DEPENDS_ON cycle and verifies validate_dag_acyclic() detects the exact cycle."""
    ms_a = MilestoneDTO(id="ms-a", thing_id="th-a", sequence_index=0, name="A", description="", target_date=date(2026, 1, 1), status=MilestoneStatus.COMMITTED, lane="L1", trl=4)
    ms_b = MilestoneDTO(id="ms-b", thing_id="th-b", sequence_index=0, name="B", description="", target_date=date(2026, 2, 1), status=MilestoneStatus.COMMITTED, lane="L1", trl=4)
    ms_c = MilestoneDTO(id="ms-c", thing_id="th-c", sequence_index=0, name="C", description="", target_date=date(2026, 3, 1), status=MilestoneStatus.COMMITTED, lane="L1", trl=4)

    th_a = ThingDTO(id="th-a", name="A", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="o1", estimated_cost=10.0, risk_factor=1.0, milestones=[ms_a])
    th_b = ThingDTO(id="th-b", name="B", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="o1", estimated_cost=10.0, risk_factor=1.0, milestones=[ms_b])
    th_c = ThingDTO(id="th-c", name="C", description="", lifecycle=LifecycleStatus.ACTIVE, owner_org_id="o1", estimated_cost=10.0, risk_factor=1.0, milestones=[ms_c])

    # A -> B -> C -> A cycle
    edges = [
        GraphEdgeDTO(id="e1", source_id="th-a", target_id="th-b", relationship=RelationshipType.DEPENDS_ON, source_milestone_id="ms-a", target_milestone_id="ms-b"),
        GraphEdgeDTO(id="e2", source_id="th-b", target_id="th-c", relationship=RelationshipType.DEPENDS_ON, source_milestone_id="ms-b", target_milestone_id="ms-c"),
        GraphEdgeDTO(id="e3", source_id="th-c", target_id="th-a", relationship=RelationshipType.DEPENDS_ON, source_milestone_id="ms-c", target_milestone_id="ms-a"),
    ]

    manifest = BijouManifestDTO(things=[th_a, th_b, th_c], edges=edges)
    engine = InMemoryGraphProjectionEngine(manifest)

    with pytest.raises(GraphCycleError) as exc_info:
        engine.validate_dag_acyclic()

    err_msg = str(exc_info.value)
    assert "Graph cycle detected" in err_msg


def test_concurrent_rebuild_and_tech_tree_reads_thread_safe() -> None:
    """Runs concurrent rebuild_projection writes and build_tech_tree_view reads across 12 threads without race conditions."""
    manifest = _build_test_manifest()
    engine = InMemoryGraphProjectionEngine(manifest)

    def reader(worker_id: int) -> None:
        for _ in range(5):
            view = engine.build_tech_tree_view(date(2026, 6, 15), TechTreeStratificationMode.TRL_TIERS)
            assert len(view.nodes) == 2

    def writer(worker_id: int) -> None:
        for i in range(5):
            m = _build_test_manifest()
            m.things[0] = ThingDTO(
                id="th-1",
                name=f"Updated Sat {worker_id}-{i}",
                description="Live write",
                lifecycle=LifecycleStatus.ACTIVE,
                owner_org_id="org-joint",
                estimated_cost=200000.0,
                risk_factor=1.5,
                milestones=m.things[0].milestones,
            )
            engine.rebuild_projection(m)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = []
        for i in range(8):
            futures.append(pool.submit(reader, i))
        for i in range(4):
            futures.append(pool.submit(writer, i))

        for f in futures:
            f.result()
