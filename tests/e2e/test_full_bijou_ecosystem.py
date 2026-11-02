"""End-to-End ecosystem integration test suite for Bijou.

Demonstrates full cross-sovereignty dogfooding:
Ingestion -> Storage -> Graph Engine -> Telemetry Federation -> Perspectives -> Analysis -> SDK.
"""

from pathlib import Path

import pytest
from bijou_ingest import ManifestIngestor
from bijou_sdk import BijouClient

from bijou.api.app import create_app
from bijou.config import BijouSettings


@pytest.fixture
def e2e_client(tmp_path: Path):
    """Fixture initializing an ASGI-backed BijouClient with isolated test persistence."""
    db_file = tmp_path / "e2e_graph.db"
    duckdb_file = tmp_path / "e2e_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    test_app = create_app(settings)

    with BijouClient(app=test_app) as client:
        yield client


def test_end_to_end_dogfooding_bijou_ecosystem(e2e_client: BijouClient):
    """Full lifecycle dogfooding of the Bijou Decision-Support Engine."""
    root_dir = Path(__file__).parent.parent.parent
    datasets_dir = root_dir / "datasets"
    yaml_path = datasets_dir / "joint_isr_architecture.yaml"
    jsonl_path = datasets_dir / "satellite_cascade_telemetry.jsonl"

    ingestor = ManifestIngestor(client=e2e_client)

    # 1. Ingest Full Multi-Domain Architecture Manifest
    manifest_res = ingestor.ingest_manifest_file(yaml_path, base_dir=datasets_dir)
    assert manifest_res.get("organizations") == 5
    assert manifest_res.get("concerns") == 5
    assert manifest_res.get("things") == 6
    assert manifest_res.get("causal_gates") == 3
    assert manifest_res.get("effects") == 4
    assert manifest_res.get("edges") == 18

    # 2. Ingest 60 Operational Telemetry Events
    ingested_events = ingestor.ingest_telemetry_file(jsonl_path, base_dir=datasets_dir)
    assert ingested_events == 60

    # 3. Query Tech Tree View
    tree = e2e_client.get_tech_tree()
    assert len(tree.nodes) == 14
    assert len(tree.tiers) == 3

    # 4. Simulate Critical Milestone Slip & Cancellation
    slip = e2e_client.simulate_slip(
        milestone_id="ms-space-flight-qual",
        slip_days=60,
        simulate_cancellation=True,
    )
    assert slip.slipped_milestone_id == "ms-space-flight-qual"
    assert slip.slip_days == 60
    assert slip.cancelled
    assert "ms-space-flight-qual" in slip.impacted_node_states

    # 5. Query Multi-Perspective Briefings across Echelons
    briefing_strat = e2e_client.get_perspective_briefing("org-strat-space")
    assert briefing_strat.subject_org_id == "org-strat-space"
    assert len(briefing_strat.owned_things) >= 2
    assert briefing_strat.portfolio_roi_score > 0.0

    briefing_c2 = e2e_client.get_perspective_briefing("org-c2-joint")
    assert briefing_c2.subject_org_id == "org-c2-joint"
    assert len(briefing_c2.owned_things) >= 1

    # 6. Evaluate Portfolio Tradeoff Analysis
    tradeoff = e2e_client.evaluate_tradeoff(
        [
            "thing-hypersonic-sensor-constellation",
            "thing-tactical-strike-interceptor",
        ]
    )
    assert len(tradeoff.proposed_thing_ids) == 2
    assert tradeoff.total_cost > 0.0
    assert tradeoff.aggregate_roi > 0.0

    # 7. Trace Provenance through DuckDB Telemetry Store
    prov_resp = e2e_client._request("GET", "/api/v1/telemetry/provenance/evt-strike-trigger-000")
    prov_chain = prov_resp.json()
    assert len(prov_chain) == 3
    verbs = [evt["causal_verb"] for evt in prov_chain]
    assert "COLLECTED" in verbs
    assert "DETECTED" in verbs
    assert "TRIGGERED" in verbs
