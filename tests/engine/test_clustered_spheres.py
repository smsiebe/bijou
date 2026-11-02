"""Unit and integration tests for Clustered Spheres of Ownership and Tool Registry."""

from datetime import date
from pathlib import Path
import pytest

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou_sdk import BijouClient
from bijou_ingest import ManifestIngestor


@pytest.fixture
def test_client(tmp_path: Path):
    db_file = tmp_path / "test_spheres.db"
    duckdb_file = tmp_path / "test_spheres.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    app = create_app(settings)

    with BijouClient(app=app) as client:
        # Ingest reference dataset
        root_dir = Path(__file__).parent.parent.parent
        datasets_dir = root_dir / "datasets"
        yaml_path = datasets_dir / "joint_isr_architecture.yaml"
        jsonl_path = datasets_dir / "satellite_cascade_telemetry.jsonl"

        ingestor = ManifestIngestor(client)
        ingestor.ingest_manifest_file(yaml_path, base_dir=datasets_dir)
        ingestor.ingest_telemetry_file(jsonl_path, base_dir=datasets_dir)

        yield client


def test_list_tools_endpoint(test_client: BijouClient):
    """Verifies that the /api/v1/tools endpoint returns registered analytical tools."""
    resp = test_client._request("GET", "/api/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) >= 4

    tool_ids = [t["tool_id"] for t in tools]
    assert "what_if_slip" in tool_ids
    assert "spheres_of_ownership" in tool_ids
    assert "focal_dashboard" in tool_ids
    assert "decision_provenance" in tool_ids


def test_clustered_spheres_view(test_client: BijouClient):
    """Verifies that the clustered spheres view partitions Things by Organization with cross-cutting edges."""
    resp = test_client._request("GET", "/api/v1/views/clustered-spheres")
    assert resp.status_code == 200
    data = resp.json()

    assert "clusters" in data
    assert "nodes" in data
    assert "edges" in data
    assert "macro_org_edges" in data

    clusters = data["clusters"]
    nodes = data["nodes"]
    edges = data["edges"]
    macro_edges = data["macro_org_edges"]

    # Verify organizations partitioned
    assert len(clusters) == 5
    org_ids = {c["org_id"] for c in clusters}
    assert "org-strat-space" in org_ids
    assert "org-c2-joint" in org_ids

    # Verify things partitioned into nodes
    assert len(nodes) == 6
    for node in nodes:
        assert node["cluster_org_id"] in org_ids
        assert node["trl"] >= 1
        assert "is_cross_cutting" in node

    # Verify cross-org edges detected
    cross_org_edges = [e for e in edges if e["is_cross_org"]]
    assert len(cross_org_edges) > 0

    # Verify macro org edges aggregated
    assert len(macro_edges) > 0
    for me in macro_edges:
        assert me["dependency_count"] >= 1
        assert len(me["involved_thing_ids"]) >= 1


def test_clustered_spheres_view_with_org_filter(test_client: BijouClient):
    """Verifies that filtering by org_id restricts clusters and nodes accordingly."""
    resp = test_client._request("GET", "/api/v1/views/clustered-spheres", params={"org_filter": "org-strat-space"})
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["clusters"]) == 1
    assert data["clusters"][0]["org_id"] == "org-strat-space"
    for node in data["nodes"]:
        assert node["cluster_org_id"] == "org-strat-space"
