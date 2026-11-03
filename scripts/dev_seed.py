"""
Bijou Local Development Seeder.
Ensures %TEMP%/bijou_test/ has populated test databases once per system restart/session.
Zero external server dependencies (uses in-process ASGI engine).
"""

import os
import sys
from pathlib import Path


def seed_if_needed():
    temp_base = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))).resolve()
    test_dir = temp_base / "bijou_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    db_file = test_dir / "bijou_graph.db"
    duckdb_file = test_dir / "bijou_telemetry.duckdb"

    if db_file.exists() and db_file.stat().st_size > 0:
        print(f"[Bijou Dev] Database already seeded at: {db_file}")
        print("[Bijou Dev] Skipping seed (persists until system restart / temp cleanup).")
        return

    print("=" * 60)
    print(f"[Bijou Dev] No existing database found at: {db_file}")
    print(f"[Bijou Dev] Seeding reference ISR architecture & telemetry into {test_dir}...")
    print("=" * 60)

    from bijou.config import BijouSettings
    from bijou.api.app import create_app
    from bijou_sdk import BijouClient
    from bijou_ingest import ManifestIngestor

    # Resolve dataset paths relative to repo root
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "datasets" / "joint_isr_architecture.json"
    if not manifest_path.exists():
        manifest_path = repo_root / "datasets" / "joint_isr_architecture.yaml"
    telemetry_path = repo_root / "datasets" / "satellite_cascade_telemetry.jsonl"

    if not manifest_path.exists():
        print(f"[Bijou Dev] Error: Manifest file not found at: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    app = create_app(settings)

    with BijouClient(app=app) as client:
        ingestor = ManifestIngestor(client)

        print(f"[Bijou Dev] Ingesting architecture manifest: {manifest_path.name}...")
        m_res = ingestor.ingest_manifest_file(manifest_path)
        print(f"[Bijou Dev] Ingested entities: {m_res}")

        if telemetry_path.exists():
            print(f"[Bijou Dev] Ingesting telemetry event stream: {telemetry_path.name}...")
            t_count = ingestor.ingest_telemetry_file(telemetry_path)
            print(f"[Bijou Dev] Ingested {t_count} telemetry events into DuckDB.")

    print("=" * 60)
    print("[Bijou Dev] Seeding completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    seed_if_needed()

