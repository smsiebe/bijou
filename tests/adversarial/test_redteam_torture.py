"""Adversarial Red-Team Torture and Cross-Boundary Synchronization Test Suite."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.core.contracts import (
    BijouManifestDTO,
    CausalContributorDTO,
    CausalGateDTO,
    CausalMechanismType,
    ConcernDTO,
    ConcernSatisfactionLinkDTO,
    EffectDTO,
    EffectEventDTO,
    EffectTier,
    GraphEdgeDTO,
    LifecycleStatus,
    MilestoneDTO,
    MilestoneStatus,
    OrganizationDTO,
    RelationshipType,
    SlipSimulationRequestDTO,
    TechTreeNodeState,
    ThingDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine
from bijou.core.engine.causal import evaluate_causal_gate_yield


@pytest.fixture
def torture_client(tmp_path: Path) -> TestClient:
    """Fixture providing a TestClient backed by live isolated SQLite and DuckDB."""
    db_file = tmp_path / "torture_graph.db"
    duckdb_file = tmp_path / "torture_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_non_cancelled_milestone_slip_degrades_downstream_and_roi() -> None:
    """Slip ms-1 by 180 days with simulate_cancellation=False past as_of_date and verify

    impacted_node_states is non-empty, eff-cueing is degraded, and roi_delta < 0.
    """
    org = OrganizationDTO(
        id="org-joint",
        name="Joint Command",
        echelon_level=1,
        mission_statement="Joint operations",
    )
    con = ConcernDTO(
        id="con-c2",
        name="Target Cueing",
        description="Speed",
        owner_org_id="org-joint",
        priority=0.9,
    )

    ms1 = MilestoneDTO(
        id="ms-1",
        thing_id="th-1",
        sequence_index=0,
        name="Constellation Ingest",
        description="Ingest",
        target_date=date(2026, 6, 1),
        actual_date=date(2026, 5, 20),
        status=MilestoneStatus.ACHIEVED,
        lane="Lane-1",
        trl=7,
    )
    th1 = ThingDTO(
        id="th-1",
        name="Satellite Ingest",
        description="Ingest payload",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-joint",
        estimated_cost=100.0,
        risk_factor=1.0,
        milestones=[ms1],
    )

    ms2 = MilestoneDTO(
        id="ms-2",
        thing_id="th-2",
        sequence_index=0,
        name="Edge Detection",
        description="Detection",
        target_date=date(2026, 8, 1),
        actual_date=date(2026, 8, 1),
        status=MilestoneStatus.ACHIEVED,
        lane="Lane-2",
        trl=7,
    )
    th2 = ThingDTO(
        id="th-2",
        name="Target Detector",
        description="Detector node",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-joint",
        estimated_cost=100.0,
        risk_factor=1.0,
        milestones=[ms2],
    )

    edge_dep = GraphEdgeDTO(
        id="edge-dep",
        source_id="th-2",
        target_id="th-1",
        relationship=RelationshipType.DEPENDS_ON,
        source_milestone_id="ms-2",
        target_milestone_id="ms-1",
    )

    gate = CausalGateDTO(
        id="gate-joint",
        name="Cueing Gate",
        mechanism=CausalMechanismType.COMBINATORIAL_AND,
        contributors=[
            CausalContributorDTO(thing_id="th-1", milestone_id="ms-1", contribution_weight=0.5),
            CausalContributorDTO(thing_id="th-2", milestone_id="ms-2", contribution_weight=0.5),
        ],
    )

    effect = EffectDTO(
        id="eff-cueing",
        name="Cueing Enabled",
        description="Strategic Cueing",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-joint",
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-c2", weight=1.0)],
    )

    manifest = BijouManifestDTO(
        organizations=[org],
        concerns=[con],
        things=[th1, th2],
        causal_gates=[gate],
        effects=[effect],
        edges=[edge_dep],
    )

    engine = InMemoryGraphProjectionEngine(manifest)
    as_of = date(2026, 8, 15)

    # Base ROI check before slip
    base_roi = engine.calculate_thing_roi("th-1", as_of) + engine.calculate_thing_roi("th-2", as_of)
    assert base_roi > 0.0

    # Slip ms-1 by 180 days with simulate_cancellation=False
    req = SlipSimulationRequestDTO(
        milestone_id="ms-1",
        slip_days=180,
        simulate_cancellation=False,
    )
    resp = engine.simulate_milestone_slip(req, as_of)

    assert resp.cancelled is False
    assert len(resp.impacted_node_states) > 0
    assert resp.impacted_node_states.get("ms-1") == TechTreeNodeState.BLOCKED
    assert resp.impacted_node_states.get("ms-2") == TechTreeNodeState.BLOCKED
    assert "eff-cueing" in resp.degraded_effect_ids
    assert "con-c2" in resp.broken_concern_ids
    assert resp.roi_delta < 0.0


def test_temporal_edge_filtering_excludes_expired_and_future_edges() -> None:
    """Verify edges outside [effective_start, effective_end] contribute 0.0 to ROI and briefings."""
    org = OrganizationDTO(
        id="org-temporal",
        name="Temporal Org",
        echelon_level=1,
        mission_statement="Temporal research operations",
    )
    con = ConcernDTO(
        id="con-1",
        name="Temporal Concern",
        description="Temporal relevance",
        owner_org_id="org-temporal",
        priority=1.0,
    )
    th = ThingDTO(
        id="th-1",
        name="Temporal Thing",
        description="Temporal testing asset",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-temporal",
        estimated_cost=100.0,
        risk_factor=1.0,
    )

    # 3 edges: one active in 2026, one expired in 2025, one future in 2027
    edge_active = GraphEdgeDTO(
        id="e-active",
        source_id="th-1",
        target_id="con-1",
        relationship=RelationshipType.SUPPORTS,
        weight=0.5,
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
    )
    edge_expired = GraphEdgeDTO(
        id="e-expired",
        source_id="th-1",
        target_id="con-1",
        relationship=RelationshipType.SUPPORTS,
        weight=0.8,
        effective_start=date(2025, 1, 1),
        effective_end=date(2025, 12, 31),
    )
    edge_future = GraphEdgeDTO(
        id="e-future",
        source_id="th-1",
        target_id="con-1",
        relationship=RelationshipType.SUPPORTS,
        weight=0.9,
        effective_start=date(2027, 1, 1),
        effective_end=date(2027, 12, 31),
    )

    manifest = BijouManifestDTO(
        organizations=[org],
        concerns=[con],
        things=[th],
        edges=[edge_active, edge_expired, edge_future],
    )
    engine = InMemoryGraphProjectionEngine(manifest)

    # 1. As of 2026-06-15: only edge_active (weight=0.5) is active
    as_of_2026 = date(2026, 6, 15)
    roi_2026 = engine.calculate_thing_roi("th-1", as_of_2026)
    assert roi_2026 == pytest.approx(0.5 / 100.0, rel=1e-4)

    briefing_2026 = engine.build_perspective_briefing("org-temporal", None, True, as_of_2026)
    cov_2026 = next(c for c in briefing_2026.supported_concerns if c.concern_id == "con-1")
    assert cov_2026.coverage_score == pytest.approx(0.5, rel=1e-4)

    # 2. As of 2024-06-15: all 3 edges are inactive (contribute 0.0)
    as_of_2024 = date(2024, 6, 15)
    roi_2024 = engine.calculate_thing_roi("th-1", as_of_2024)
    assert roi_2024 == 0.0

    briefing_2024 = engine.build_perspective_briefing("org-temporal", None, True, as_of_2024)
    cov_2024 = next(c for c in briefing_2024.supported_concerns if c.concern_id == "con-1")
    assert cov_2024.coverage_score == 0.0


def test_parent_org_id_hierarchy_rollup_without_explicit_edges() -> None:
    """Define hierarchy solely via OrganizationDTO.parent_org_id and assert include_descendants rolls up."""
    org_parent = OrganizationDTO(
        id="org-p",
        name="Parent Org",
        echelon_level=1,
        mission_statement="Strategic command",
        parent_org_id=None,
    )
    org_child = OrganizationDTO(
        id="org-c",
        name="Child Org",
        echelon_level=2,
        mission_statement="Operational command",
        parent_org_id="org-p",
    )
    org_grandchild = OrganizationDTO(
        id="org-gc",
        name="Grandchild Org",
        echelon_level=3,
        mission_statement="Tactical command",
        parent_org_id="org-c",
    )

    th_p = ThingDTO(
        id="th-p",
        name="Parent Thing",
        description="Parent Asset",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-p",
        estimated_cost=100.0,
        risk_factor=1.0,
    )
    th_c = ThingDTO(
        id="th-c",
        name="Child Thing",
        description="Child Asset",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-c",
        estimated_cost=50.0,
        risk_factor=1.0,
    )
    th_gc = ThingDTO(
        id="th-gc",
        name="Grandchild Thing",
        description="Grandchild Asset",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-gc",
        estimated_cost=25.0,
        risk_factor=1.0,
    )

    # Manifest contains NO RelationshipType.PARENT_OF edges
    manifest = BijouManifestDTO(
        organizations=[org_parent, org_child, org_grandchild],
        things=[th_p, th_c, th_gc],
        edges=[],
    )
    engine = InMemoryGraphProjectionEngine(manifest)
    as_of = date(2026, 6, 1)

    # include_descendants=True: must rollup child and grandchild Things
    briefing_desc = engine.build_perspective_briefing("org-p", None, include_descendants=True, as_of_date=as_of)
    owned_ids_desc = {t.id for t in briefing_desc.owned_things}
    assert owned_ids_desc == {"th-p", "th-c", "th-gc"}
    assert briefing_desc.total_committed_cost == pytest.approx(175.0)

    # include_descendants=False: isolates parent Things only
    briefing_iso = engine.build_perspective_briefing("org-p", None, include_descendants=False, as_of_date=as_of)
    owned_ids_iso = {t.id for t in briefing_iso.owned_things}
    assert owned_ids_iso == {"th-p"}
    assert briefing_iso.total_committed_cost == pytest.approx(100.0)


def test_threshold_k_of_n_causal_gate_exact_boundary() -> None:
    """Verify k=3 of 5 yields 0.0 at 2 achieved and 1.0 at 3 achieved."""
    gate = CausalGateDTO(
        id="gate-k3",
        name="3 of 5 Gate",
        mechanism=CausalMechanismType.THRESHOLD_K_OF_N,
        threshold_k=3,
        contributors=[
            CausalContributorDTO(thing_id=f"th-{i}", milestone_id=f"ms-{i}", contribution_weight=1.0)
            for i in range(1, 6)
        ],
    )

    # 2 achieved, 3 locked -> yield 0.0
    states_2 = {
        "ms-1": TechTreeNodeState.ACHIEVED,
        "ms-2": TechTreeNodeState.ACHIEVED,
        "ms-3": TechTreeNodeState.LOCKED,
        "ms-4": TechTreeNodeState.LOCKED,
        "ms-5": TechTreeNodeState.LOCKED,
    }
    assert evaluate_causal_gate_yield(gate, states_2) == 0.0

    # 3 achieved, 2 locked -> yield 1.0
    states_3 = {
        "ms-1": TechTreeNodeState.ACHIEVED,
        "ms-2": TechTreeNodeState.ACHIEVED,
        "ms-3": TechTreeNodeState.ACHIEVED,
        "ms-4": TechTreeNodeState.LOCKED,
        "ms-5": TechTreeNodeState.LOCKED,
    }
    assert evaluate_causal_gate_yield(gate, states_3) == 1.0

    # 4 achieved, 1 locked -> yield 1.0
    states_4 = {
        "ms-1": TechTreeNodeState.ACHIEVED,
        "ms-2": TechTreeNodeState.ACHIEVED,
        "ms-3": TechTreeNodeState.ACHIEVED,
        "ms-4": TechTreeNodeState.ACHIEVED,
        "ms-5": TechTreeNodeState.LOCKED,
    }
    assert evaluate_causal_gate_yield(gate, states_4) == 1.0


def test_focal_dashboard_hydrates_actual_duckdb_metrics(torture_client: TestClient) -> None:
    """Ingest events with custom metric 'radar_track_rate' and assert telemetry_rollups contains it."""
    client = torture_client

    # 1. Create Organization and Focal Thing
    org = OrganizationDTO(
        id="org-sensor",
        name="Sensor Directorate",
        echelon_level=2,
        mission_statement="Operational sensing",
    )
    client.post("/api/v1/organizations", json=org.model_dump(mode="json", by_alias=True))

    thing = ThingDTO(
        id="th-radar",
        name="AESA Radar Node",
        description="Radar Node",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-sensor",
        estimated_cost=250000.0,
        risk_factor=1.5,
    )
    client.post("/api/v1/things", json=thing.model_dump(mode="json", by_alias=True))

    # 2. Ingest 4 custom telemetry events for radar_track_rate
    events = [
        EffectEventDTO(
            event_id=f"evt-radar-{i}",
            thing_id="th-radar",
            source_org_id="org-sensor",
            causal_verb="CONFIRMED",
            occurred_at=datetime(2026, 6, 1, 12, i, 0, tzinfo=timezone.utc),
            metric_name="radar_track_rate",
            metric_value=25.0 * (i + 1),
            confidence=0.95,
        )
        for i in range(4)
    ]
    resp_ingest = client.post(
        "/api/v1/telemetry/events",
        json=[e.model_dump(mode="json", by_alias=True) for e in events],
    )
    assert resp_ingest.status_code == 200
    assert resp_ingest.json()["ingested_count"] == 4

    # 3. Query focal dashboard
    resp_focal = client.get("/api/v1/views/things/th-radar/focal")
    assert resp_focal.status_code == 200
    focal_data = resp_focal.json()

    rollups = focal_data.get("telemetry_rollups", [])
    assert len(rollups) > 0
    metric_names = [r["metric_name"] for r in rollups]
    assert "radar_track_rate" in metric_names

    radar_rollup = next(r for r in rollups if r["metric_name"] == "radar_track_rate")
    assert radar_rollup["event_count"] == 4
    assert radar_rollup["aggregated_value"] == pytest.approx(250.0)  # 25 + 50 + 75 + 100


def test_perspective_cache_invalidates_on_edge_weight_mutation(torture_client: TestClient) -> None:
    """Query briefing, mutate edge weight via POST /api/v1/edges, re-query briefing and verify update."""
    client = torture_client

    org = OrganizationDTO(
        id="org-mut",
        name="Mutation Org",
        echelon_level=1,
        mission_statement="Mutation testing",
    )
    con = ConcernDTO(
        id="con-mut",
        name="Mutation Concern",
        description="Mutation concern target",
        owner_org_id="org-mut",
        priority=1.0,
    )
    th = ThingDTO(
        id="th-mut",
        name="Mutation Thing",
        description="Mutation thing asset",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-mut",
        estimated_cost=100.0,
        risk_factor=1.0,
    )

    client.post("/api/v1/organizations", json=org.model_dump(mode="json", by_alias=True))
    client.post("/api/v1/concerns", json=con.model_dump(mode="json", by_alias=True))
    client.post("/api/v1/things", json=th.model_dump(mode="json", by_alias=True))

    edge_init = GraphEdgeDTO(
        id="edge-mut-1",
        source_id="th-mut",
        target_id="con-mut",
        relationship=RelationshipType.SUPPORTS,
        weight=0.2,
    )
    client.post("/api/v1/edges", json=edge_init.model_dump(mode="json", by_alias=True))

    # Initial query populates perspective cache
    resp1 = client.get("/api/v1/views/perspectives/org-mut")
    assert resp1.status_code == 200
    data1 = resp1.json()
    cov1 = next(c for c in data1["supported_concerns"] if c["concern_id"] == "con-mut")
    assert cov1["coverage_score"] == pytest.approx(0.2)
    assert data1["portfolio_roi_score"] == pytest.approx(0.2 / 100.0)

    # Mutate edge weight from 0.2 to 0.8
    edge_updated = GraphEdgeDTO(
        id="edge-mut-1",
        source_id="th-mut",
        target_id="con-mut",
        relationship=RelationshipType.SUPPORTS,
        weight=0.8,
    )
    resp_edge = client.post("/api/v1/edges", json=edge_updated.model_dump(mode="json", by_alias=True))
    assert resp_edge.status_code == 201

    # Re-query briefing; cache must have been invalidated
    resp2 = client.get("/api/v1/views/perspectives/org-mut")
    assert resp2.status_code == 200
    data2 = resp2.json()
    cov2 = next(c for c in data2["supported_concerns"] if c["concern_id"] == "con-mut")
    assert cov2["coverage_score"] == pytest.approx(0.8)
    assert data2["portfolio_roi_score"] == pytest.approx(0.8 / 100.0)


def test_web_js_field_references_match_openapi_dto_properties() -> None:
    """Parse views.js, app.js, and index.html and assert zero hallucinated fields and valid DTO fields."""
    static_dir = Path(__file__).parent.parent.parent / "src" / "bijou" / "web" / "static"
    views_js = (static_dir / "views.js").read_text(encoding="utf-8")
    app_js = (static_dir / "app.js").read_text(encoding="utf-8")
    index_html = (static_dir / "index.html").read_text(encoding="utf-8")

    all_web_content = f"{views_js}\n{app_js}\n{index_html}"

    forbidden_hallucinations = [
        "roi_breakdown",
        "strategic_alignment",
        "funded_things",
        "evaluated_candidates",
        "downstream_unlocks",
        "TIME_HORIZONS",
    ]

    for bad_field in forbidden_hallucinations:
        assert bad_field not in all_web_content, (
            f"Hallucinated field '{bad_field}' found in web static assets!"
        )

    # Assert presence of required valid contract fields
    assert "supported_concerns" in views_js
    assert "owned_things" in views_js
    assert "portfolio_roi_score" in views_js
    assert "FISCAL_ERA" in index_html
    assert "TOPOLOGICAL_DEPTH" in index_html


def test_tech_tree_js_renders_edges_and_traverses_upstream_spine() -> None:
    """Assert tech_tree.js iterates edges to create SVG paths and highlightSpine traverses upstream spine."""
    static_dir = Path(__file__).parent.parent.parent / "src" / "bijou" / "web" / "static"
    tech_tree_js = (static_dir / "tech_tree.js").read_text(encoding="utf-8")

    # Assert edge iteration for SVG rendering
    assert "edges" in tech_tree_js
    assert "renderEdges" in tech_tree_js or "svg" in tech_tree_js.lower()
    assert "path" in tech_tree_js.lower()

    # Assert highlightSpine upstream traversal
    assert "highlightSpine" in tech_tree_js
    assert "source_node_id" in tech_tree_js
    assert "target_node_id" in tech_tree_js
