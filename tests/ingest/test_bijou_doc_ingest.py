"""Integration and security tests for bijou-doc-ingest package."""

from pathlib import Path

import pytest
from bijou_ingest import ManifestIngestor, validate_safe_path
from bijou_sdk import BijouClient

from bijou.api.app import create_app
from bijou.config import BijouSettings


@pytest.fixture
def ingest_client(tmp_path: Path):
    """Fixture initializing an ASGI-backed BijouClient with isolated test persistence."""
    db_file = tmp_path / "ingest_test_graph.db"
    duckdb_file = tmp_path / "ingest_test_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    test_app = create_app(settings)

    with BijouClient(app=test_app) as client:
        yield client


def test_reference_dataset_validates_and_ingests_via_sdk(ingest_client: BijouClient):
    """Verifies that the reference Joint ISR architecture YAML and telemetry stream ingest cleanly."""
    root_dir = Path(__file__).parent.parent.parent
    datasets_dir = root_dir / "datasets"
    yaml_path = datasets_dir / "joint_isr_architecture.yaml"
    jsonl_path = datasets_dir / "satellite_cascade_telemetry.jsonl"

    assert yaml_path.exists(), f"Reference architecture manifest missing: {yaml_path}"
    assert jsonl_path.exists(), f"Reference telemetry dataset missing: {jsonl_path}"

    ingestor = ManifestIngestor(client=ingest_client)

    # 1. Ingest Manifest
    manifest_res = ingestor.ingest_manifest_file(yaml_path, base_dir=datasets_dir)
    assert manifest_res.get("organizations") == 5
    assert manifest_res.get("concerns") == 5
    assert manifest_res.get("things") == 6
    assert manifest_res.get("causal_gates") == 3
    assert manifest_res.get("effects") == 4
    assert manifest_res.get("edges") == 18

    # 2. Ingest 60 Telemetry Events
    ingested_events_count = ingestor.ingest_telemetry_file(jsonl_path, base_dir=datasets_dir)
    assert ingested_events_count == 60

    # 3. Verify Tech Tree View contains nodes and gates
    tree_view = ingest_client.get_tech_tree()
    assert len(tree_view.nodes) == 14
    assert len(tree_view.tiers) == 3


def test_ingestor_rejects_path_traversal_sequences(tmp_path: Path):
    """Asserts that validate_safe_path prevents path traversal and directory escape attempts."""
    safe_dir = tmp_path / "safe_sandbox"
    safe_dir.mkdir()
    valid_file = safe_dir / "valid_doc.yaml"
    valid_file.write_text("schema_version: '1.0.0'", encoding="utf-8")

    outside_file = tmp_path / "secret_doc.yaml"
    outside_file.write_text("secret_data: true", encoding="utf-8")

    # Valid relative path inside safe_sandbox
    resolved = validate_safe_path(safe_dir, "valid_doc.yaml")
    assert resolved == valid_file.resolve()

    # Path traversal attempt using parent directory '..'
    with pytest.raises(ValueError) as exc_traversal:
        validate_safe_path(safe_dir, "../secret_doc.yaml")
    assert "Path traversal detected" in str(exc_traversal.value)

    # Absolute path pointing outside the safe directory
    with pytest.raises(ValueError) as exc_abs:
        validate_safe_path(safe_dir, outside_file)
    assert "Path traversal detected" in str(exc_abs.value)
