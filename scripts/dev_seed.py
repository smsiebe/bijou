"""
Bijou Local Development Seeder (v2).
Ensures %TEMP%/bijou_test/ has populated test databases once per system restart/session.
"""

import os
import sys
from pathlib import Path


def seed_if_needed() -> None:
    temp_base = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))).resolve()
    test_dir = temp_base / "bijou_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    db_file = test_dir / "bijou_graph.db"
    duckdb_file = test_dir / "bijou_telemetry.duckdb"

    from bijou.config import BijouSettings
    from bijou.api.app import create_app
    from bijou_sdk import BijouClient
    from bijou_ingest import ManifestIngestor

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    app = create_app(settings)

    with BijouClient(app=app) as client:
        existing_efforts = client.list_efforts()
        if existing_efforts:
            print(f"[Bijou Dev] Database already seeded ({len(existing_efforts)} efforts) at: {db_file}")
            return

        repo_root = Path(__file__).resolve().parent.parent
        manifest_path = repo_root / "datasets" / "joint_isr_architecture.json"
        telemetry_path = repo_root / "datasets" / "satellite_cascade_telemetry.jsonl"

        if not manifest_path.exists():
            print(f"[Bijou Dev] Error: Manifest not found at {manifest_path}", file=sys.stderr)
            sys.exit(1)

        ingestor = ManifestIngestor(client)
        print(f"[Bijou Dev] Seeding v2 reference manifest: {manifest_path.name}...")
        m_res = ingestor.ingest_manifest_file(manifest_path, replace_all=True)
        print(f"[Bijou Dev] Ingested v2 entities: {m_res}")

        if telemetry_path.exists():
            t_count = ingestor.ingest_telemetry_file(telemetry_path)
            print(f"[Bijou Dev] Ingested {t_count} telemetry events into DuckDB.")


if __name__ == "__main__":
    seed_if_needed()
