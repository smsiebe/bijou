"""Tests for Bijou v2 integrated manifest & telemetry ingestion utilities (bijou.sdk)."""

from pathlib import Path

import pytest

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.sdk import BijouClient, ManifestIngestor, validate_safe_path


def test_ingestor_loads_v2_json_and_yaml_manifests_and_telemetry(tmp_path: Path) -> None:
    datasets_dir = Path(__file__).resolve().parent.parent.parent / "datasets"
    app = create_app(
        BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/ingest.db",
            duckdb_path=str(tmp_path / "ingest.duckdb"),
            enable_reasoning=False,
        )
    )
    with BijouClient(app=app) as client:
        ing = ManifestIngestor(client)
        counts_json = ing.ingest_manifest_file(
            "joint_isr_architecture.json",
            base_dir=datasets_dir,
            replace_all=True,
            validate_first=True,
        )
        assert counts_json["organizations"] == 5
        assert counts_json["efforts"] == 6

        counts_yaml = ing.ingest_manifest_file("joint_isr_architecture.yaml", base_dir=datasets_dir, replace_all=True)
        assert counts_yaml["efforts"] == 6

        tel_count = ing.ingest_telemetry_file("satellite_cascade_telemetry.jsonl", base_dir=datasets_dir)
        assert tel_count == 5


def test_path_traversal_blocked(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        validate_safe_path(tmp_path, "../outside.yaml")
