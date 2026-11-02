"""Adversarial and red-team torture tests for multi-slip sandboxing, CPM slack, and SPOF centrality."""

from datetime import date, timedelta

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


def test_multi_milestone_slip_sandbox() -> None:
    """Pass 3 simultaneous slips in simulated_slips and assert downstream blast radius combines all delays."""
    org = OrganizationDTO(
        id="org-defense-command",
        name="Joint Strategic Defense Command",
        echelon_level=0,
        mission_statement="Multi-domain theater resilience",
    )
    concern_c2 = ConcernDTO(
        id="con-theater-c2",
        name="Integrated Theater C2 Mesh",
        description="Resilient automated sensor-to-shooter coordination",
        owner_org_id="org-defense-command",
        priority=0.95,
    )
    concern_track = ConcernDTO(
        id="con-track-persistence",
        name="Hypersonic Track Persistence",
        description="Persistent low-latency telemetry tracking",
        owner_org_id="org-defense-command",
        priority=0.88,
    )

    # 3 foundational sensing / comms initiatives
    ms_sensor_a = MilestoneDTO(
        id="ms-sensor-a",
        thing_id="th-sensor-a",
        sequence_index=0,
        name="EO/IR Space Payload Flight Article",
        description="Delivery of focal plane array flight article",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Orbital Payloads",
        trl=6,
    )
    th_sensor_a = ThingDTO(
        id="th-sensor-a",
        name="Space Sensing Constellation Block I",
        description="Wide-field persistent surveillance satellite",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=1500000.0,
        risk_factor=1.2,
        milestones=[ms_sensor_a],
    )

    ms_sensor_b = MilestoneDTO(
        id="ms-sensor-b",
        thing_id="th-sensor-b",
        sequence_index=0,
        name="Radar Array Calibration",
        description="Ground calibration and array phase synchronization",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 25),
        status=MilestoneStatus.ACHIEVED,
        lane="Surface Sensors",
        trl=6,
    )
    th_sensor_b = ThingDTO(
        id="th-sensor-b",
        name="Surface Phased Array Radar",
        description="Early warning tracking array",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=2200000.0,
        risk_factor=1.3,
        milestones=[ms_sensor_b],
    )

    ms_comms_c = MilestoneDTO(
        id="ms-comms-c",
        thing_id="th-comms-c",
        sequence_index=0,
        name="Optical Intersatellite Crosslink",
        description="Laser transceiver hardware signoff",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 28),
        status=MilestoneStatus.ACHIEVED,
        lane="Mesh Communications",
        trl=6,
    )
    th_comms_c = ThingDTO(
        id="th-comms-c",
        name="Optical Mesh Constellation",
        description="Space transport crosslink layer",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=1800000.0,
        risk_factor=1.1,
        milestones=[ms_comms_c],
    )

    # Intermediate fusion node depending on ms-sensor-a and ms-sensor-b
    ms_fusion_d = MilestoneDTO(
        id="ms-fusion-d",
        thing_id="th-fusion-d",
        sequence_index=0,
        name="Automated Track Correlator Flight Binary",
        description="Edge AI kinematic correlator",
        target_date=date(2026, 7, 15),
        actual_date=date(2026, 7, 10),
        status=MilestoneStatus.ACHIEVED,
        lane="Data Fusion",
        trl=6,
    )
    th_fusion_d = ThingDTO(
        id="th-fusion-d",
        name="Kinematic AI Fusion Engine",
        description="Real-time sensor fusion software suite",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=3500000.0,
        risk_factor=1.4,
        milestones=[ms_fusion_d],
    )

    # Intermediate relay node depending on ms-comms-c
    ms_relay_e = MilestoneDTO(
        id="ms-relay-e",
        thing_id="th-relay-e",
        sequence_index=0,
        name="Tactical Ground Entry Gateway",
        description="Downlink modem demodulator installation",
        target_date=date(2026, 7, 1),
        actual_date=date(2026, 6, 25),
        status=MilestoneStatus.ACHIEVED,
        lane="Mesh Communications",
        trl=6,
    )
    th_relay_e = ThingDTO(
        id="th-relay-e",
        name="Tactical Gateway Terminal",
        description="Dispersed gateway receivers",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=2000000.0,
        risk_factor=1.2,
        milestones=[ms_relay_e],
    )

    # Apex terminal milestone ms-c2-f depending on ms-fusion-d and ms-relay-e
    ms_c2_f = MilestoneDTO(
        id="ms-c2-f",
        thing_id="th-c2-f",
        sequence_index=0,
        name="Full Theater Automated Interceptor Cueing",
        description="Integrated live-fire fire-control interface",
        target_date=date(2026, 9, 1),
        actual_date=date(2026, 8, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Command & Control",
        trl=7,
    )
    th_c2_f = ThingDTO(
        id="th-c2-f",
        name="Theater Fire Control Platform",
        description="Mission-critical automated engagement node",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-defense-command",
        estimated_cost=500000.0,
        risk_factor=1.0,
        milestones=[ms_c2_f],
    )

    # Dependency graph edges
    edges = [
        GraphEdgeDTO(
            id="edge-fusion-dep-a",
            source_id="th-fusion-d",
            target_id="th-sensor-a",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-fusion-d",
            target_milestone_id="ms-sensor-a",
        ),
        GraphEdgeDTO(
            id="edge-fusion-dep-b",
            source_id="th-fusion-d",
            target_id="th-sensor-b",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-fusion-d",
            target_milestone_id="ms-sensor-b",
        ),
        GraphEdgeDTO(
            id="edge-relay-dep-c",
            source_id="th-relay-e",
            target_id="th-comms-c",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-relay-e",
            target_milestone_id="ms-comms-c",
        ),
        GraphEdgeDTO(
            id="edge-c2-dep-d",
            source_id="th-c2-f",
            target_id="th-fusion-d",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-c2-f",
            target_milestone_id="ms-fusion-d",
        ),
        GraphEdgeDTO(
            id="edge-c2-dep-e",
            source_id="th-c2-f",
            target_id="th-relay-e",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-c2-f",
            target_milestone_id="ms-relay-e",
        ),
    ]

    gate = CausalGateDTO(
        id="gate-c2-execution",
        name="Automated Defense Cueing Synchronization Gate",
        mechanism=CausalMechanismType.COMBINATORIAL_AND,
        contributors=[
            CausalContributorDTO(thing_id="th-c2-f", milestone_id="ms-c2-f", contribution_weight=1.0),
        ],
    )
    effect = EffectDTO(
        id="eff-theater-cueing",
        name="Operational Theater Cueing Active",
        description="Automated cueing authorized and validated",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-c2-execution",
        satisfies_concerns=[
            ConcernSatisfactionLinkDTO(concern_id="con-theater-c2", weight=1.0),
            ConcernSatisfactionLinkDTO(concern_id="con-track-persistence", weight=0.8),
        ],
    )

    manifest = BijouManifestDTO(
        organizations=[org],
        concerns=[concern_c2, concern_track],
        things=[th_sensor_a, th_sensor_b, th_comms_c, th_fusion_d, th_relay_e, th_c2_f],
        causal_gates=[gate],
        effects=[effect],
        edges=edges,
    )

    engine = InMemoryGraphProjectionEngine(manifest)
    as_of_date = date(2026, 9, 15)

    # Multi-slip sandbox request with 3 simultaneous milestone slips
    sim_request = SlipSimulationRequestDTO(
        simulated_slips={
            "ms-sensor-a": 60,
            "ms-sensor-b": 45,
            "ms-comms-c": 90,
        }
    )

    result = engine.simulate_milestone_slip(sim_request, as_of_date)

    # Assert that downstream blast radius captures all combined delays
    assert len(result.impacted_node_states) >= 3
    # ms-fusion-d was planned for 2026-07-15; ms-sensor-a slipped 60d past it to 2026-07-31 -> BLOCKED
    assert result.impacted_node_states["ms-fusion-d"] == TechTreeNodeState.BLOCKED
    # ms-relay-e was planned for 2026-07-01; ms-comms-c slipped 90d to 2026-08-30 -> BLOCKED
    assert result.impacted_node_states["ms-relay-e"] == TechTreeNodeState.BLOCKED
    # ms-c2-f depends on both and transitions to BLOCKED
    assert result.impacted_node_states["ms-c2-f"] == TechTreeNodeState.BLOCKED

    # Degraded effects & broken strategic concerns
    assert "eff-theater-cueing" in result.degraded_effect_ids
    assert "con-theater-c2" in result.broken_concern_ids
    assert result.roi_delta < 0.0


def test_cpm_slack_days_and_spof_centrality() -> None:
    """Construct a DAG where one node is a strict choke point (SPOF) for 3 downstream effects, and another node has 90 days of slack."""
    org = OrganizationDTO(
        id="org-cpm-spof",
        name="Strategic Architecture Office",
        echelon_level=0,
        mission_statement="Portfolio topological assurance",
    )
    concerns = [
        ConcernDTO(
            id=f"con-eff-{i}",
            name=f"Strategic Objective {i}",
            description=f"Objective {i}",
            owner_org_id="org-cpm-spof",
            priority=0.8,
        )
        for i in range(1, 4)
    ]

    # Source node
    ms_source = MilestoneDTO(
        id="ms-source",
        thing_id="th-source",
        sequence_index=0,
        name="Foundational Kernel Architecture",
        description="Core architecture baseline",
        target_date=date(2026, 3, 1),
        status=MilestoneStatus.COMMITTED,
        lane="Core Systems",
        trl=4,
    )
    th_source = ThingDTO(
        id="th-source",
        name="Core Systems Kernel",
        description="Kernel program",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-cpm-spof",
        estimated_cost=500000.0,
        risk_factor=1.0,
        milestones=[ms_source],
    )

    # Choke point (SPOF) node that bridges source to 3 independent downstream effect paths
    ms_choke = MilestoneDTO(
        id="ms-choke",
        thing_id="th-choke",
        sequence_index=0,
        name="Common Avionics Integration Bus",
        description="Unified inter-service bus bridge",
        target_date=date(2026, 4, 1),
        status=MilestoneStatus.COMMITTED,
        lane="Core Systems",
        trl=5,
    )
    th_choke = ThingDTO(
        id="th-choke",
        name="Common Avionics Platform",
        description="Avionics bus bridge program",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-cpm-spof",
        estimated_cost=1200000.0,
        risk_factor=1.1,
        milestones=[ms_choke],
    )

    # 3 downstream destinations from choke point
    dest_things: list[ThingDTO] = []
    dest_edges: list[GraphEdgeDTO] = [
        GraphEdgeDTO(
            id="edge-src-choke",
            source_id="th-choke",
            target_id="th-source",
            relationship=RelationshipType.DEPENDS_ON,
            source_milestone_id="ms-choke",
            target_milestone_id="ms-source",
        )
    ]
    causal_gates: list[CausalGateDTO] = []
    effects: list[EffectDTO] = []

    for i in range(1, 4):
        ms_dest = MilestoneDTO(
            id=f"ms-dest-{i}",
            thing_id=f"th-dest-{i}",
            sequence_index=0,
            name=f"Operational Capability Endpoint {i}",
            description=f"Endpoint {i}",
            target_date=date(2026, 5, 1),
            status=MilestoneStatus.COMMITTED,
            lane="Endpoints",
            trl=7,
        )
        th_dest = ThingDTO(
            id=f"th-dest-{i}",
            name=f"Endpoint Program {i}",
            description=f"Program {i}",
            lifecycle=LifecycleStatus.ACTIVE,
            owner_org_id="org-cpm-spof",
            estimated_cost=800000.0,
            risk_factor=1.2,
            milestones=[ms_dest],
        )
        dest_things.append(th_dest)
        dest_edges.append(
            GraphEdgeDTO(
                id=f"edge-choke-dest-{i}",
                source_id=f"th-dest-{i}",
                target_id="th-choke",
                relationship=RelationshipType.DEPENDS_ON,
                source_milestone_id=f"ms-dest-{i}",
                target_milestone_id="ms-choke",
            )
        )
        gate_i = CausalGateDTO(
            id=f"gate-{i}",
            name=f"Gate {i}",
            mechanism=CausalMechanismType.ADDITIVE,
            contributors=[
                CausalContributorDTO(thing_id=f"th-dest-{i}", milestone_id=f"ms-dest-{i}", contribution_weight=1.0)
            ],
        )
        causal_gates.append(gate_i)
        eff_i = EffectDTO(
            id=f"eff-{i}",
            name=f"Effect {i}",
            description=f"Effect description {i}",
            tier=EffectTier.TIER_1_STRATEGIC,
            causal_gate_id=f"gate-{i}",
            satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id=f"con-eff-{i}", weight=1.0)],
        )
        effects.append(eff_i)

    # Independent node with exactly 90 days of slack
    # ms-slack target: 2026-03-01; ms-consumer target: 2026-05-30 (March 31d + April 30d + May 29d = 90d)
    ms_slack_date = date(2026, 3, 1)
    ms_consumer_date = ms_slack_date + timedelta(days=90)

    ms_slack = MilestoneDTO(
        id="ms-slack",
        thing_id="th-slack",
        sequence_index=0,
        name="Auxiliary Power Module Prototype",
        description="Buffer power subsystem",
        target_date=ms_slack_date,
        status=MilestoneStatus.COMMITTED,
        lane="Subsystems",
        trl=5,
    )
    th_slack = ThingDTO(
        id="th-slack",
        name="Auxiliary Subsystem Platform",
        description="Power module",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-cpm-spof",
        estimated_cost=300000.0,
        risk_factor=1.0,
        milestones=[ms_slack],
    )

    ms_consumer = MilestoneDTO(
        id="ms-consumer",
        thing_id="th-consumer",
        sequence_index=0,
        name="Subsystem Final Assembly",
        description="Late scheduled integration",
        target_date=ms_consumer_date,
        status=MilestoneStatus.COMMITTED,
        lane="Subsystems",
        trl=6,
    )
    th_consumer = ThingDTO(
        id="th-consumer",
        name="Downstream Subsystem Consumer",
        description="Consumer system",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-cpm-spof",
        estimated_cost=400000.0,
        risk_factor=1.0,
        milestones=[ms_consumer],
    )

    slack_edge = GraphEdgeDTO(
        id="edge-slack-consumer",
        source_id="th-consumer",
        target_id="th-slack",
        relationship=RelationshipType.DEPENDS_ON,
        source_milestone_id="ms-consumer",
        target_milestone_id="ms-slack",
    )

    all_things = [th_source, th_choke, *dest_things, th_slack, th_consumer]
    all_edges = [*dest_edges, slack_edge]

    manifest = BijouManifestDTO(
        organizations=[org],
        concerns=concerns,
        things=all_things,
        causal_gates=causal_gates,
        effects=effects,
        edges=all_edges,
    )

    engine = InMemoryGraphProjectionEngine(manifest)
    view = engine.build_tech_tree_view(date(2026, 2, 1), TechTreeStratificationMode.TRL_TIERS)

    choke_node = next(n for n in view.nodes if n.milestone_id == "ms-choke")
    slack_node = next(n for n in view.nodes if n.milestone_id == "ms-slack")

    # Assert SPOF flag and Centrality on the choke point
    assert choke_node.is_spof is True
    assert choke_node.centrality_score > 0.0

    # Assert CPM Slack of exactly 90 days on the unconstrained predecessor
    assert slack_node.slack_days == 90
